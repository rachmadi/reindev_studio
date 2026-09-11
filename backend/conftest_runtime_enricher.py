# -*- coding: utf-8 -*-
"""
Generic Runtime Evidence Enrichment Plugin for Pytest.
Captures structured diagnostic evidence on test failure:
1. HTTP Response Diagnostic: status code -> response body -> validation detail
2. Exception Diagnostic: exception type -> message -> source location
3. Assertion Diagnostic: actual -> expected -> failure location
"""
import sys
import json

try:
    import pytest
except ImportError:
    pytest = None

if pytest is not None:
    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(item, call):
        outcome = yield
        report = outcome.get_result()
        if report.when == "call" and report.failed:
            _extract_generic_diagnostics(item, call, report)


def _extract_generic_diagnostics(item, call, report):
    if not getattr(call, "excinfo", None):
        return

    extracted_http = False

    # 1. Walk traceback frames to find any HTTP Response objects
    tb = getattr(call.excinfo, "tb", None)
    curr = tb
    while curr and not extracted_http:
        frame = getattr(curr, "tb_frame", None)
        f_locals = getattr(frame, "f_locals", {}) if frame else {}
        for var_name, var_val in list(f_locals.items()):
            if hasattr(var_val, "status_code"):
                status_code = getattr(var_val, "status_code", None)
                if isinstance(status_code, int):
                    body_text = None
                    if hasattr(var_val, "text"):
                        body_text = str(var_val.text)
                    elif hasattr(var_val, "content"):
                        try:
                            body_text = var_val.content.decode("utf-8", errors="replace")
                        except Exception:
                            body_text = str(var_val.content)
                    elif hasattr(var_val, "json"):
                        try:
                            j = var_val.json() if callable(var_val.json) else var_val.json
                            body_text = json.dumps(j)
                        except Exception:
                            pass

                    val_detail = None
                    if body_text:
                        try:
                            parsed = json.loads(body_text)
                            if isinstance(parsed, dict) and "detail" in parsed:
                                val_detail = json.dumps(parsed["detail"])
                            elif isinstance(parsed, (dict, list)):
                                val_detail = json.dumps(parsed)
                        except Exception:
                            val_detail = body_text[:500]

                    sys.stderr.write("\n--- [GENERIC RUNTIME DIAGNOSTIC EVIDENCE] ---\n")
                    sys.stderr.write("Type: HTTP_RESPONSE_DIAGNOSTIC\n")
                    sys.stderr.write(f"Status Code: {status_code}\n")
                    if body_text:
                        sys.stderr.write(f"Response Body: {body_text[:1000]}\n")
                    if val_detail:
                        sys.stderr.write(f"Validation Detail: {val_detail}\n")
                    sys.stderr.write("---------------------------------------------\n\n")
                    sys.stderr.flush()
                    extracted_http = True
                    break
        curr = getattr(curr, "tb_next", None)

    # 2. Generic Exception Diagnostic (if not standard assertion failure)
    exc_type = getattr(call.excinfo, "type", None)
    if exc_type is not None and exc_type.__name__ != "AssertionError":
        sys.stderr.write("\n--- [GENERIC RUNTIME DIAGNOSTIC EVIDENCE] ---\n")
        sys.stderr.write("Type: EXCEPTION_DIAGNOSTIC\n")
        sys.stderr.write(f"Exception Type: {exc_type.__name__}\n")
        sys.stderr.write(f"Exception Message: {str(call.excinfo.value)}\n")
        sys.stderr.write("---------------------------------------------\n\n")
        sys.stderr.flush()
