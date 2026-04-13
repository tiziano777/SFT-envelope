"""Lineage strategy determination and experiment discovery."""

from __future__ import annotations

from typing import Optional

from envelope.middleware.shared.envelopes import HandshakeRequest, Strategy
from envelope.middleware.shared.nodes import ExperimentNode


class LineageController:
    """Determines handshake strategy and manages experiment lineage discovery."""

    @staticmethod
    def determine_strategy(
        existing_exp: Optional[ExperimentNode],
        req: HandshakeRequest,
    ) -> Strategy:
        """Determine strategy based on experiment existence and request.

        Args:
            existing_exp: Existing experiment from find_by_hashes, or None
            req: HandshakeRequest with config/code/req hashes

        Returns:
            Strategy enum value (NEW, RESUME, BRANCH, RETRY)

        Strategy logic:
        - NEW: No existing experiment (existing_exp is None)
        - RESUME: Experiment exists with all hashes matching, no base_exp_id
        - BRANCH: base_exp_id provided without checkpoint_id_to_resume
        - RETRY: base_exp_id provided with checkpoint_id_to_resume, same config
        """
        if not existing_exp:
            # No directory match → NEW
            return Strategy.NEW

        if req.base_exp_id:
            # base_exp_id provided → branching scenario
            if req.checkpoint_id_to_resume:
                # Explicit resume from checkpoint → RETRY
                return Strategy.RETRY
            else:
                # Different config from base → BRANCH
                return Strategy.BRANCH
        else:
            # No base_exp_id, but experiment exists → RESUME
            return Strategy.RESUME

    @staticmethod
    def exp_id_from_strategy(
        strategy: Strategy,
        existing_exp: Optional[ExperimentNode],
        req: HandshakeRequest,
    ) -> str:
        """Generate or select experiment ID based on strategy.

        Args:
            strategy: Determined strategy
            existing_exp: Existing experiment node (if any)
            req: HandshakeRequest

        Returns:
            Experiment ID string
        """
        if strategy == Strategy.RESUME:
            # Reuse existing experiment ID
            assert existing_exp is not None
            return existing_exp.exp_id

        if strategy in (Strategy.BRANCH, Strategy.RETRY):
            # Use base_exp_id as reference (new run will have unique exp_id)
            # In practice, worker generates new exp_id
            return req.base_exp_id or str(__import__("uuid").uuid4())

        # NEW strategy: generate new ID
        return str(__import__("uuid").uuid4())
