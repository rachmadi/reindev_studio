# -*- coding: utf-8 -*-
"""
Phase-End Validated StateGraph for ReinDev Studio (Unification Wrapper)
ReinDev Studio — v2.2 (End-Phase Validated Engine)

Mendelegasikan dan menyatukan seluruh StateGraph ke implementasi otoritatif di backend/graph.py,
mengeliminasi fragmentasi graf ganda (Dual-World Graph Fragmentation).
"""

from typing import Dict, Any, List, Optional
from .state import SquadState
from .graph import (
    build_squad_graph,
    squad_graph,
    pm_validator_node,
    route_after_pm_validator,
    architect_validator_node,
    route_after_architect_validator,
    developer_validator_node,
    route_after_developer_validator,
    frozen_oracle_node,
    test_suite_validator_node,
    route_after_test_suite_validator,
    executor_validator_node,
    route_after_executor_validator,
    reviewer_validator_node,
    route_after_reviewer_validator,
    contract_validation_node,
    route_after_contract_gate,
    route_after_developer,
    route_after_executor
)


class PhaseValidatedSquadState(SquadState, total=False):
    """Backward-compatible subclass alias untuk SquadState."""
    pass


# Re-export aliases for pilot and legacy runners
build_phase_validated_graph = build_squad_graph
phase_validated_squad_graph = squad_graph
oracle_validator_node = test_suite_validator_node
route_after_oracle_validator = route_after_test_suite_validator
executor_iteration_validator_node = executor_validator_node
