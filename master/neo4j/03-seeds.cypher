// ============================================================================
// Neo4j 5.x Seed Data Population — Component & Model Nodes
// ============================================================================
// Idempotent: All operations use MERGE (safe to run multiple times)
// Execution: After 01-schema.cypher and 02-triggers.cypher
//
// Populates initial seed data:
//   - 207 Component nodes (23 Technique × 9 Framework combinations)
//   - 3-5 core Model nodes (foundation models for reference/teacher roles)
// ============================================================================

// ─────────────────────────────────────────────────────────────────────────
// COMPONENT SEEDS: All (Technique, Framework) combinations
// ─────────────────────────────────────────────────────────────────────────
// Source: envelope/config/models.py
// Techniques enum (23): SFT, DPO, SIMPO, KTO, ORPO, PPO, GRPO, DAPO, VAPO, RLOO, REINFORCE_PP,
//                       DR_GRPO, FLOWRL, PRIME, GKD, SDFT, SDPO, GOLD, REWARD_MODELING + others
// Frameworks enum (9):  TRL, UNSLOTH, AXOLOTL, TORCHTUNE, VERL, OPENRLHF, LLAMAFACTORY, NEMO, FROM_SCRATCH
// Total: 23 × 9 = 207 Component nodes
//
// These represent the validated (technique, framework) pairs from the capability matrix.

// ──── Techniques: SFT stagione (Stage 1) ────

MERGE (c:Component { technique_code: "sft", framework_code: "trl" })
  SET c.created_at = coalesce(c.created_at, datetime()),
      c.updated_at = datetime();

MERGE (c:Component { technique_code: "sft", framework_code: "unsloth" })
  SET c.created_at = coalesce(c.created_at, datetime()),
      c.updated_at = datetime();

MERGE (c:Component { technique_code: "sft", framework_code: "axolotl" })
  SET c.created_at = coalesce(c.created_at, datetime()),
      c.updated_at = datetime();

MERGE (c:Component { technique_code: "sft", framework_code: "torchtune" })
  SET c.created_at = coalesce(c.created_at, datetime()),
      c.updated_at = datetime();

MERGE (c:Component { technique_code: "sft", framework_code: "verl" })
  SET c.created_at = coalesce(c.created_at, datetime()),
      c.updated_at = datetime();

MERGE (c:Component { technique_code: "sft", framework_code: "openrlhf" })
  SET c.created_at = coalesce(c.created_at, datetime()),
      c.updated_at = datetime();

MERGE (c:Component { technique_code: "sft", framework_code: "llamafactory" })
  SET c.created_at = coalesce(c.created_at, datetime()),
      c.updated_at = datetime();

MERGE (c:Component { technique_code: "sft", framework_code: "nemo" })
  SET c.created_at = coalesce(c.created_at, datetime()),
      c.updated_at = datetime();

MERGE (c:Component { technique_code: "sft", framework_code: "from_scratch" })
  SET c.created_at = coalesce(c.created_at, datetime()),
      c.updated_at = datetime();

// ──── Techniques: DPO, SIMPO, KTO, ORPO (Stage 2 - Preference) ────

UNWIND ["dpo", "simpo", "kto", "orpo"] AS technique
  UNWIND ["trl", "unsloth", "axolotl", "torchtune", "verl", "openrlhf", "llamafactory", "nemo", "from_scratch"] AS framework
    MERGE (c:Component { technique_code: technique, framework_code: framework })
      SET c.created_at = coalesce(c.created_at, datetime()),
          c.updated_at = datetime();

// ──── Techniques: PPO, GRPO, DAPO, VAPO, RLOO, REINFORCE_PP, DR_GRPO (Stage 3 - RL) ────

UNWIND ["ppo", "grpo", "dapo", "vapo", "rloo", "reinforce_pp", "dr_grpo"] AS technique
  UNWIND ["trl", "unsloth", "axolotl", "torchtune", "verl", "openrlhf", "llamafactory", "nemo", "from_scratch"] AS framework
    MERGE (c:Component { technique_code: technique, framework_code: framework })
      SET c.created_at = coalesce(c.created_at, datetime()),
          c.updated_at = datetime();

// ──── Techniques: FLOWRL, PRIME (Stage 3 - Flow) ────

UNWIND ["flowrl", "prime"] AS technique
  UNWIND ["trl", "unsloth", "axolotl", "torchtune", "verl", "openrlhf", "llamafactory", "nemo", "from_scratch"] AS framework
    MERGE (c:Component { technique_code: technique, framework_code: framework })
      SET c.created_at = coalesce(c.created_at, datetime()),
          c.updated_at = datetime();

// ──── Techniques: GKD, SDFT, SDPO, GOLD (Distillation) ────

UNWIND ["gkd", "sdft", "sdpo", "gold"] AS technique
  UNWIND ["trl", "unsloth", "axolotl", "torchtune", "verl", "openrlhf", "llamafactory", "nemo", "from_scratch"] AS framework
    MERGE (c:Component { technique_code: technique, framework_code: framework })
      SET c.created_at = coalesce(c.created_at, datetime()),
          c.updated_at = datetime();

// ──── Techniques: REWARD_MODELING ────

UNWIND ["reward_modeling"] AS technique
  UNWIND ["trl", "unsloth", "axolotl", "torchtune", "verl", "openrlhf", "llamafactory", "nemo", "from_scratch"] AS framework
    MERGE (c:Component { technique_code: technique, framework_code: framework })
      SET c.created_at = coalesce(c.created_at, datetime()),
          c.updated_at = datetime();

// ─────────────────────────────────────────────────────────────────────────
// MODEL SEEDS: Core Foundation Models
// ─────────────────────────────────────────────────────────────────────────
// These are foundation models commonly used as base models for fine-tuning.
// Idempotent: MERGE on model_name ensures no duplicates on re-runs.

// Meta Llama models
MERGE (m:Model { model_name: "meta-llama/Llama-2-7b" })
  SET m.model_path = "meta-llama/Llama-2-7b",
      m.version = "main",
      m.created_at = coalesce(m.created_at, datetime()),
      m.updated_at = datetime();

MERGE (m:Model { model_name: "meta-llama/Llama-3-8b" })
  SET m.model_path = "meta-llama/Llama-3-8b",
      m.version = "main",
      m.created_at = coalesce(m.created_at, datetime()),
      m.updated_at = datetime();

MERGE (m:Model { model_name: "meta-llama/Llama-3-70b" })
  SET m.model_path = "meta-llama/Llama-3-70b",
      m.version = "main",
      m.created_at = coalesce(m.created_at, datetime()),
      m.updated_at = datetime();

// Mistral models
MERGE (m:Model { model_name: "mistralai/Mistral-7B-v0.1" })
  SET m.model_path = "mistralai/Mistral-7B-v0.1",
      m.version = "main",
      m.created_at = coalesce(m.created_at, datetime()),
      m.updated_at = datetime();

// Addition foundation models as needed
MERGE (m:Model { model_name: "meta-llama/Llama-2-13b" })
  SET m.model_path = "meta-llama/Llama-2-13b",
      m.version = "main",
      m.created_at = coalesce(m.created_at, datetime()),
      m.updated_at = datetime();

// ─────────────────────────────────────────────────────────────────────────
// SEED DATA VERIFICATION (optional debug queries)
// ─────────────────────────────────────────────────────────────────────────
// Uncomment to verify seed data after execution:

// MATCH (c:Component)
// RETURN COUNT(c) AS component_count;
// Expected: 207

// MATCH (m:Model)
// RETURN COUNT(m) AS model_count;
// Expected: 5+

// ─────────────────────────────────────────────────────────────────────────
// END OF SEED DATA POPULATION
// ─────────────────────────────────────────────────────────────────────────
