import pytest
from backend.environment_grounding import (
    GroundingFact,
    EnvironmentGroundingEngine,
    generate_fact_card_for_architect,
    generate_fact_card_for_developer,
)


def test_grounding_fact_dataclass():
    fact = GroundingFact(
        category="ENVIRONMENT_FACT",
        source="python_runtime",
        key="python_version",
        value="3.13.1",
        relevance_scope="python",
        description="Standard Python runtime"
    )
    assert fact.category == "ENVIRONMENT_FACT"
    assert "3.13.1" in fact.to_formatted_line()
    assert "[ENVIRONMENT_FACT]" in fact.to_formatted_line()


def test_collect_environment_facts_python():
    facts = EnvironmentGroundingEngine.collect_environment_facts("python")
    assert len(facts) > 0
    categories = {f.category for f in facts}
    assert "ENVIRONMENT_FACT" in categories
    
    # Check that python runtime is captured
    py_facts = [f for f in facts if f.key == "language_runtime"]
    assert len(py_facts) >= 1
    assert "Python" in py_facts[0].value


def test_collect_environment_facts_dart():
    facts = EnvironmentGroundingEngine.collect_environment_facts("dart")
    assert len(facts) > 0
    scopes = {f.relevance_scope for f in facts}
    assert "dart" in scopes or "global" in scopes


def test_filter_relevant_facts_scope_isolation():
    facts = [
        GroundingFact(category="ENVIRONMENT_FACT", source="pip", key="fastapi", value="0.115", relevance_scope="python"),
        GroundingFact(category="ENVIRONMENT_FACT", source="pubspec", key="riverpod", value="2.5", relevance_scope="dart"),
        GroundingFact(category="ENVIRONMENT_FACT", source="os", key="os_arch", value="win32", relevance_scope="global"),
    ]
    
    # Filtering for python must exclude dart facts
    py_filtered = EnvironmentGroundingEngine.filter_relevant_facts(facts, "python")
    keys_py = [f.key for f in py_filtered]
    assert "fastapi" in keys_py
    assert "os_arch" in keys_py
    assert "riverpod" not in keys_py

    # Filtering for dart must exclude python facts
    dart_filtered = EnvironmentGroundingEngine.filter_relevant_facts(facts, "dart")
    keys_dart = [f.key for f in dart_filtered]
    assert "riverpod" in keys_dart
    assert "os_arch" in keys_dart
    assert "fastapi" not in keys_dart


def test_filter_relevant_facts_active_token_prioritization():
    facts = [
        GroundingFact(category="ENVIRONMENT_FACT", source="pip", key="pytest", value="8.0", relevance_scope="python", description="Test runner"),
        GroundingFact(category="ENVIRONMENT_FACT", source="pip", key="pydantic", value="2.10", relevance_scope="python", description="Data validation"),
    ]
    # If active error references "pydantic", it must be prioritized to front
    prioritized = EnvironmentGroundingEngine.filter_relevant_facts(facts, "python", active_tokens=["pydantic"])
    assert prioritized[0].key == "pydantic"


def test_format_grounding_block_epistemic_grouping():
    facts = [
        GroundingFact(category="ENVIRONMENT_FACT", source="sys", key="runtime", value="Python 3.13", relevance_scope="python"),
        GroundingFact(category="DOCUMENTATION_FACT", source="catalog", key="api_rule", value="v2 migration", relevance_scope="python", description="Breaking change in v2"),
        GroundingFact(category="RUNTIME_FACT", source="compiler", key="observed_feedback_1", value="exit_code=1", relevance_scope="python"),
    ]
    output = EnvironmentGroundingEngine.format_grounding_block(facts, title="TEST GROUNDING")
    assert "[TEST GROUNDING]" in output
    assert "--- ENVIRONMENT_FACT ---" in output
    assert "--- DOCUMENTATION_FACT ---" in output
    assert "--- RUNTIME_FACT ---" in output
    assert "Grounding ini memperkaya fakta teknis" in output


def test_dynamic_runtime_facts_inclusion():
    dynamic = ["Error: No named parameter with the name 'data'"]
    facts = EnvironmentGroundingEngine.collect_environment_facts("dart", dynamic_runtime_facts=dynamic)
    runtime_facts = [f for f in facts if f.category == "RUNTIME_FACT"]
    assert len(runtime_facts) == 1
    assert "No named parameter" in runtime_facts[0].value
