"""
test_environment_grounding.py
=============================
Unit tests untuk Universal Environment Grounding Framework:
- Manifest scanner (pubspec.lock, package.json)
- Declarative Knowledge Catalog & SemVer matching
- Fact card generation untuk Architect & Developer
- Positive canonical template injection
- Actionable semantic hint untuk undefined symbols
"""

import sys
from pathlib import Path
import pytest

from backend.knowledge_catalog import (
    catalog,
    DeprecationRule,
    KnowledgeCatalog,
    parse_semver,
    semver_matches,
)
from backend.environment_grounding import (
    parse_pubspec_lock,
    parse_package_json,
    find_active_manifest_packages,
    generate_fact_card_for_architect,
    generate_fact_card_for_developer,
    generate_fact_card,
)
from backend.diagnostic_parser import (
    FailingTest,
    infer_semantic_hint,
    HINT_GROUNDING_UNDEFINED_SYMBOL,
)


# ---------------------------------------------------------------------------
# 1. SemVer Matching & Knowledge Catalog Tests
# ---------------------------------------------------------------------------

def test_parse_semver():
    assert parse_semver("2.5.1") == (2, 5, 1)
    assert parse_semver("3.0.0") == (3, 0, 0)
    assert parse_semver("1") == (1, 0, 0)
    assert parse_semver("2.4") == (2, 4, 0)
    assert parse_semver(None) == (0, 0, 0)


def test_semver_matches():
    # Riverpod >= 2.0.0
    assert semver_matches("2.5.1", version_min="2.0.0") is True
    assert semver_matches("3.4.3", version_min="2.0.0") is True
    assert semver_matches("1.0.3", version_min="2.0.0") is False

    # Pydantic v1 (< 2.0.0)
    assert semver_matches("1.10.8", version_max="2.0.0") is True
    assert semver_matches("2.5.0", version_max="2.0.0") is False

    # In between [1.0.0, 2.0.0)
    assert semver_matches("1.5.0", version_min="1.0.0", version_max="2.0.0") is True
    assert semver_matches("2.0.0", version_min="1.0.0", version_max="2.0.0") is False


def test_knowledge_catalog_riverpod_v3():
    packages = {"flutter_riverpod": "3.4.3"}
    rules = catalog.get_matching_rules("dart", packages)
    rule_ids = [r.id for r in rules]
    assert "riverpod_v2_plus_no_state_notifier" in rule_ids
    rule = next(r for r in rules if r.id == "riverpod_v2_plus_no_state_notifier")
    assert "StateNotifier" in rule.prohibited_patterns
    assert "Provider<CardMetricData>" in rule.positive_template


def test_knowledge_catalog_pydantic_v2():
    packages = {"pydantic": "2.10.0"}
    rules = catalog.get_matching_rules("python", packages)
    rule_ids = [r.id for r in rules]
    assert "pydantic_v2_modern_validators" in rule_ids
    assert "pydantic_v1_legacy_support" not in rule_ids


# ---------------------------------------------------------------------------
# 2. Manifest Parser Tests
# ---------------------------------------------------------------------------

def test_parse_pubspec_lock_sandbox():
    sandbox_lock = Path(__file__).parent / "sandbox" / "pubspec.lock"
    if sandbox_lock.exists():
        pkgs = parse_pubspec_lock(sandbox_lock)
        assert "flutter_riverpod" in pkgs
        assert pkgs["flutter_riverpod"] == "3.4.3"


def test_parse_package_json(tmp_path):
    pkg_json = tmp_path / "package.json"
    pkg_json.write_text('{"dependencies": {"react": "^18.2.0", "axios": "~1.4.0"}}', encoding="utf-8")
    pkgs = parse_package_json(pkg_json)
    assert pkgs["react"] == "18.2.0"
    assert pkgs["axios"] == "1.4.0"


# ---------------------------------------------------------------------------
# 3. Fact Card Generation Tests (Architect vs Developer)
# ---------------------------------------------------------------------------

def test_generate_fact_card_architect_dart():
    card = generate_fact_card_for_architect("dart", task="buat card metric widget")
    assert "[ENVIRONMENT FACTS" in card
    assert "ARCHITECTURAL CONSTRAINTS" in card
    assert "flutter_riverpod: 3.4.3" in card or "flutter_riverpod" in card
    assert "StateNotifier" in card
    assert "SIMBOL TERLARANG" in card


def test_generate_fact_card_developer_dart():
    card = generate_fact_card_for_developer("dart", task="buat card metric widget")
    assert "[ENVIRONMENT FACT CARD" in card
    assert "AUTHORITATIVE PRECEDENCE" in card
    assert "POLA KANONIKAL YANG WAJIB DIGUNAKAN" in card
    assert "Provider<CardMetricData>" in card
    # Pastikan tidak ada ambiguitas "StateNotifierProvider HANYA di riverpod <2.0"
    assert "HANYA di riverpod <2.0" not in card


def test_generate_fact_card_developer_python():
    card = generate_fact_card_for_developer("python", task="buat API inventaris")
    assert "pydantic" in card
    assert "AUTHORITATIVE PRECEDENCE" in card
    assert "@field_validator" in card
    assert "ConfigDict" in card


# ---------------------------------------------------------------------------
# 4. Actionable Diagnostic Hint for Undefined Symbols
# ---------------------------------------------------------------------------

def test_infer_semantic_hint_undefined_symbol():
    test_comp = FailingTest(
        test_name="compilation_check",
        test_file="test/card_metric_test.dart",
        failure_type="compilation_error",
        message="Error: The type 'StateNotifier' isn't defined.",
        source_file="lib/card_metric.dart",
    )
    hint = infer_semantic_hint(test_comp)
    assert hint == HINT_GROUNDING_UNDEFINED_SYMBOL
    assert "ENVIRONMENT FACT CARD" in hint
