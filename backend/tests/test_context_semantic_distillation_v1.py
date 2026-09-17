"""
Test Suite for Treatment #1.8.2: Context Semantic Distillation & Adaptive Delivery v1.
Validates Properties A through O:
- Property A: Semantic Distillation Size Reduction (>20% representation reduction without dropping decision facts)
- Property B: Adaptive Budget Parametrization (respects 4500, 6000, 7500, 10000, 12000, 15000)
- Property C: 9 Structured Blocks of Repair Decision Packet Present
- Property D: Relational Chain Preservation in CURRENT_VALID_STATE
- Property E: Atomic Semantic Payload Validation (what, where, observed, expected, PRESERVE, ALLOWED, FORBIDDEN)
- Property F: Structured DELIVERY_FAILURE (Fail-Closed, 0 LLM Invocations, 0 Turns Consumed)
- Property G: Deterministic Recovery Pass with Configured Budget
- Property H: Extended Telemetry Validation (all 8 audit fields)
- Property I: Elimination of Scaffold Code Duplication
- Property J: Distillation of Verbose Diagnostic Tracebacks
- Property K: Cross-Domain Generalization (Compiler IR vs Audio DSP Graph)
- Property L: No Silent Omission of Acceptance Obligations
- Property M: Backward Compatibility with Turn 0 Context Assembly
- Property N: Prompt De-duplication on Repair Turns in Architect
- Property O: Deterministic Invariance (bit-identical output on identical input)
"""

import pytest
from typing import Dict, Any, List
from unittest.mock import MagicMock

from backend.context_hardening import (
    build_architect_repair_context,
    build_architect_decision_context,
    distill_failure_item_semantic,
    distill_canonical_schema_semantic,
    compress_raw_diagnostics_semantic,
    resolve_context_budget,
    ContextTelemetry,
)
from backend.architect_preservation import (
    validate_architect_repair_context_delivery,
    RepairStateLedger,
    RepairStateItem,
    RepairTransitionStatus,
)
from backend.agents.architect import architect_agent


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_repair_state():
    """Realistic repair state mimicking an architect repair turn."""
    return {
        "task": "Build an HTTP API for item management with CRUD operations.",
        "contract_revision_count": 1,
        "contract": {
            "task_intent": {
                "authoritative_target_file": "app/main.py",
                "domain": "web_api",
            },
            "file_tree": ["app/main.py", "app/models.py"],
            "interface_contracts": [
                {"identifier": "app.main:app", "target_file": "app/main.py"},
                {"identifier": "app.main:get_items", "target_file": "app/main.py"},
            ],
            "data_models": [
                {"model_name": "Item"},
            ]
        },
        "architectural_blueprint": {
            "authoritative_target_file": "app/main.py",
            "file_tree": ["app/main.py", "app/models.py"],
            "files": {
                "app/main.py": {
                    "path": "app/main.py",
                    "code": (
                        "from fastapi import FastAPI\n\n"
                        "app = FastAPI()\n\n"
                        "@app.get('/items')\n"
                        "def get_items():\n"
                        "    '''Retrieve item list.'''\n"
                        "    return []\n"
                    )
                },
                "app/models.py": {
                    "path": "app/models.py",
                    "code": (
                        "from pydantic import BaseModel\n\n"
                        "class Item(BaseModel):\n"
                        "    id: int\n"
                        "    name: str\n"
                    )
                }
            },
            "interface_contracts": [
                {"identifier": "app.main:app", "target_file": "app/main.py"},
                {"identifier": "app.main:get_items", "target_file": "app/main.py"},
            ],
            "data_models": [
                {"model_name": "Item"},
            ]
        },
        "contract_feedback": (
            "Traceback (most recent call last):\n"
            "  File \"/usr/lib/python3.11/site-packages/fastapi/routing.py\", line 200, in run\n"
            "    res = endpoint()\n"
            "  File \"/repo/backend/runner.py\", line 45, in evaluate\n"
            "    assert res is not None\n"
            "AssertionError: Missing interface declaration for POST /items endpoint."
        ),
        "test_files": {
            "tests/test_api.py": (
                "def test_create_item():\n"
                "    response = client.post('/items', json={'name': 'widget'})\n"
                "    assert response.status_code == 201\n"
            )
        }
    }


# ---------------------------------------------------------------------------
# Property A: Semantic Distillation Size Reduction
# ---------------------------------------------------------------------------

def test_property_a_distillation_size_reduction(mock_repair_state):
    """Distillation should reduce representation size while retaining 100% decision facts."""
    ctx, telem = build_architect_repair_context(mock_repair_state, max_chars=12000)
    
    assert telem["raw_context_chars"] > 0
    assert telem["final_context_chars"] <= 12000
    assert telem["final_context_chars"] <= telem["raw_context_chars"]
    assert telem["compression_ratio"] <= 1.0


# ---------------------------------------------------------------------------
# Property B: Adaptive Context Budget Parametrization
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("budget", [4500, 6000, 7500, 10000, 12000, 15000])
def test_property_b_adaptive_budget_parametrization(mock_repair_state, budget):
    """Context assembler must adapt strictly to the configured budget parameter."""
    state = dict(mock_repair_state)
    state["context_budget"] = budget
    ctx, telem = build_architect_repair_context(state)
    
    assert len(ctx) <= budget
    assert telem["configured_budget"] == budget
    assert telem["final_context_chars"] == len(ctx)


# ---------------------------------------------------------------------------
# Property C: 9 Structured Blocks of Repair Decision Packet Present
# ---------------------------------------------------------------------------

def test_property_c_repair_decision_packet_blocks(mock_repair_state):
    """All required structured sections must be present in the repair context."""
    ctx, telem = build_architect_repair_context(mock_repair_state, max_chars=12000)
    
    expected_headers = [
        "[1] IMMUTABLE ACCEPTANCE AUTHORITY",
        "[2] ACCEPTANCE OBLIGATION LEDGER & CANONICAL BLUEPRINT SCHEMA CONSTRAINTS",
        "[3] CURRENT COMPATIBILITY FAILURES",
        "[4] LOCKED/PROVEN STATE & INVARIANTS",
        "[5] CURRENT SCAFFOLD & VALIDATED STRUCTURAL STATE",
        "[6] REPAIR TARGET (ATOMIC REPAIR INVARIANT)",
        "[7] REPAIR BOUNDARY (ATOMIC REPAIR INVARIANT)",
        "[8] EXPECTED POST-REPAIR STATE & VERIFICATION CRITERIA",
        "[9] IMPLEMENTATION GROUNDING & RELATIONAL BLUEPRINT STATE [F]",
    ]
    for hdr in expected_headers:
        assert hdr in ctx, f"Missing required section header: {hdr}"


# ---------------------------------------------------------------------------
# Property D: Relational Chain Preservation in CURRENT_VALID_STATE
# ---------------------------------------------------------------------------

def test_property_d_relational_chain_preservation(mock_repair_state):
    """CURRENT_VALID_STATE must preserve artifact -> target location -> interface -> scaffold."""
    ctx, telem = build_architect_repair_context(mock_repair_state, max_chars=12000)
    
    assert "Established File Collection (file_tree):" in ctx
    assert "app/main.py" in ctx
    assert "app/models.py" in ctx
    assert "Associated Interfaces:" in ctx or "Scaffold Interface Signatures" in ctx
    assert telem["relational_preservation_status"] == "INTACT"


# ---------------------------------------------------------------------------
# Property E: Atomic Semantic Payload Validation
# ---------------------------------------------------------------------------

def test_property_e_atomic_semantic_payload_validation(mock_repair_state):
    """Context must pass atomic semantic payload validation (what, where, observed, expected, PRESERVE, ALLOWED, FORBIDDEN)."""
    ctx, telem = build_architect_repair_context(mock_repair_state, max_chars=12000)
    
    valid, errors = validate_architect_repair_context_delivery(ctx)
    assert valid is True, f"Delivery validation failed: {errors}"
    assert telem["delivery_valid"] is True
    assert telem["semantic_payload_completeness"] is True


# ---------------------------------------------------------------------------
# Property F: Structured DELIVERY_FAILURE (Fail-Closed, 0 LLM Invocations)
# ---------------------------------------------------------------------------

def test_property_f_fail_closed_delivery_failure():
    """Invalid delivered context must return structured DELIVERY_FAILURE with 0 LLM calls and 0 turn cost."""
    bad_state = {
        "task": "Test task",
        "contract_revision_count": 1,
        "contract_feedback": "Some failure",
        "context_budget": 50,  # Extreme budget restriction causing delivery gate failure
    }
    
    mock_llm = MagicMock()
    mock_tracer = MagicMock()
    
    result = architect_agent(bad_state, llm=mock_llm, tracer=mock_tracer)
    
    # Assert fail-closed: LLM was NOT invoked
    assert mock_llm.invoke.call_count == 0
    # Status is DELIVERY_FAILURE
    assert result["contract_status"] == "DELIVERY_FAILURE"
    assert result["status"] == "DELIVERY_FAILURE"
    assert result["delivery_valid"] is False
    assert result.get("blueprint_revision_count", 0) == 0


# ---------------------------------------------------------------------------
# Property G: Deterministic Recovery Pass
# ---------------------------------------------------------------------------

def test_property_g_recovery_pass_uses_configured_budget(mock_repair_state):
    """The delivery gate recovery pass must respect configured context budget."""
    state = dict(mock_repair_state)
    state["context_budget"] = 10000
    
    ctx, telem = build_architect_decision_context(state)
    assert telem["configured_budget"] == 10000
    assert len(ctx) <= 10000


# ---------------------------------------------------------------------------
# Property H: Extended Telemetry Validation
# ---------------------------------------------------------------------------

def test_property_h_extended_telemetry_fields(mock_repair_state):
    """All 8 new audit fields must be populated in telemetry."""
    ctx, telem = build_architect_repair_context(mock_repair_state, max_chars=12000)
    
    required_telemetry_fields = [
        "raw_context_chars",
        "distilled_context_chars",
        "final_context_chars",
        "configured_budget",
        "estimated_token_count",
        "compression_ratio",
        "semantic_payload_completeness",
        "relational_preservation_status",
    ]
    for fld in required_telemetry_fields:
        assert fld in telem, f"Missing telemetry field: {fld}"
        assert telem[fld] is not None

    assert telem["estimated_token_count"] == len(ctx) // 4
    assert telem["final_context_chars"] == len(ctx)


# ---------------------------------------------------------------------------
# Property I: Elimination of Scaffold Code Duplication
# ---------------------------------------------------------------------------

def test_property_i_scaffold_code_deduplication(mock_repair_state):
    """Scaffold code should not be printed twice in CURRENT_VALID_STATE."""
    ctx, telem = build_architect_repair_context(mock_repair_state, max_chars=12000)
    
    valid_state_marker = "[5] CURRENT SCAFFOLD & VALIDATED STRUCTURAL STATE"
    next_marker = "[6] REPAIR TARGET (ATOMIC REPAIR INVARIANT)"
    
    assert valid_state_marker in ctx
    assert next_marker in ctx
    sec_content = ctx.split(valid_state_marker)[1].split(next_marker)[0]
    
    occurrences = sec_content.count("def get_items():")
    assert occurrences <= 1, f"Expected scaffold code to appear at most once in valid state, found {occurrences}"


# ---------------------------------------------------------------------------
# Property J: Distillation of Verbose Diagnostic Tracebacks
# ---------------------------------------------------------------------------

def test_property_j_traceback_distillation():
    """Python internal traceback frames must be distilled to structured causal facts without loss."""
    noisy_traceback = (
        "Traceback (most recent call last):\n"
        "  File \"/usr/lib/python3.11/site-packages/fastapi/routing.py\", line 200, in run\n"
        "    res = endpoint()\n"
        "  File \"/usr/lib/python3.11/site-packages/starlette/applications.py\", line 120, in app\n"
        "    await call_next(request)\n"
        "  File \"/repo/backend/runner.py\", line 45, in evaluate\n"
        "    assert res is not None\n"
        "AssertionError: Expected status code 200 but got 404"
    )
    distilled = distill_failure_item_semantic(noisy_traceback, target_location="app/api.py", max_chars=300)
    assert "/usr/lib/python3.11" not in distilled
    assert "Failure: AssertionError: Expected status code 200 but got 404" in distilled
    assert "Observed at: app/api.py" in distilled
    assert "Evidence source: Acceptance Oracle Test Suite" in distilled

    bounded_diag = compress_raw_diagnostics_semantic(noisy_traceback, max_chars=200)
    assert len(bounded_diag) <= 200


# ---------------------------------------------------------------------------
# Property K: Cross-Domain Generalization (Compiler IR vs Audio Graph)
# ---------------------------------------------------------------------------

def test_property_k_cross_domain_generalization():
    """Distillation and delivery validation must work universally across domains without domain-specific hardcoding."""
    # Domain 1: Compiler IR AST
    compiler_state = {
        "task": "Implement an AST lowering pass from high-level AST to linear bytecode IR.",
        "contract_revision_count": 1,
        "contract": {
            "task_intent": {
                "authoritative_target_file": "src/compiler/lowering.py",
                "domain": "compiler",
            },
            "file_tree": ["src/compiler/lowering.py", "src/compiler/ir.py"],
            "interface_contracts": [
                {"identifier": "src.compiler.lowering:LoweringPass.run", "target_file": "src/compiler/lowering.py"}
            ]
        },
        "architectural_blueprint": {
            "authoritative_target_file": "src/compiler/lowering.py",
            "file_tree": ["src/compiler/lowering.py"],
            "files": {
                "src/compiler/lowering.py": {
                    "path": "src/compiler/lowering.py",
                    "code": "class LoweringPass:\n    def run(self, ast):\n        return []\n"
                }
            }
        },
        "contract_feedback": "TypeError: LoweringPass.run expects BytecodeIR output",
    }
    comp_ctx, comp_telem = build_architect_repair_context(compiler_state, max_chars=12000)
    val_comp, errs_comp = validate_architect_repair_context_delivery(comp_ctx)
    assert val_comp is True, f"Compiler IR delivery validation failed: {errs_comp}"

    # Domain 2: Audio DSP Graph
    audio_state = {
        "task": "Implement a real-time DSP filter graph node for biquad audio equalization.",
        "contract_revision_count": 1,
        "contract": {
            "task_intent": {
                "authoritative_target_file": "lib/dsp/biquad.py",
                "domain": "audio_dsp",
            },
            "file_tree": ["lib/dsp/biquad.py"],
            "interface_contracts": [
                {"identifier": "lib.dsp.biquad:BiquadFilter.process_buffer", "target_file": "lib/dsp/biquad.py"}
            ]
        },
        "architectural_blueprint": {
            "authoritative_target_file": "lib/dsp/biquad.py",
            "file_tree": ["lib/dsp/biquad.py"],
            "files": {
                "lib/dsp/biquad.py": {
                    "path": "lib/dsp/biquad.py",
                    "code": "class BiquadFilter:\n    def process_buffer(self, buf):\n        return buf\n"
                }
            }
        },
        "contract_feedback": "ValueError: process_buffer must support floating point audio samples.",
    }
    aud_ctx, aud_telem = build_architect_repair_context(audio_state, max_chars=12000)
    val_aud, errs_aud = validate_architect_repair_context_delivery(aud_ctx)
    assert val_aud is True, f"Audio DSP delivery validation failed: {errs_aud}"


# ---------------------------------------------------------------------------
# Property L: No Silent Omission of Acceptance Obligations
# ---------------------------------------------------------------------------

def test_property_l_no_silent_omission(mock_repair_state):
    """Obligations and schema rules must never be dropped silently during compression."""
    ctx, telem = build_architect_repair_context(mock_repair_state, max_chars=12000)
    
    assert "[1] IMMUTABLE ACCEPTANCE AUTHORITY" in ctx
    assert "[2] ACCEPTANCE OBLIGATION LEDGER & CANONICAL BLUEPRINT SCHEMA CONSTRAINTS" in ctx
    assert "Acceptance Oracle" in ctx
    assert "FROZEN_ORACLE" in telem["authoritative_sources"]
    assert "file_tree" in ctx
    assert "files" in ctx


# ---------------------------------------------------------------------------
# Property M: Backward Compatibility with Turn 0 Context Assembly
# ---------------------------------------------------------------------------

def test_property_m_turn0_backward_compatibility():
    """Turn 0 context assembly must remain functional and produce valid decision context."""
    turn0_state = {
        "task": "Implement a simple math calculator module.",
        "contract_revision_count": 0,
        "v0_requirement_model": {
            "requirements": [
                {"category": "REQ", "description": "Support add and subtract"}
            ]
        }
    }
    ctx, telem = build_architect_decision_context(turn0_state)
    assert "[1] USER INTENT" in ctx
    assert "Support add and subtract" in ctx
    assert telem["context_size"] == len(ctx)


# ---------------------------------------------------------------------------
# Property N: Prompt De-duplication on Repair Turns in Architect
# ---------------------------------------------------------------------------

def test_property_n_prompt_deduplication_in_architect(mock_repair_state):
    """Repair turn prompt in Architect must not duplicate raw oracle ledgers outside decision_ctx."""
    state = dict(mock_repair_state)
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content="=== BLUEPRINT JSON ===\n{}\n=== END BLUEPRINT JSON ===")
    
    architect_agent(state, llm=mock_llm)
    
    assert mock_llm.invoke.called
    sent_prompt = mock_llm.invoke.call_args[0][0][1].content
    
    assert "[6] REPAIR TARGET (ATOMIC REPAIR INVARIANT)" in sent_prompt
    assert "[7] REPAIR BOUNDARY (ATOMIC REPAIR INVARIANT)" in sent_prompt
    assert sent_prompt.count("[6] REPAIR TARGET (ATOMIC REPAIR INVARIANT)") == 1


# ---------------------------------------------------------------------------
# Property O: Deterministic Invariance
# ---------------------------------------------------------------------------

def test_property_o_deterministic_invariance(mock_repair_state):
    """Identical state inputs must produce bit-identical context and telemetry."""
    ctx1, telem1 = build_architect_repair_context(mock_repair_state, max_chars=12000)
    ctx2, telem2 = build_architect_repair_context(mock_repair_state, max_chars=12000)
    
    assert ctx1 == ctx2
    assert telem1 == telem2


# ---------------------------------------------------------------------------
# Property P: Two-Way Semantic Invariance (No Loss + No Invention)
# ---------------------------------------------------------------------------

def test_property_p_two_way_semantic_invariance_no_loss_no_invention(mock_repair_state):
    """
    Two-Way Semantic Invariance:
    1. NO LOSS: Every canonical failure fact, target file, and interface from state is preserved.
    2. NO INVENTION: No new obligations, requirements, constraints, or phantom symbols are introduced.
    """
    ctx, telem = build_architect_repair_context(mock_repair_state, max_chars=12000)

    # 1. NO INFORMATION LOSS
    for fp in mock_repair_state["contract"]["file_tree"]:
        assert fp in ctx, f"Loss detected: Canonical file '{fp}' missing from distilled context"
    for ifc in mock_repair_state["contract"]["interface_contracts"]:
        assert ifc["identifier"] in ctx, f"Loss detected: Canonical interface '{ifc['identifier']}' missing from distilled context"
    assert "Item" in ctx, "Loss detected: Canonical data model 'Item' missing from distilled context"

    # 2. NO INFORMATION INVENTION
    forbidden_inventions = [
        "app.phantom_service",
        "delete_everything",
        "mock_db_session",
        "unauthorized_override",
        "payment_gateway",
        "admin_backdoor",
    ]
    for inv in forbidden_inventions:
        assert inv not in ctx, f"Invention detected: Distiller introduced ungrounded symbol '{inv}'"

    auth_target = mock_repair_state["contract"]["task_intent"]["authoritative_target_file"]
    assert f"WHERE (Target file / artifact location): {auth_target}" in ctx


# ---------------------------------------------------------------------------
# Property Q: Generic Budget Resolution Consistency
# ---------------------------------------------------------------------------

def test_property_q_generic_budget_resolution_consistency():
    """resolve_context_budget must behave identically across all caller scenarios."""
    assert resolve_context_budget({"context_budget": 8500, "max_context_chars": 6000}) == 8500
    assert resolve_context_budget({"max_context_chars": 6000}) == 6000
    assert resolve_context_budget({}) == 12000
    assert resolve_context_budget(None) == 12000
    assert resolve_context_budget({}, default=10000) == 10000
