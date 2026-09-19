# FORENSIC RCA — FASTAPI ARCHITECT SEMANTIC MAPPING v1
**Run ID:** `pv_pilot_fastapi_t1_rep1_20260919_062116`  
**Evaluation Scope:** Forensic Root Cause Analysis on Architect Semantic Decision & Authority Binding  
**Governance Protocol:** Evidence-First | No Modification | No Rerun | Epistemic Labelling  

---

## 1. Executive Finding

- **Core Finding:** `[OBSERVED FACT]` During the controlled 1×3 pilot for Treatment *Architect Authority Binding v1*, the FastAPI Architect failed to generate an `ArchitecturalBlueprint` matching the Frozen Acceptance Authority, resulting in deterministic contract status `REJECTED` and 0 Developer execution loops.
- **Direct Cause:** `[OBSERVED FACT]` The Frozen Oracle defined 4 public HTTP endpoint obligations (`POST /products`, `GET /products`, `GET /products/{id}`, `DELETE /products/{id}`). The Architect model (`qwen2.5-coder:7b`) received all 4 obligations explicitly in its prompt (Section `[2]`), but failed to emit route or method bindings. Instead, it substituted the public HTTP endpoints with 6 internal Python callables (`Product`, `create_product`, `delete_product`, `get_all_products`, `get_product_by_id`, `update_product`) without route decorators (`@app.post`, `@app.get`, `@app.delete`) or blueprint route metadata (`route: null`, `method: null`).
- **Pipeline Integrity:** `[OBSERVED FACT]` The deterministic Authority Binding Gate functioned exactly as designed: it detected that 0/4 authoritative obligations had declared interface coverage in the blueprint, classified the mismatch under dimension `ROUTE_METHOD`, and blocked the contract from reaching `FROZEN` status.
- **Classification:** `[STRONG EVIDENCE]` Primary: **`ARCHITECT`**. Sub-type: **`semantic mapping failure`** (the model performed semantic substitution from public HTTP interface to internal service functions).

---

## 2. Exact Architect Input Reconstruction

`[OBSERVED FACT]` Architect Turn 0 was invoked at timestamp `2026-09-19T06:24:15.460051` and completed synthesis at `2026-09-19T06:26:09.152265` (Wall time: 113.68s, input characters: 20,704, estimated input tokens: 5,176 within Ollama `num_ctx: 8192`).

The exact prompt delivered to the model consisted of two messages:

### System Message: `ARCHITECT_SYSTEM_PROMPT` (7,763 chars)
- Defines the role of Senior Software & System Architect.
- Mandates canonical JSON output in `=== BLUEPRINT JSON === ... === END BLUEPRINT JSON ===`.
- Provides canonical schema example containing `file_tree`, `files`, `code_scaffold`, `interface_contracts`, and `data_models`.
- Invariant 1 dictates: `code_scaffold HANYA berupa interface signatures dan stubs minimal (misal: deklarasi kelas, fungsi, metode dengan pass atau return dummy)`.
- Invariant 3 establishes: `Acceptance Oracle adalah Acceptance Authority (WHAT). Canonical Schema dan Governance menentukan aturan validitas struktur. Architect adalah Design Authority (HOW).`
- Invariant 6 specifies: `Elemen 'parameters' pada interface_contracts WAJIB menggunakan field kanonikal: param_name, param_type, param_location ('PATH', 'QUERY', 'BODY', 'ARGUMENT', atau 'PROP'), dan is_required`.

### Human Message: Assembled Turn 0 Context (12,941 chars)
Composed of 5 numbered sections:
1. `[1] USER INTENT / V0 REQUIREMENTS (EPISTEMIC GROUNDING FACTS)` (1,235 chars):
   - User Task: `"Bangun modul REST API FastAPI untuk manajemen inventaris produk dengan operasi CRUD lengkap dan validasi data."`
   - V0 Requirements: 6 requirement items covering CRUD operations, Pydantic validation, error handling, and in-memory storage.
2. `[2] ACCEPTANCE OBLIGATION LEDGER (AUTHORITATIVE ACCEPTANCE OBLIGATIONS)` (4,225 chars):
   - Formatted ledger containing all 4 canonical obligations extracted from `frozen_oracle/fastapi_t1/test_main.py`.
   - Acceptance behavior and 5 canonical scenarios extracted from test cases.
3. `[3] PM SPECIFICATION (PROPOSAL — DESIGN REFERENCE ONLY)` (3,474 chars):
   - PM narrative specification produced in Turn 0.
   - Explicit authority override banner: `"Aturan Otoritas: Jika terdapat perbedaan atau konflik antara PM Proposal dengan [2] ACCEPTANCE OBLIGATION LEDGER, maka [2] ACCEPTANCE OBLIGATION LEDGER MUTLAK MENANG."`
4. `[4] BLUEPRINT SCHEMA & CANONICAL OUTPUT SPECIFICATION` (1,152 chars):
   - Exact fields required in the JSON root: `authoritative_target_file`, `file_tree`, `architecture_summary`, `files`, `interface_contracts`, `data_models`.
5. `[5] ARCHITECT CONSTRUCTION RULES & PRE-SEAL SELF-REVIEW` (2,855 chars):
   - Mandate: `"Setiap obligasi dari [2] WAJIB terwakili di interface_contracts atau data_models"`.
   - Pre-seal item 4: `"Apakah SELURUH obligasi publik dalam [2] ACCEPTANCE OBLIGATION LEDGER dan alur skenario penerimaan telah memiliki padanan deklarasi eksplisit di interface_contracts atau data_models?"`.

---

## 3. Authority Visibility

`[OBSERVED FACT]` All 4 public HTTP endpoints were **100% EXPLICITLY VISIBLE** to the Architect model prior to generation in Turn 0.

Section `[2]` delivered the following exact text representation for each endpoint:

```text
1. Obligation ID: OBL-HTTP-POST-products
   Authority: FROZEN_ORACLE
   Kind: INTERACTION
   Public Identity: /products
   Inputs: {'http_method': 'POST', 'raw_path': '/products', 'payload_fields': ['name', 'quantity']}
   Outputs: {'expected_status': 201, 'response_fields': ['name', 'quantity', 'id']}
   Observable Behavior: HTTP endpoint '/products' accepting POST method (expected status: 201)
   Acceptance Evidence: client.post('/products')
   Source Reference: test_main.py:10

2. Obligation ID: OBL-HTTP-GET-products
   Authority: FROZEN_ORACLE
   Kind: INTERACTION
   Public Identity: /products
   Inputs: {'http_method': 'GET', 'raw_path': '/products'}
   Outputs: {'expected_status': 200}
   Observable Behavior: HTTP endpoint '/products' accepting GET method (expected status: 200)
   Acceptance Evidence: client.get('/products')
   Source Reference: test_main.py:19

3. Obligation ID: OBL-HTTP-GET-products_id
   Authority: FROZEN_ORACLE
   Kind: INTERACTION
   Public Identity: /products/{id}
   Inputs: {'http_method': 'GET', 'raw_path': '/products/{id}'}
   Outputs: {'expected_status': 200, 'response_fields': ['name', 'quantity']}
   Observable Behavior: HTTP endpoint '/products/{id}' accepting GET method (expected status: 200)
   Acceptance Evidence: client.get('/products/{id}')
   Source Reference: test_main.py:31

4. Obligation ID: OBL-HTTP-DELETE-products_id
   Authority: FROZEN_ORACLE
   Kind: INTERACTION
   Public Identity: /products/{id}
   Inputs: {'http_method': 'DELETE', 'raw_path': '/products/{id}'}
   Outputs: {'expected_status': 204}
   Observable Behavior: HTTP endpoint '/products/{id}' accepting DELETE method (expected status: 204)
   Acceptance Evidence: client.delete('/products/{id}')
   Source Reference: test_main.py:42
```

In addition, all 5 ground truth test stimuli were presented:
- Stimulus 1: `POST /products` (status 201)
- Stimulus 2: `GET /products` (status 200)
- Stimulus 3: `GET f'/products/{prod_id}'` (status 200)
- Stimulus 4: `DELETE f'/products/{prod_id}'` (status 204)
- Stimulus 5: `DELETE /products/999999` (status 404)

`[OBSERVED FACT]` No endpoint was hidden, truncated, or obfuscated. Every endpoint path, HTTP method, expected status code, and call-site syntax was delivered in full.

---

## 4. PM / Oracle Relationship

- `[OBSERVED FACT]` The PM specification (Section `[3]`) was 350 words (3,474 characters) describing high-level user stories for product management.
- `[OBSERVED FACT]` The prompt explicitly established the hierarchy of authority:
  `"Aturan Otoritas: Jika terdapat perbedaan atau konflik antara PM Proposal dengan [2] ACCEPTANCE OBLIGATION LEDGER, maka [2] ACCEPTANCE OBLIGATION LEDGER MUTLAK MENANG. Architect DILARANG mengubah atau mengarang nama/tipe yang bertentangan dengan Acceptance Authority."`
- `[STRONG EVIDENCE]` There was no conflicting endpoint definition in the PM specification. The PM specification described CRUD capabilities in natural language (create, read all, read by ID, update, delete).
- `[INFERENCE]` The model was not misled by a conflicting authoritative claim in the PM specification, because the prompt instructed that the Acceptance Obligation Ledger had absolute priority (`MUTLAK MENANG`).

---

## 5. Raw Output Analysis

`[OBSERVED FACT]` Line 7 of `run_trace.jsonl` records the Architect Turn 0 synthesis. The model emitted 4,420 characters of raw text containing a JSON block between `=== BLUEPRINT JSON ===` and `=== END BLUEPRINT JSON ===`.

Key elements observed in the model's raw output:
1. **Route Decorators:** `[OBSERVED FACT]` None. The `code_scaffold` for `main.py` did not include FastAPI route decorators (`@app.post(...)`, `@app.get(...)`, `@app.delete(...)`).
2. **HTTP Methods:** `[OBSERVED FACT]` None. In `interface_contracts`, the model emitted objects with keys `identifier`, `target_file`, `parameters`, `expected_return`. Neither `method` nor `http_method` was provided.
3. **Endpoint Paths:** `[OBSERVED FACT]` None. Neither `route` nor `path` was provided in `interface_contracts`.
4. **Declared Interfaces:** `[OBSERVED FACT]` The model declared 6 symbols:
   - `Product` (Pydantic model)
   - `create_product` (function)
   - `get_all_products` (function)
   - `get_product_by_id` (function)
   - `update_product` (function — invented, not in Oracle)
   - `delete_product` (function)
5. **Code Scaffold Content:** `[OBSERVED FACT]` The model wrote:
   ```python
   def create_product(product: Product) -> Product:
       pass

   def get_all_products() -> list:
       pass

   def get_product_by_id(product_id: int) -> Product:
       pass

   def update_product(product_id: int, product: Product) -> Product:
       pass

   def delete_product(product_id: int) -> bool:
       pass
   ```
6. **Subsequent Turns (Repairs):**
   - **Turn 1 (Line 12–13):** `[OBSERVED FACT]` When presented with the Contract Gate rejection diagnostic (`"Public HTTP endpoint '/products' has no declared interface coverage in contract"`), the model attempted to change `code_scaffold` from a string to an arbitrary dictionary (`{'Product': ..., 'create_product': ...}`), violating schema invariant `UNRECOVERABLE_REPRESENTATION_ERROR`. It still declared the same 6 function names and 0 HTTP routes.
   - **Turn 2 (Line 17–18):** `[OBSERVED FACT]` The model reverted `code_scaffold` to a string, but still declared the same internal callables, resulting in a 3rd rejection and budget exhaustion.

---

## 6. Parser / Representation Analysis

- `[OBSERVED FACT]` The parser `parse_blueprint_json` in `backend/blueprint_schema.py` successfully extracted the JSON payload on Turn 0 (`serialization_success: True`, `blueprint_ast_validity: 0 errors`).
- `[OBSERVED FACT]` The parser did not drop, discard, or strip any route or method attributes:
  - `BlueprintInterfaceContract` explicitly parses `route` (and aliases `path`, `endpoint`) and `method` (and alias `http_method`).
  - The model simply never emitted those fields in the raw JSON payload.
- `[OBSERVED FACT]` Question: Did public route/interface binding fail in parser or generation?
  - **Verdict:** **A. Tidak pernah dihasilkan oleh model (Never generated by the model).**
  - The parser is **NOT** the cause of the failure.

---

## 7. Blueprint Capability Check

- `[OBSERVED FACT]` `backend/blueprint_schema.py` defines `BlueprintInterfaceContract`:
  ```python
  class BlueprintInterfaceContract(BaseModel):
      identifier: str = Field(..., min_length=1, description="Nama fungsi/endpoint/metode")
      route: Optional[str] = Field(None, description="Route path (misal: /products)")
      method: Optional[str] = Field(None, description="HTTP Method (misal: GET, POST)")
      target_file: str = Field(..., min_length=1, description="Berkas tempat kontrak ini didefinisikan")
  ```
- `[OBSERVED FACT]` Normalization logic supports multiple industry-standard aliases:
  - `identifier`: `name`, `function_name`, `endpoint_name`, `symbol`
  - `route`: `path`, `endpoint`
  - `method`: `http_method`
  - `target_file`: `file`, `target`
- `[OBSERVED FACT]` `schema_limitation = NO EVIDENCE`. The schema is fully capable of representing HTTP routes, methods, and target artifacts.

---

## 8. Obligation-to-Blueprint Trace Table

`[OBSERVED FACT]` Trace of each authoritative obligation against Turn 0 Architect Blueprint:

| Obligation ID | Method & Path | Visible in Prompt? | Blueprint Representation | Status |
|---|---|---|---|---|
| **OBL-HTTP-POST-products** | `POST /products` | **YES** (Section `[2]`, line 10) | `create_product` (function, `route: null`, `method: null`) | **REPLACED** (Internal callable) |
| **OBL-HTTP-GET-products** | `GET /products` | **YES** (Section `[2]`, line 19) | `get_all_products` (function, `route: null`, `method: null`) | **REPLACED** (Internal callable) |
| **OBL-HTTP-GET-products_id** | `GET /products/{id}` | **YES** (Section `[2]`, line 31) | `get_product_by_id` (function, `route: null`, `method: null`) | **REPLACED** (Internal callable) |
| **OBL-HTTP-DELETE-products_id** | `DELETE /products/{id}` | **YES** (Section `[2]`, line 42) | `delete_product` (function, `route: null`, `method: null`) | **REPLACED** (Internal callable) |

- **Summary:**
  - `Preserved`: 0 / 4
  - `Transformed`: 0 / 4
  - `Omitted`: 0 / 4
  - `Replaced`: 4 / 4 (All 4 public HTTP routes were replaced with internal Python callables)
  - `Invented Extra`: 1 (`update_product`, which does not exist anywhere in the Frozen Oracle)

---

## 9. Internal Callable Substitution Analysis

- **Functions Generated:** `Product`, `create_product`, `get_all_products`, `get_product_by_id`, `delete_product`, `update_product`.
- **Did the Architect add them because of PM?** `[STRONG EVIDENCE]` Partially. The PM specification described standard CRUD operations including "memperbarui produk" (update product).
- **Did the Architect add them because of Oracle?** `[OBSERVED FACT]` NO. The Oracle tests only `POST /products`, `GET /products`, `GET /products/{id}`, `DELETE /products/{id}`, and `DELETE /products/999999`. The Oracle never calls `update_product` or any internal function by name; it interacts exclusively via `TestClient(app)` HTTP requests.
- **Did the Architect infer them on its own?** `[STRONG EVIDENCE]` YES. The model defaulted to classic library/service layer naming conventions (`create_product`, `get_all_products`, `update_product`).
- **Did the Architect replace public HTTP obligations with internal callables?** `[OBSERVED FACT]` YES. The model emitted internal function signatures instead of public route declarations.
- **Did the Architect emit dual representations (both routes and callables)?** `[OBSERVED FACT]` NO. The model generated only internal functions. No route binding metadata or route decorators existed anywhere in the blueprint.

---

## 10. Flutter Cross-Task Control Comparison

`[OBSERVED FACT]` In the exact same 1×3 pilot (`pv_pilot_flutter_t1_rep1_20260919_063148`):

| Metric / Dimension | FastAPI (`fastapi_t1`) | Flutter (`flutter_t1`) | Observed Structural Difference |
|---|---|---|---|
| **Authoritative Obligations** | 4 HTTP endpoints (`POST /products`, `GET /products`, etc.) | 2 OOP/Widget entities (`CardMetric`, `MetricData`) | HTTP route semantics vs Constructor/Class semantics |
| **Public Identity Kind** | `INTERACTION` (Path `/products` + Method `POST`) | `OBSERVABLE_RUNTIME` & `DATA_MODEL` (Class names) | URL string identifier vs OOP Symbol identifier |
| **Oracle Test Mechanism** | `client.post('/products')` (HTTP Client) | `CardMetric(...)`, `MetricData(...)` (Dart Constructor call) | Indirection via web protocol vs Direct AST instantiation |
| **System Prompt Example** | Class `EntityA` + function `operation_a` | Class `EntityA` + function `operation_a` | Example structure matches Flutter OOP pattern, but differs from FastAPI web route pattern |
| **Input Context Tokens** | 5,176 tokens | 4,443 tokens | Within budget for both |
| **Turn 0 Architect Verdict** | **FAIL (`REJECTED`)** | **PASS (`FROZEN`)** | Flutter coverage: 2/2 (100%); FastAPI coverage: 0/4 (0%) |
| **Final Pilot Outcome** | FAIL (0 Dev loops, 448.4s) | **PASS (Turn 0 converged, 2/2 tests pass, 253.9s)** | Deterministic Authority Binding correctly accepted Flutter and rejected FastAPI |

`[STRONG EVIDENCE]` In Flutter, the target symbols in the Oracle were Dart classes/widgets (`CardMetric`, `MetricData`), which directly match the canonical blueprint structure (`data_models` and `interface_contracts`). In FastAPI, the target symbols in the Oracle were HTTP endpoints accessed via an HTTP client, requiring the model to map HTTP routes into route contracts or decorated endpoints.

---

## 11. First Divergence

`[OBSERVED FACT]` Temporal Sequence of First Divergence:

1. `06:21:16` — Pilot initialized. Target: `fastapi_t1`. `[VALID]`
2. `06:23:07` — V0 Requirement Interpretation completed and validated. `[VALID]`
3. `06:24:15` — PM Specification completed and validated. `[VALID]`
4. `06:24:15` — Context Assembler extracts 4 Canonical Obligations from Frozen Oracle and formats Section `[2]`. `[VALID]`
5. **`06:26:09.152` — FIRST DIVERGENCE:** Architect LLM invocation on Turn 0 completes. The model outputs `=== BLUEPRINT JSON ===` containing `['Product', 'create_product', 'delete_product', 'get_all_products', 'get_product_by_id', 'update_product']` with `route: null` and `method: null`, and stubs lacking `@app.post`/`@app.get` decorators. `[DIVERGENCE EVENT]`
6. `06:26:09.183` — Parser successfully extracts JSON. No data altered. `[PASSIVE]`
7. `06:26:09.184` — Authority Binding Gate analyzes coverage against Frozen Oracle:
   - Found 4 missing authoritative obligations (`POST /products`, `GET /products`, `GET /products/{id}`, `DELETE /products/{id}`).
   - Sets contract status to `REJECTED`. Contract is blocked from freeze. `[GATE DETECTED]`

`[OBSERVED FACT]` The first divergence occurred inside the **Architect LLM output generation at Turn 0 (`06:26:09.152`)**, prior to parsing, normalization, or validation.

---

## 12. Capability Attribution Gate

`[STRONG EVIDENCE]` Systematic evaluation of the 9 Capability Attribution Gate conditions:

| # | Gate Condition | Evaluation | Evidence Source |
|---|---|---|---|
| **1** | Authority was explicitly visible | **PASS** | Section `[2]` contains all 4 obligations, paths, methods, and status codes. |
| **2** | Authority representation was unambiguous | **PASS** | Explicit strings: `HTTP endpoint '/products' accepting POST method (expected status: 201)`, etc. |
| **3** | PM did not create unresolved authority conflict | **PASS** | Section `[3]` banner: `"[2] ACCEPTANCE OBLIGATION LEDGER MUTLAK MENANG"`. PM contained no contradictory endpoints. |
| **4** | Blueprint schema could represent required semantics | **PASS** | `BlueprintInterfaceContract` contains `route` and `method` fields with aliases `path`, `endpoint`, `http_method`. |
| **5** | Parser preserved model output | **PASS** | `parse_blueprint_json` parsed raw JSON without stripping fields; model never produced `route` or `method`. |
| **6** | No context truncation | **PASS** | Input was 20,704 chars (~5,176 tokens), strictly within `num_ctx: 8192`. Truncation flag: `False`. |
| **7** | No deterministic transformation altered the meaning | **PASS** | Trace confirms raw LLM output matches parsed AST dictionary. |
| **8** | Architect raw output demonstrates the wrong decision | **PASS** | Raw output explicitly contains internal function names (`create_product`) instead of HTTP route definitions. |
| **9** | No infrastructure failure | **PASS** | Turn 0 completed in 113.68s, HTTP 200 from Ollama, zero token limit aborts. |

**Result:** **ALL 9 CONDITIONS ARE FULLY SATISFIED.**  
`[STRONG EVIDENCE]` The failure is cleanly attributable to the Architect model's semantic decision at Turn 0, not to context loss, schema limitations, or pipeline corruption.

---

## 13. Evidence Classification

- **PRIMARY CLASSIFICATION:** **`ARCHITECT`**
- **SPECIFIC SUB-CLASSIFICATION:** **`semantic mapping failure`**
- **Detailed Finding:**
  - `[OBSERVED FACT]` Not a `PIPELINE` failure: The pipeline assembled all authoritative obligations cleanly, parsed the output faithfully, and deterministically rejected the invalid blueprint.
  - `[OBSERVED FACT]` Not a `DEVELOPER` failure: 0 Developer loops were run because the contract was never frozen.
  - `[OBSERVED FACT]` Not an `INFRASTRUCTURE` failure: Ollama processed the request cleanly without crash, repeat-loop abort, or timeout.
  - `[OBSERVED FACT]` Not a `schema limitation`: The blueprint schema supports routes and methods.
  - `[STRONG EVIDENCE]` The Architect model received explicit public HTTP endpoint obligations and substituted them with internal Python callables, lacking the route metadata required for FastAPI public interfaces.

---

## 14. Confidence Level

- **Confidence Score:** **100% (High Certainty)**
- **Basis:**
  - Direct trace evidence from `pv_pilot_fastapi_t1_rep1_20260919_062116/run_trace.jsonl`.
  - Reconstructed prompt matching exact character counts and token estimates.
  - Verified source code of `blueprint_schema.py`, `architect.py`, `context_assembler.py`, and `frozen_oracle/fastapi_t1/test_main.py`.
  - Controlled cross-task baseline comparison against `pv_pilot_flutter_t1_rep1_20260919_063148` from the exact same pilot execution.

---

## 15. UNKNOWN / Unresolved Items

1. `[UNKNOWN]` **Prompt Example Influence:** The `ARCHITECT_SYSTEM_PROMPT` contains an illustrative example using `operation_a(entity: EntityA) -> EntityA:` and `class EntityA:`. It is unknown whether providing an OOP/functional example without an HTTP route example biased the 7B model toward generating internal Python callables instead of FastAPI route handlers.
2. `[UNKNOWN]` **Model Generalization on Web Protocols:** It is unknown whether the 7B model (`qwen2.5-coder:7b`) can inherently distinguish between a library API contract and an HTTP REST route contract without explicit instruction on how FastAPI route handlers map to `interface_contracts.route` and `interface_contracts.method`.
3. `[UNKNOWN]` **Repair Turn Recovery Behavior:** On Turn 1 and Turn 2, the model received explicit feedback identifying the exact missing routes (`"Public HTTP endpoint '/products' has no declared interface coverage"`), but responded by corrupting the scaffold format (Turn 1) and repeating the internal function names (Turn 2). The cognitive mechanism preventing the model from incorporating the diagnostic remains unobserved.
