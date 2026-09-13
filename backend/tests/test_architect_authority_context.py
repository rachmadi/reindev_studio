"""
Tests for Architect Authority-Verified Context Package (context_hardening.py).
Verifies:
1. Section [5] ORACLE-DERIVED INTERFACES originates ONLY from authoritative test suites.
2. PM draft is labeled PM_PROPOSAL and never FROZEN/ORACLE-DERIVED.
3. Explicit authority tags: ORACLE_FACT, PM_PROPOSAL, ARCHITECT_INFERENCE.
4. Deterministic consistency check: highest authority (ORACLE_FACT) wins, conflicts logged.
"""

import pytest
from backend.context_hardening import (
    extract_authoritative_oracle_interfaces,
    check_and_resolve_authority_conflicts,
    build_architect_decision_context,
)


class TestAuthoritativeOracleExtractor:
    """Test extract_authoritative_oracle_interfaces across test suites."""

    def test_extracts_fastapi_endpoints_and_symbols(self):
        state = {
            "test_files": {
                "test_api.py": (
                    "from fastapi.testclient import TestClient\n"
                    "import main\n\n"
                    "def test_endpoints():\n"
                    "    client = TestClient(main.app)\n"
                    "    r = client.get('/products')\n"
                    "    r2 = client.post('/orders')\n"
                    "    assert hasattr(main, 'Product')\n"
                )
            }
        }
        interfaces = extract_authoritative_oracle_interfaces(state)
        assert any("/products [GET]" in ifc for ifc in interfaces)
        assert any("/orders [POST]" in ifc for ifc in interfaces)
        assert any("Product" in ifc for ifc in interfaces)
        assert all("[ORACLE_FACT]" in ifc for ifc in interfaces)

    def test_extracts_dart_tested_widgets(self):
        state = {
            "test_files": {
                "widget_test.dart": (
                    "import 'package:flutter_test/flutter_test.dart';\n"
                    "import 'package:app/main.dart';\n\n"
                    "void main() {\n"
                    "  testWidgets('renders card', (tester) async {\n"
                    "    await tester.pumpWidget(const MetricCard(title: 'CPU', value: 42.0));\n"
                    "    expect(find.byType(CardMetric), findsOneWidget);\n"
                    "  });\n"
                    "}\n"
                )
            }
        }
        interfaces = extract_authoritative_oracle_interfaces(state)
        assert any("CardMetric" in ifc for ifc in interfaces)
        assert any("MetricCard" in ifc for ifc in interfaces)
        assert all("[ORACLE_FACT]" in ifc for ifc in interfaces)


class TestArchitectContextAuthorityHardening:
    """Test build_architect_decision_context authority labeling and consistency check."""

    def test_draft_contract_labeled_pm_proposal_not_frozen(self):
        state = {
            "task": "Build calculator CLI",
            "contract_status": "DRAFT",
            "contract": {
                "interface_contracts": [{"identifier": "add_numbers"}],
                "data_models": [{"model_name": "CalcRequest"}],
            },
            "test_files": {
                "test_main.py": "import main\ndef test_calc(): assert hasattr(main, 'calculate')\n"
            }
        }
        ctx, telem = build_architect_decision_context(state)

        # Section 4 must be PM_PROPOSAL
        assert "[4] PROPOSED CONTRACT SPECIFICATION (PM_PROPOSAL" in ctx
        assert "Interfaces [PM_PROPOSAL]: add_numbers" in ctx
        assert "NOT acceptance authority" in ctx

        # Section 5 must be ORACLE_FACT derived from test suite
        assert "[5] AUTHORITATIVE ACCEPTANCE ORACLE INTERFACES (ORACLE_FACT" in ctx
        assert "[ORACLE_FACT] calculate" in ctx

        # PM proposal must NOT be labeled FROZEN in Section 5
        assert "[ORACLE_FACT] add_numbers" not in ctx

    def test_frozen_contract_labeled_oracle_fact(self):
        state = {
            "task": "Build calculator CLI",
            "contract_status": "FROZEN",
            "contract_sha256": "abcdef1234567890abcdef1234567890",
            "contract": {
                "interface_contracts": [{"identifier": "calculate"}],
            },
            "test_files": {}
        }
        ctx, telem = build_architect_decision_context(state)
        assert "[4] FROZEN CONTRACT SPECIFICATION (ORACLE_FACT" in ctx
        assert "SHA-256 Seal: abcdef1234567890" in ctx

    def test_deterministic_authority_conflict_resolution(self):
        """
        Verify that when a lower authority (PM Proposal or Repair boundary) conflicts
        with an ORACLE_FACT, ORACLE_FACT wins and conflict is reported.
        """
        sections = {
            "authority_oracle_interfaces": "[5] ORACLE-DERIVED\n  - [ORACLE_FACT] calculate (Tested module symbol)",
            "requirement_repair_boundary": "[10] REPAIR BOUNDARY\nFORBIDDEN:\n  x do not modify calculate",
        }
        state = {
            "contract_status": "PROPOSED",
            "contract": {
                "interface_contracts": [{"identifier": "compute"}]  # PM proposed compute instead of calculate
            }
        }

        updated_sections, conflicts = check_and_resolve_authority_conflicts(sections, state)
        assert len(conflicts) >= 1
        assert any("calculate" in c and "ORACLE_FACT" in c for c in conflicts)
        assert "AUTHORITY CONFLICT RESOLUTIONS" in updated_sections["evidence_violations"]
