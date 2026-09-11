# -*- coding: utf-8 -*-
"""
Unit Tests for Generic Runtime Evidence Enrichment (R-1) and Caller-Callee Schema Compatibility (R-2)
ReinDev Studio — Staged Causal Evidence & Observability Architecture

Verifikasi deterministik:
1. Generic HTTP 422 capture & extraction (status code -> response body -> validation detail)
2. Generic HTTP 400 capture & extraction
3. Generic Exception diagnostic capture (type -> message)
4. Frozen Oracle immutability preservation when enricher active (zero file mutation)
5. Caller-Callee Schema Compatibility audit detects interface mismatch
6. Caller-Callee Schema Compatibility audit returns None when interfaces compatible
7. Non-solver guarantee on RX-B5-CONTRACT-SCHEMA-MISMATCH (factual disparity without solver dictation)
8. Evidence rendering includes [GENERIC RUNTIME DIAGNOSTIC EVIDENCE] in render_repair_directive
"""

import os
import sys
import json
import tempfile
import hashlib
import subprocess
import pytest

from backend.context_assembler import (
    extract_generic_runtime_diagnostics,
    audit_caller_callee_schema_compatibility,
    assemble_b5_evidence,
    synthesize_b5_actionable_prescriptions,
)
from backend.contextual_evidence import (
    ContextualEvidencePackage,
    ViolationItem,
    render_repair_directive,
)


def test_generic_http_422_capture_and_extraction():
    """R-1: Memverifikasi penangkapan respons HTTP 422 beserta response body dan validation detail."""
    test_code = """
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    name: str
    price: float
    quantity: int

@app.post("/items", status_code=201)
def create(item: Item):
    return item

def test_create_item():
    client = TestClient(app)
    response = client.post("/items", json={"name": "Widget", "price": 10.5})
    assert response.status_code == 201
"""
    with tempfile.TemporaryDirectory() as td:
        tfile = os.path.join(td, "test_sample.py")
        with open(tfile, "w", encoding="utf-8") as f:
            f.write(test_code)

        backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        env = os.environ.copy()
        env["PYTHONPATH"] = backend_dir

        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-p", "conftest_runtime_enricher", tfile],
            cwd=td,
            env=env,
            capture_output=True,
            text=True,
        )

        full_output = (proc.stdout + "\n" + proc.stderr).strip()
        assert "--- [GENERIC RUNTIME DIAGNOSTIC EVIDENCE] ---" in full_output
        assert "Status Code: 422" in full_output

        diagnostics = extract_generic_runtime_diagnostics(full_output)
        assert len(diagnostics) >= 1
        diag = diagnostics[0]
        assert diag.get("type") == "HTTP_RESPONSE_DIAGNOSTIC"
        assert diag.get("status_code") == 422
        assert "quantity" in str(diag.get("validation_detail")) or "quantity" in str(diag.get("response_body"))


def test_generic_http_400_capture_and_extraction():
    """R-1: Memverifikasi penangkapan respons HTTP 400 Bad Request."""
    test_code = """
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

app = FastAPI()

@app.get("/items/{item_id}")
def get_item(item_id: int):
    if item_id < 0:
        raise HTTPException(status_code=400, detail="Invalid negative item ID")
    return {"id": item_id}

def test_negative_id():
    client = TestClient(app)
    response = client.get("/items/-5")
    assert response.status_code == 200
"""
    with tempfile.TemporaryDirectory() as td:
        tfile = os.path.join(td, "test_sample.py")
        with open(tfile, "w", encoding="utf-8") as f:
            f.write(test_code)

        backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        env = os.environ.copy()
        env["PYTHONPATH"] = backend_dir

        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-p", "conftest_runtime_enricher", tfile],
            cwd=td,
            env=env,
            capture_output=True,
            text=True,
        )

        full_output = (proc.stdout + "\n" + proc.stderr).strip()
        assert "--- [GENERIC RUNTIME DIAGNOSTIC EVIDENCE] ---" in full_output
        assert "Status Code: 400" in full_output

        diagnostics = extract_generic_runtime_diagnostics(full_output)
        assert len(diagnostics) >= 1
        diag = diagnostics[0]
        assert diag.get("status_code") == 400
        assert "Invalid negative item ID" in str(diag.get("response_body")) or "Invalid negative item ID" in str(diag.get("validation_detail"))


def test_generic_exception_capture():
    """R-1: Memverifikasi penangkapan generic unhandled exception."""
    test_code = """
def test_unhandled_exception():
    raise ValueError("Incompatible dimensions: matrix (2,3) vs (4,5)")
"""
    with tempfile.TemporaryDirectory() as td:
        tfile = os.path.join(td, "test_sample.py")
        with open(tfile, "w", encoding="utf-8") as f:
            f.write(test_code)

        backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        env = os.environ.copy()
        env["PYTHONPATH"] = backend_dir

        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-p", "conftest_runtime_enricher", tfile],
            cwd=td,
            env=env,
            capture_output=True,
            text=True,
        )

        full_output = (proc.stdout + "\n" + proc.stderr).strip()
        assert "--- [GENERIC RUNTIME DIAGNOSTIC EVIDENCE] ---" in full_output
        assert "Type: EXCEPTION_DIAGNOSTIC" in full_output

        diagnostics = extract_generic_runtime_diagnostics(full_output)
        assert len(diagnostics) >= 1
        diag = diagnostics[0]
        assert diag.get("exception_type") == "ValueError"
        assert "Incompatible dimensions" in diag.get("exception_message", "")


def test_frozen_oracle_immutability_with_enricher():
    """R-1: Memverifikasi bahwa conftest_runtime_enricher tidak memutasi berkas Oracle/test apa pun."""
    test_code = """
def test_ok():
    assert 1 == 1
"""
    with tempfile.TemporaryDirectory() as td:
        tfile = os.path.join(td, "test_oracle.py")
        with open(tfile, "w", encoding="utf-8") as f:
            f.write(test_code)

        sha_before = hashlib.sha256(open(tfile, "rb").read()).hexdigest()

        backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        env = os.environ.copy()
        env["PYTHONPATH"] = backend_dir

        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-p", "conftest_runtime_enricher", tfile],
            cwd=td,
            env=env,
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0

        sha_after = hashlib.sha256(open(tfile, "rb").read()).hexdigest()
        assert sha_before == sha_after, "Frozen Oracle file was mutated by test runner!"


def test_audit_caller_callee_schema_compatibility_detects_mismatch():
    """R-2: Memverifikasi deteksi disparitas skema caller-callee."""
    test_code = """
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_create_product():
    payload = {"name": "Mechanical Keyboard", "quantity": 15}
    response = client.post("/products", json=payload)
    assert response.status_code == 201
"""
    impl_code = """
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Product(BaseModel):
    name: str
    price: float
    quantity: int

@app.post("/products", status_code=201)
def create_product(product: Product):
    return product
"""
    test_files = {"test_main.py": test_code}
    code_files = {"main.py": impl_code}

    audit = audit_caller_callee_schema_compatibility(test_files, code_files, target_language="python")
    assert audit is not None, "Should detect schema disparity"
    assert audit["endpoint"] == "/products"
    assert audit["caller_keys"] == ["name", "quantity"]
    assert audit["callee_symbol"] == "Product"
    assert "price" in audit["missing_in_caller"]


def test_audit_caller_callee_schema_compatibility_no_mismatch_when_compatible():
    """R-2: Memverifikasi bahwa ketika model memiliki default value, tidak ada disparitas."""
    test_code = """
from fastapi.testclient import TestClient
from main import app
client = TestClient(app)

def test_create_product():
    response = client.post("/products", json={"name": "Mechanical Keyboard", "quantity": 15})
    assert response.status_code == 201
"""
    impl_code = """
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Product(BaseModel):
    name: str
    quantity: int
    price: float = 0.0

@app.post("/products", status_code=201)
def create_product(product: Product):
    return product
"""
    test_files = {"test_main.py": test_code}
    code_files = {"main.py": impl_code}

    audit = audit_caller_callee_schema_compatibility(test_files, code_files, target_language="python")
    assert audit is None, "Should not detect disparity when all omitted fields have default values"


def test_prescription_non_solver_guarantee():
    """R-2: Memverifikasi preskripsi RX-B5-CONTRACT-SCHEMA-MISMATCH mematuhi prinsip non-solver."""
    test_code = """
def test_create_product():
    payload = {"name": "Mechanical Keyboard", "quantity": 15}
    response = client.post("/products", json=payload)
    assert response.status_code == 201
"""
    impl_code = """
class Product(BaseModel):
    name: str
    price: float
    quantity: int

@app.post("/products", status_code=201)
def create_product(product: Product):
    return product
"""
    output = "FAILED test_main.py::test_create_product - assert 422 == 201\nE   assert 422 == 201"
    state = {
        "run_id": "test_r2",
        "iteration_count": 1,
        "max_iterations": 10,
        "target_language": "python",
        "code_files": {"main.py": impl_code},
        "test_files": {"test_main.py": test_code},
        "contract": {"task_intent": {"authoritative_target_file": "main.py"}},
    }
    violations = [
        ViolationItem(
            violation_id="VIO-B5-001",
            criterion="sandbox_tests_passed",
            severity="CRITICAL",
            location="sandbox_runner",
            observed_state="1 test(s) failed with exit code 1",
            expected_state="All sandbox tests pass with exit code 0",
            source_detector="B5_EXECUTOR_ITERATION",
        )
    ]

    prescriptions = synthesize_b5_actionable_prescriptions(
        state=state,
        violations=violations,
        output=output,
        target_lang="python",
        auth_file="main.py",
    )

    schema_rx = [p for p in prescriptions if p.prescription_id == "RX-B5-CONTRACT-SCHEMA-MISMATCH"]
    assert len(schema_rx) == 1, "Must synthesize RX-B5-CONTRACT-SCHEMA-MISMATCH"
    rx = schema_rx[0]

    # Non-solver guarantee checks:
    # 1. Stated as factual observation
    assert "Observed contract mismatch: caller supplies" in rx.observed_failure
    assert "caller supplies ['name', 'quantity']" in rx.required_change
    assert "Repair the request/response interface so the implementation accepts the authoritative caller representation" in rx.required_change

    # 2. MUST NOT dictate specific code implementation
    forbidden_solver_phrases = [
        "beri default",
        "default 0.0",
        "price = 0.0",
        "set default value to 0.0",
        "tambahkan field",
    ]
    for phrase in forbidden_solver_phrases:
        assert phrase not in rx.required_change.lower(), f"Prescription violated non-solver principle with: '{phrase}'"


def test_render_repair_directive_includes_runtime_diagnostic():
    """R-1 & V5-2: Memverifikasi render_repair_directive menyertakan Generic Runtime Diagnostics."""
    pkg = ContextualEvidencePackage.from_dict({
        "package_id": "CEP-B5-TEST-001",
        "timestamp": "2026-09-12T00:00:00Z",
        "validator": "B5_EXECUTOR_ITERATION",
        "phase": "EXECUTOR",
        "validator_type": "ITERATION",
        "verdict": "FAIL",
        "causal_owner": "DEVELOPER",
        "failure_summary": "Sandbox execution failed: 1 test(s) failed (exit_code=1, passed=0).",
        "root_causes": ["Sandbox test failure (exit_code=1, failed=1)."],
        "violations": [],
        "evidence": [
            {
                "item": "generic_runtime_diagnostic",
                "evidence_class": "DETERMINISTIC",
                "observed": [
                    {
                        "type": "HTTP_RESPONSE_DIAGNOSTIC",
                        "status_code": 422,
                        "response_body": {"detail": [{"type": "missing", "loc": ["body", "price"], "msg": "Field required"}]},
                        "validation_detail": [{"type": "missing", "loc": ["body", "price"], "msg": "Field required"}],
                    }
                ],
                "expected": "Clean execution without HTTP error status",
                "status": "INVALID",
            }
        ],
    })

    rendered = render_repair_directive(pkg)
    assert "[DETERMINISTIC SANDBOX FAILURE EVIDENCE]" in rendered
    assert "Generic Runtime Diagnostics:" in rendered
    assert "Type: HTTP_RESPONSE_DIAGNOSTIC" in rendered
    assert "Status Code: 422" in rendered
    assert "Validation Detail:" in rendered
    assert "body" in rendered and "price" in rendered
