"""Base trainer for from-scratch PyTorch training loops.

This is the root ABC. All from-scratch trainers inherit from this class.
The training loop (train()) is concrete and fully functional. Subclasses
only need to implement compute_loss() and collate_fn().

Supports single-GPU, multi-GPU via FSDP, and multi-node via FSDP + torchrun.
"""

from __future__ import annotations

import json
import math
import os
import shutil
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import torch
import torch.nn as nn
from torch.utils.data import DataLoader


@dataclass
class FSDPTrainerConfig:
    """FSDP-specific settings for BaseFromScratchTrainer."""

    enabled: bool = False
    sharding_strategy: str = "full_shard"
    auto_wrap_policy: str = "transformer_based"
    min_num_params: int = 1_000_000
    cpu_offload: bool = False
    mixed_precision: str = "none"
    forward_prefetch: bool = True
    backward_prefetch: str = "backward_pre"
    sync_module_states: bool = True
    use_orig_params: bool = True
    limit_all_gathers: bool = True
    activation_checkpointing: bool = False


@dataclass
class TrainerConfig:
    """Training configuration for hyperparameters overridable via HPARAM_* env vars."""

    output_dir: str = "./output"
    learning_rate: float = 1e-5
    per_device_train_batch_size: int = 2
    warmup_ratio: float = 0.1
    weight_decay: float = 0.01
    num_train_epochs: int = 3
    gradient_accumulation_steps: int = 4
    lr_scheduler_type: str = "cosine"
    max_grad_norm: float = 1.0
    logging_steps: int = 10
    save_steps: int = 500
    save_total_limit: int = 3
    seed: int = 42
    bf16: bool = True
    fp16: bool = False
    gradient_checkpointing: bool = True
    max_seq_length: int = 2048
    technique_args: dict[str, Any] = field(default_factory=dict)
    fsdp: FSDPTrainerConfig = field(default_factory=FSDPTrainerConfig)


# ──────────────── Structured Output ────────────────

_STRUCTURED = os.environ.get("ENVELOPE_STRUCTURED_OUTPUT", "false").lower() == "true"


def emit(marker: str, data: Any) -> None:
    """Emit structured output for external tooling."""
    if _STRUCTURED:
        if isinstance(data, dict):
            print(f"{marker}: {json.dumps(data)}", flush=True)
        else:
            print(f"{marker}: {data}", flush=True)


# ──────────────── LR Schedulers ────────────────


def _get_cosine_schedule_with_warmup(
    optimizer: torch.optim.Optimizer,
    num_warmup_steps: int,
    num_training_steps: int,
) -> torch.optim.lr_scheduler.LambdaLR:
    def lr_lambda(current_step: int) -> float:
        if current_step < num_warmup_steps:
            return float(current_step) / float(max(1, num_warmup_steps))
        progress = float(current_step - num_warmup_steps) / float(
            max(1, num_training_steps - num_warmup_steps)
        )
        return max(0.0, 0.5 * (1.0 + math.cos(math.pi * progress)))

    return torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)


def _get_linear_schedule_with_warmup(
    optimizer: torch.optim.Optimizer,
    num_warmup_steps: int,
    num_training_steps: int,
) -> torch.optim.lr_scheduler.LambdaLR:
    def lr_lambda(current_step: int) -> float:
        if current_step < num_warmup_steps:
            return float(current_step) / float(max(1, num_warmup_steps))
        return max(
            0.0,
            float(num_training_steps - current_step)
            / float(max(1, num_training_steps - num_warmup_steps)),
        )

    return torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)


# ──────────────── FSDP Helpers ────────────────


def _detect_transformer_layer_class(model: nn.Module) -> type | None:
    """Detect the transformer layer class for FSDP auto-wrapping.

    Looks for common layer class names in HuggingFace models.
    Returns the class or None.
    """
    layer_class_names = {
        "DecoderLayer",
        "LlamaDecoderLayer",
        "MistralDecoderLayer",
        "Qwen2DecoderLayer",
        "GPT2Block",
        "GPTNeoXLayer",
        "PhiDecoderLayer",
        "GemmaDecoderLayer",
        "Phi3DecoderLayer",
        "StableLmDecoderLayer",
    }
    for module in model.modules():
        if type(module).__name__ in layer_class_names:
            return type(module)
    # Fallback: find the most common repeated module with "Layer" in name
    from collections import Counter

    child_types = Counter(type(m).__name__ for m in model.modules())
    for cls_name, count in child_types.most_common():
        if count >= 4 and "Layer" in cls_name:
            for m in model.modules():
                if type(m).__name__ == cls_name:
                    return type(m)
    return None


class BaseFromScratchTrainer(ABC):
    """Abstract base for all from-scratch PyTorch trainers.

    Provides a complete, concrete training loop with gradient accumulation,
    mixed precision, LR scheduling, gradient clipping, checkpointing, and
    optional FSDP for multi-GPU/multi-node distributed training.

    Subclasses implement:
        - compute_loss(batch) -> Tensor
        - collate_fn(examples) -> dict

    Optional hooks:
        - on_train_begin(), on_train_end(metrics), on_step_end(step, loss),
          on_epoch_end(epoch, metrics), on_save(step)
    """

    def __init__(
        self,
        model: nn.Module,
        tokenizer: Any,
        config: TrainerConfig,
        train_dataset: Any,
        eval_dataset: Any | None = None,
        **kwargs: Any,
    ) -> None:
        self.tokenizer = tokenizer
        self.config = config
        self.train_dataset = train_dataset
        self.eval_dataset = eval_dataset
        self.global_step = 0
        self._extra_kwargs = kwargs

        # Distributed setup
        self._is_distributed = config.fsdp.enabled and int(os.environ.get("WORLD_SIZE", "1")) > 1
        self._local_rank = int(os.environ.get("LOCAL_RANK", "0"))
        self._world_size = int(os.environ.get("WORLD_SIZE", "1"))
        self._rank = int(os.environ.get("RANK", "0"))

        if self._is_distributed:
            import torch.distributed as dist

            if not dist.is_initialized():
                dist.init_process_group(backend="nccl")
            torch.cuda.set_device(self._local_rank)
            self.device = torch.device(f"cuda:{self._local_rank}")
        else:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        if config.gradient_checkpointing and hasattr(model, "gradient_checkpointing_enable"):
            model.gradient_checkpointing_enable()

        if self._is_distributed:
            model = self._wrap_with_fsdp(model)
        else:
            model.to(self.device)

        self.model = model

    # ──────── Abstract contract ────────

    @abstractmethod
    def compute_loss(self, batch: dict[str, torch.Tensor]) -> torch.Tensor:
        """Compute the training loss for a single batch. Must return a scalar tensor."""

    @abstractmethod
    def collate_fn(self, examples: list[dict]) -> dict[str, torch.Tensor]:
        """Convert raw dataset examples into a model-ready batch dict."""

    # ──────── Hooks (override for custom behavior) ────────

    def on_train_begin(self) -> None:
        pass

    def on_train_end(self, metrics: dict[str, Any]) -> None:
        pass

    def on_step_end(self, step: int, loss: float) -> None:
        pass

    def on_epoch_end(self, epoch: int, metrics: dict[str, Any]) -> None:
        pass

    def on_save(self, step: int) -> None:
        pass

    # ──────── Distributed helpers ────────

    def _should_log(self) -> bool:
        """Only rank 0 should log."""
        return not self._is_distributed or self._rank == 0

    def _cleanup_distributed(self) -> None:
        """Clean up distributed process group."""
        if self._is_distributed:
            import torch.distributed as dist

            if dist.is_initialized():
                dist.destroy_process_group()

    def _wrap_with_fsdp(self, model: nn.Module) -> nn.Module:
        """Wrap the model with FSDP based on FSDPTrainerConfig settings."""
        import functools

        from torch.distributed.fsdp import (
            BackwardPrefetch,
            CPUOffload,
            FullyShardedDataParallel as FSDP,
            MixedPrecision,
            ShardingStrategy,
        )
        from torch.distributed.fsdp.wrap import (
            size_based_auto_wrap_policy,
            transformer_auto_wrap_policy,
        )

        fsdp_cfg = self.config.fsdp

        # Sharding strategy
        strategy_map = {
            "full_shard": ShardingStrategy.FULL_SHARD,
            "shard_grad_op": ShardingStrategy.SHARD_GRAD_OP,
            "no_shard": ShardingStrategy.NO_SHARD,
            "hybrid_shard": ShardingStrategy.HYBRID_SHARD,
        }
        sharding = strategy_map[fsdp_cfg.sharding_strategy]

        # Mixed precision
        mp_policy = None
        if fsdp_cfg.mixed_precision == "bf16":
            mp_policy = MixedPrecision(
                param_dtype=torch.bfloat16,
                reduce_dtype=torch.bfloat16,
                buffer_dtype=torch.bfloat16,
            )
        elif fsdp_cfg.mixed_precision == "fp16":
            mp_policy = MixedPrecision(
                param_dtype=torch.float16,
                reduce_dtype=torch.float16,
                buffer_dtype=torch.float16,
            )

        # Auto-wrap policy
        wrap_cls = None
        if fsdp_cfg.auto_wrap_policy == "transformer_based":
            wrap_cls = _detect_transformer_layer_class(model)
            if wrap_cls:
                auto_wrap = functools.partial(
                    transformer_auto_wrap_policy,
                    transformer_layer_cls={wrap_cls},
                )
            else:
                auto_wrap = functools.partial(
                    size_based_auto_wrap_policy,
                    min_num_params=fsdp_cfg.min_num_params,
                )
        else:
            auto_wrap = functools.partial(
                size_based_auto_wrap_policy,
                min_num_params=fsdp_cfg.min_num_params,
            )

        # CPU offload
        cpu_offload = CPUOffload(offload_params=True) if fsdp_cfg.cpu_offload else None

        # Backward prefetch
        prefetch_map = {
            "backward_pre": BackwardPrefetch.BACKWARD_PRE,
            "backward_post": BackwardPrefetch.BACKWARD_POST,
        }
        backward_prefetch = prefetch_map[fsdp_cfg.backward_prefetch]

        model = FSDP(
            model,
            sharding_strategy=sharding,
            mixed_precision=mp_policy,
            auto_wrap_policy=auto_wrap,
            cpu_offload=cpu_offload,
            forward_prefetch=fsdp_cfg.forward_prefetch,
            backward_prefetch=backward_prefetch,
            sync_module_states=fsdp_cfg.sync_module_states,
            use_orig_params=fsdp_cfg.use_orig_params,
            limit_all_gathers=fsdp_cfg.limit_all_gathers,
            device_id=self._local_rank,
        )

        # Activation checkpointing via FSDP
        if fsdp_cfg.activation_checkpointing and wrap_cls:
            from torch.distributed.algorithms._checkpoint.checkpoint_wrapper import (
                apply_activation_checkpointing,
                checkpoint_wrapper,
                CheckpointImpl,
            )

            apply_activation_checkpointing(
                model,
                checkpoint_wrapper_fn=functools.partial(
                    checkpoint_wrapper, checkpoint_impl=CheckpointImpl.NO_REENTRANT
                ),
                check_fn=lambda submodule: isinstance(submodule, wrap_cls),
            )

        return model

    # ──────── Concrete training loop ────────

    def train(self) -> dict[str, Any]:
        """Run the full training loop. Returns final metrics dict."""
        cfg = self.config
        torch.manual_seed(cfg.seed)

        # DataLoader (with DistributedSampler for FSDP)
        sampler = None
        if self._is_distributed:
            from torch.utils.data import DistributedSampler

            sampler = DistributedSampler(
                self.train_dataset,
                num_replicas=self._world_size,
                rank=self._rank,
                shuffle=True,
                seed=cfg.seed,
            )
            dataloader = DataLoader(
                self.train_dataset,
                batch_size=cfg.per_device_train_batch_size,
                sampler=sampler,
                collate_fn=self.collate_fn,
                drop_last=True,
            )
        else:
            dataloader = DataLoader(
                self.train_dataset,
                batch_size=cfg.per_device_train_batch_size,
                shuffle=True,
                collate_fn=self.collate_fn,
                drop_last=True,
            )

        # Optimizer (MUST be created AFTER FSDP wrapping)
        optimizer = self._create_optimizer()

        # Scheduler
        steps_per_epoch = len(dataloader) // cfg.gradient_accumulation_steps
        total_steps = steps_per_epoch * cfg.num_train_epochs
        num_warmup = int(total_steps * cfg.warmup_ratio)
        scheduler = self._create_scheduler(optimizer, num_warmup, total_steps)

        # Mixed precision — disable GradScaler when FSDP handles mixed precision
        fsdp_handles_mp = self._is_distributed and cfg.fsdp.mixed_precision != "none"
        use_amp = (cfg.bf16 or cfg.fp16) and not fsdp_handles_mp
        amp_dtype = torch.bfloat16 if cfg.bf16 else torch.float16
        scaler = torch.amp.GradScaler("cuda", enabled=cfg.fp16 and not fsdp_handles_mp)

        self.on_train_begin()
        self.model.train()

        running_loss = 0.0
        log_loss = 0.0
        start_time = time.time()

        try:
            for epoch in range(cfg.num_train_epochs):
                if sampler is not None:
                    sampler.set_epoch(epoch)

                for step_in_epoch, batch in enumerate(dataloader):
                    # Move batch to device
                    batch = {k: v.to(self.device) if isinstance(v, torch.Tensor) else v for k, v in batch.items()}

                    # Forward with mixed precision
                    with torch.amp.autocast("cuda", dtype=amp_dtype, enabled=use_amp):
                        loss = self.compute_loss(batch)
                        loss = loss / cfg.gradient_accumulation_steps

                    # Backward
                    scaler.scale(loss).backward()

                    running_loss += loss.item()

                    # Accumulation step
                    if (step_in_epoch + 1) % cfg.gradient_accumulation_steps == 0:
                        scaler.unscale_(optimizer)
                        torch.nn.utils.clip_grad_norm_(self.model.parameters(), cfg.max_grad_norm)
                        scaler.step(optimizer)
                        scaler.update()
                        scheduler.step()
                        optimizer.zero_grad()

                        self.global_step += 1
                        log_loss += running_loss
                        running_loss = 0.0

                        self.on_step_end(self.global_step, log_loss)

                        # Logging (rank 0 only)
                        if self.global_step % cfg.logging_steps == 0 and self._should_log():
                            avg_loss = log_loss / cfg.logging_steps
                            elapsed = time.time() - start_time
                            print(
                                f"Step {self.global_step}/{total_steps} | "
                                f"Loss: {avg_loss:.4f} | "
                                f"LR: {scheduler.get_last_lr()[0]:.2e} | "
                                f"Time: {elapsed:.0f}s",
                                flush=True,
                            )
                            log_loss = 0.0

                        # Save checkpoint
                        if cfg.save_steps > 0 and self.global_step % cfg.save_steps == 0:
                            self._save_checkpoint(self.global_step)
                            self.on_save(self.global_step)

                epoch_metrics = {"epoch": epoch + 1, "global_step": self.global_step}
                self.on_epoch_end(epoch + 1, epoch_metrics)

            # Final metrics
            total_time = time.time() - start_time
            metrics = {
                "train_loss": log_loss / max(1, self.global_step % cfg.logging_steps) if log_loss else 0.0,
                "total_steps": self.global_step,
                "total_time_seconds": round(total_time, 2),
                "samples_per_second": round(
                    self.global_step * cfg.per_device_train_batch_size * cfg.gradient_accumulation_steps / total_time, 2
                ),
            }

            self._save_checkpoint(self.global_step)
            self.on_train_end(metrics)
            return metrics
        finally:
            self._cleanup_distributed()

    def _create_optimizer(self) -> torch.optim.Optimizer:
        """Create AdamW optimizer with weight decay."""
        cfg = self.config
        # Separate weight decay and no-decay params
        no_decay = {"bias", "LayerNorm.weight", "layer_norm.weight"}
        params = [
            {
                "params": [p for n, p in self.model.named_parameters() if not any(nd in n for nd in no_decay) and p.requires_grad],
                "weight_decay": cfg.weight_decay,
            },
            {
                "params": [p for n, p in self.model.named_parameters() if any(nd in n for nd in no_decay) and p.requires_grad],
                "weight_decay": 0.0,
            },
        ]
        return torch.optim.AdamW(params, lr=cfg.learning_rate)

    def _create_scheduler(
        self,
        optimizer: torch.optim.Optimizer,
        num_warmup_steps: int,
        num_training_steps: int,
    ) -> torch.optim.lr_scheduler.LambdaLR:
        """Create LR scheduler based on config."""
        if self.config.lr_scheduler_type == "linear":
            return _get_linear_schedule_with_warmup(optimizer, num_warmup_steps, num_training_steps)
        return _get_cosine_schedule_with_warmup(optimizer, num_warmup_steps, num_training_steps)

    def _save_checkpoint(self, step: int) -> None:
        """Save model checkpoint. FSDP-aware if distributed."""
        save_dir = Path(self.config.output_dir) / f"checkpoint-{step}"

        if self._is_distributed:
            from torch.distributed.fsdp import (
                FullStateDictConfig,
                FullyShardedDataParallel as FSDP,
                StateDictType,
            )

            full_state_cfg = FullStateDictConfig(offload_to_cpu=True, rank0_only=True)
            with FSDP.state_dict_type(self.model, StateDictType.FULL_STATE_DICT, full_state_cfg):
                state_dict = self.model.state_dict()

            if self._rank == 0:
                save_dir.mkdir(parents=True, exist_ok=True)
                torch.save(state_dict, save_dir / "model.pt")
                if hasattr(self.tokenizer, "save_pretrained"):
                    self.tokenizer.save_pretrained(str(save_dir))
                self._manage_checkpoints()
                print(f"Checkpoint saved: {save_dir}", flush=True)

            import torch.distributed as dist

            dist.barrier()
        else:
            save_dir.mkdir(parents=True, exist_ok=True)
            if hasattr(self.model, "save_pretrained"):
                self.model.save_pretrained(str(save_dir))
            else:
                torch.save(self.model.state_dict(), save_dir / "model.pt")
            if hasattr(self.tokenizer, "save_pretrained"):
                self.tokenizer.save_pretrained(str(save_dir))
            self._manage_checkpoints()
            print(f"Checkpoint saved: {save_dir}", flush=True)

    def _manage_checkpoints(self) -> None:
        """Remove oldest checkpoints beyond save_total_limit."""
        output_path = Path(self.config.output_dir)
        checkpoints = sorted(output_path.glob("checkpoint-*"), key=lambda p: int(p.name.split("-")[1]))
        while len(checkpoints) > self.config.save_total_limit:
            oldest = checkpoints.pop(0)
            shutil.rmtree(oldest)

    def save_model(self) -> None:
        """Save the final model to output_dir."""
        output_path = Path(self.config.output_dir) / "final"
        if self._is_distributed:
            from torch.distributed.fsdp import (
                FullStateDictConfig,
                FullyShardedDataParallel as FSDP,
                StateDictType,
            )

            full_state_cfg = FullStateDictConfig(offload_to_cpu=True, rank0_only=True)
            with FSDP.state_dict_type(self.model, StateDictType.FULL_STATE_DICT, full_state_cfg):
                state_dict = self.model.state_dict()

            if self._rank == 0:
                output_path.mkdir(parents=True, exist_ok=True)
                torch.save(state_dict, output_path / "model.pt")
                if hasattr(self.tokenizer, "save_pretrained"):
                    self.tokenizer.save_pretrained(str(output_path))
        else:
            output_path.mkdir(parents=True, exist_ok=True)
            if hasattr(self.model, "save_pretrained"):
                self.model.save_pretrained(str(output_path))
            else:
                torch.save(self.model.state_dict(), output_path / "model.pt")
            if hasattr(self.tokenizer, "save_pretrained"):
                self.tokenizer.save_pretrained(str(output_path))
