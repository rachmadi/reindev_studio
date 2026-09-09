"""
Unit & Integration Tests for Developer Gateway & OpenRouter Adapter
ReinDev Studio — Iterasi 6 Frontier Model Integration

Test Matrix:
1. Test Credential Safety & Isolation
2. Test HTTP Error & Transport Failure Classification (MODEL_TRANSPORT_ERROR)
3. Test Response Extraction & Normalization
4. Test Anti-Fallback & Strict Model Pinning
5. Test Configuration Hierarchy & Loader
6. Test Existing Local Path Preservation (Ollama + Qwen 7B)
7. Test Zero Prompt Tampering
8. Test Pipeline Integration with Developer Agent & Graph
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock
from langchain_core.messages import SystemMessage, HumanMessage

from backend.developer_gateway import (
    DeveloperGateway,
    DeveloperTransportError,
    DeveloperResponse,
    OpenRouterDeveloperAdapter,
    OllamaDeveloperAdapter,
    load_developer_config,
    BaseDeveloperAdapter
)
from backend.agents.developer import developer_agent, parse_code_blocks
from backend.graph import route_after_developer, END


# ===========================================================================
# 1. Test Credential Safety & Isolation
# ===========================================================================

class TestCredentialSafety:
    """Verifikasi isolasi mutlak kredensial OPENROUTER_API_KEY."""

    def test_api_key_read_from_environment(self, monkeypatch):
        """API key harus dibaca langsung dari environment variable."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-secret-token-12345")
        adapter = OpenRouterDeveloperAdapter(model="qwen/qwen-2.5-coder-32b-instruct")
        assert adapter._api_key == "sk-or-v1-secret-token-12345"

    def test_missing_api_key_raises_transport_error(self, monkeypatch):
        """Ketiadaan OPENROUTER_API_KEY harus melempar MODEL_TRANSPORT_ERROR."""
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        adapter = OpenRouterDeveloperAdapter(api_key="")
        
        with pytest.raises(DeveloperTransportError) as exc_info:
            adapter.invoke("Halo, tulis kode")
            
        err = exc_info.value
        assert err.error_code == "MODEL_TRANSPORT_ERROR"
        assert "OPENROUTER_API_KEY environment variable is not set" in str(err)
        assert err.provider == "openrouter"

    def test_no_api_key_leakage_in_repr(self, monkeypatch):
        """String representation adapter DILARANG memuat API key."""
        secret_key = "sk-or-v1-super-confidential-key"
        monkeypatch.setenv("OPENROUTER_API_KEY", secret_key)
        adapter = OpenRouterDeveloperAdapter()
        repr_str = repr(adapter)
        
        assert secret_key not in repr_str
        assert "model=" in repr_str
        assert "endpoint=" in repr_str

    def test_no_api_key_leakage_in_transport_error_dict(self):
        """Dictionary hasil to_dict() DeveloperTransportError DILARANG memuat API key."""
        err = DeveloperTransportError(
            message="Connection failed",
            error_code="MODEL_TRANSPORT_ERROR",
            status_code=500,
            provider="openrouter",
            model="qwen/qwen-2.5-coder-32b-instruct"
        )
        d = err.to_dict()
        assert "api_key" not in d
        assert "Authorization" not in str(d)
        assert d["error_code"] == "MODEL_TRANSPORT_ERROR"

    def test_no_api_key_leakage_in_response_metadata(self, monkeypatch):
        """Metadata response DILARANG memuat API key maupun header Authorization."""
        secret_key = "sk-or-v1-my-secret-key-999"
        monkeypatch.setenv("OPENROUTER_API_KEY", secret_key)
        adapter = OpenRouterDeveloperAdapter(model="test-model")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "id": "gen-123",
            "model": "test-model",
            "choices": [{"message": {"role": "assistant", "content": "def add(a, b): return a + b"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 15, "total_tokens": 25}
        }

        with patch("requests.post", return_value=mock_resp):
            resp = adapter.invoke("Tulis fungsi add")

        meta = resp.metadata
        assert "api_key" not in meta
        assert secret_key not in json.dumps(meta)
        assert meta["developer_backend"] == "openrouter"
        assert meta["model"] == "test-model"


# ===========================================================================
# 2. Test HTTP Transport Errors (MODEL_TRANSPORT_ERROR)
# ===========================================================================

class TestHTTPTransportErrors:
    """Verifikasi klasifikasi kegagalan HTTP dan jaringan secara deterministik."""

    @pytest.fixture(autouse=True)
    def setup_api_key(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-dummy-key")

    def test_http_401_unauthorized(self):
        adapter = OpenRouterDeveloperAdapter(model="test-model")
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.json.return_value = {"error": {"message": "Invalid API key"}}

        with patch("requests.post", return_value=mock_resp):
            with pytest.raises(DeveloperTransportError) as exc_info:
                adapter.invoke("test")
        
        err = exc_info.value
        assert err.error_code == "MODEL_TRANSPORT_ERROR"
        assert err.status_code == 401
        assert "401" in str(err)

    def test_http_429_rate_limit(self):
        adapter = OpenRouterDeveloperAdapter(model="test-model")
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.json.return_value = {"error": {"message": "Rate limit exceeded"}}

        with patch("requests.post", return_value=mock_resp):
            with pytest.raises(DeveloperTransportError) as exc_info:
                adapter.invoke("test")
        
        err = exc_info.value
        assert err.error_code == "MODEL_TRANSPORT_ERROR"
        assert err.status_code == 429

    def test_http_500_upstream_server_error(self):
        adapter = OpenRouterDeveloperAdapter(model="test-model")
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.json.return_value = {"error": {"message": "Internal server error"}}

        with patch("requests.post", return_value=mock_resp):
            with pytest.raises(DeveloperTransportError) as exc_info:
                adapter.invoke("test")
        
        err = exc_info.value
        assert err.error_code == "MODEL_TRANSPORT_ERROR"
        assert err.status_code == 500

    def test_http_timeout(self):
        import requests
        adapter = OpenRouterDeveloperAdapter(model="test-model", timeout_sec=5)

        with patch("requests.post", side_effect=requests.exceptions.Timeout("Connection timed out")):
            with pytest.raises(DeveloperTransportError) as exc_info:
                adapter.invoke("test")
        
        err = exc_info.value
        assert err.error_code == "MODEL_TRANSPORT_ERROR"
        assert err.status_code == 408
        assert "timed out" in str(err).lower()

    def test_http_connection_error(self):
        import requests
        adapter = OpenRouterDeveloperAdapter(model="test-model")

        with patch("requests.post", side_effect=requests.exceptions.ConnectionError("DNS failure")):
            with pytest.raises(DeveloperTransportError) as exc_info:
                adapter.invoke("test")
        
        err = exc_info.value
        assert err.error_code == "MODEL_TRANSPORT_ERROR"
        assert "connectivity error" in str(err).lower()

    def test_empty_choices_in_response(self):
        adapter = OpenRouterDeveloperAdapter(model="test-model")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"choices": []}

        with patch("requests.post", return_value=mock_resp):
            with pytest.raises(DeveloperTransportError) as exc_info:
                adapter.invoke("test")
        
        err = exc_info.value
        assert err.error_code == "MODEL_TRANSPORT_ERROR"
        assert "empty" in str(err).lower()


# ===========================================================================
# 3. Test Response Extraction & Normalization
# ===========================================================================

class TestResponseExtraction:
    """Verifikasi normalisasi payload respons OpenRouter ke standar DeveloperResponse."""

    def test_successful_response_normalization(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-valid")
        adapter = OpenRouterDeveloperAdapter(model="qwen/qwen-2.5-coder-32b-instruct")

        sample_code = "=== FILE: main.py ===\ndef hello():\n    return 'world'\n=== END FILE ==="
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "id": "gen-999",
            "model": "qwen/qwen-2.5-coder-32b-instruct",
            "choices": [{"message": {"role": "assistant", "content": sample_code}}],
            "usage": {"prompt_tokens": 150, "completion_tokens": 40, "total_tokens": 190}
        }

        with patch("requests.post", return_value=mock_resp):
            resp = adapter.invoke("Generate code")

        assert isinstance(resp, DeveloperResponse)
        assert resp.content == sample_code
        assert resp.metadata["model"] == "qwen/qwen-2.5-coder-32b-instruct"
        assert resp.metadata["developer_backend"] == "openrouter"
        assert "latency_s" in resp.metadata
        assert resp.metadata["usage"]["total_tokens"] == 190


# ===========================================================================
# 4. Test Anti-Fallback & Strict Model Pinning
# ===========================================================================

class TestAntiFallback:
    """Verifikasi bahwa tidak ada pergantian model diam-diam (zero automatic fallback)."""

    def test_no_automatic_fallback_on_model_failure(self, monkeypatch):
        """Jika model cloud gagal, adapter harus melempar error dan TIDAK beralih ke model lain."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-valid")
        requested_model = "deepseek/deepseek-chat"
        adapter = OpenRouterDeveloperAdapter(model=requested_model)

        mock_resp = MagicMock()
        mock_resp.status_code = 503
        mock_resp.json.return_value = {"error": {"message": "Service Unavailable"}}

        with patch("requests.post", return_value=mock_resp) as mock_post:
            with pytest.raises(DeveloperTransportError) as exc_info:
                adapter.invoke("test")

        # Pastikan hanya ada 1 request ke model yang diminta, bukan mencoba model fallback
        assert mock_post.call_count == 1
        payload = mock_post.call_args[1]["json"]
        assert payload["model"] == requested_model
        assert payload["provider"]["allow_fallbacks"] is False

        err = exc_info.value
        assert err.model == requested_model
        assert err.error_code == "MODEL_TRANSPORT_ERROR"


# ===========================================================================
# 5. Test Configuration Hierarchy & Loader
# ===========================================================================

class TestConfigurationHierarchy:
    """Verifikasi prioritas konfigurasi Developer Gateway."""

    def test_default_configuration(self, monkeypatch):
        """Default tanpa env/config harus ollama + qwen2.5-coder:7b."""
        monkeypatch.delenv("DEVELOPER_BACKEND", raising=False)
        monkeypatch.delenv("DEVELOPER_MODEL", raising=False)
        monkeypatch.delenv("LLM_PROVIDER", raising=False)

        cfg = load_developer_config()
        assert cfg["backend"] == "ollama"
        assert cfg["model"] == "qwen2.5-coder:7b"

    def test_environment_variable_override(self, monkeypatch):
        """Environment variables DEVELOPER_BACKEND dan DEVELOPER_MODEL harus diutamakan."""
        monkeypatch.setenv("DEVELOPER_BACKEND", "openrouter")
        monkeypatch.setenv("DEVELOPER_MODEL", "meta-llama/llama-3.3-70b-instruct")

        cfg = load_developer_config()
        assert cfg["backend"] == "openrouter"
        assert cfg["model"] == "meta-llama/llama-3.3-70b-instruct"

    def test_dict_configuration_override(self, monkeypatch):
        """Dictionary config harus dipatuhi jika env var tidak disetel."""
        monkeypatch.delenv("DEVELOPER_BACKEND", raising=False)
        monkeypatch.delenv("DEVELOPER_MODEL", raising=False)
        monkeypatch.delenv("LLM_PROVIDER", raising=False)

        custom_cfg = {"developer": {"backend": "openrouter", "model": "openai/gpt-4o-mini"}}
        cfg = load_developer_config(custom_cfg)
        assert cfg["backend"] == "openrouter"
        assert cfg["model"] == "openai/gpt-4o-mini"

    def test_gateway_create_adapter_factory(self, monkeypatch):
        """Factory Gateway harus mengembalikan tipe adapter yang tepat."""
        adapter_ollama = DeveloperGateway.create_adapter(backend="ollama", model="qwen2.5-coder:7b")
        assert isinstance(adapter_ollama, OllamaDeveloperAdapter)
        assert adapter_ollama.model == "qwen2.5-coder:7b"

        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-dummy")
        adapter_openrouter = DeveloperGateway.create_adapter(
            backend="openrouter",
            model="qwen/qwen-2.5-coder-32b-instruct"
        )
        assert isinstance(adapter_openrouter, OpenRouterDeveloperAdapter)
        assert adapter_openrouter.model == "qwen/qwen-2.5-coder-32b-instruct"


# ===========================================================================
# 6. Test Existing Local Path Preservation
# ===========================================================================

class TestExistingLocalPath:
    """Verifikasi bahwa jalur lokal Ollama + Qwen 7B tetap intact dan default."""

    def test_ollama_adapter_defaults(self):
        adapter = OllamaDeveloperAdapter()
        assert adapter.model == "qwen2.5-coder:7b"
        assert adapter.base_url == "http://localhost:11434"
        assert adapter.temperature == 0.2
        assert adapter.num_predict == 1000

    def test_ollama_adapter_with_mock_llm(self, monkeypatch):
        """Dalam mode MOCK_LLM, Ollama adapter dapat merespons tanpa server Ollama aktif."""
        monkeypatch.setenv("MOCK_LLM", "true")
        adapter = OllamaDeveloperAdapter(model="qwen2.5-coder:7b")
        resp = adapter.invoke("Tulis kode kalkulator")
        assert isinstance(resp, DeveloperResponse)
        assert "FILE:" in resp.content
        assert resp.metadata["is_mock"] is True


# ===========================================================================
# 7. Test Zero Prompt Tampering
# ===========================================================================

class TestZeroPromptTampering:
    """Verifikasi bahwa adapter OpenRouter tidak memodifikasi prompt ReinDev sama sekali."""

    def test_prompt_content_passed_verbatim(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-valid")
        adapter = OpenRouterDeveloperAdapter(model="test-model")

        sys_msg = SystemMessage(content="ReinDev Official System Prompt")
        user_msg = HumanMessage(content="Official User Task [ACTIONABLE HINT] P0-1")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"role": "assistant", "content": "clean code"}}]
        }

        with patch("requests.post", return_value=mock_resp) as mock_post:
            adapter.invoke([sys_msg, user_msg])

        payload = mock_post.call_args[1]["json"]
        messages = payload["messages"]

        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "ReinDev Official System Prompt"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Official User Task [ACTIONABLE HINT] P0-1"

        # Pastikan tidak ada injeksi sistem tambahan seperti "You are a frontier model..."
        for m in messages:
            assert "frontier model" not in m["content"].lower()
            assert "try harder" not in m["content"].lower()


# ===========================================================================
# 8. Test Pipeline Integration with Developer Agent & Graph
# ===========================================================================

class TestPipelineIntegration:
    """Verifikasi integrasi Developer Agent dan Graph dengan Developer Gateway."""

    def test_developer_agent_with_openrouter_adapter(self, monkeypatch):
        """developer_agent berhasil menggunakan OpenRouter adapter dan memperbarui state."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-valid")

        code_text = "=== FILE: main.py ===\ndef calculate():\n    return 42\n=== END FILE ==="
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "model": "qwen/qwen-2.5-coder-32b-instruct",
            "choices": [{"message": {"role": "assistant", "content": code_text}}],
            "usage": {"total_tokens": 120}
        }

        state = {
            "task": "Buat fungsi kalkulasi",
            "specifications": "acceptance criteria",
            "architecture_plan": "file tree",
            "target_language": "python",
            "iteration_count": 0,
            "developer_backend": "openrouter",
            "developer_model": "qwen/qwen-2.5-coder-32b-instruct",
            "run_id": "test-run-123",
            "logs": []
        }

        with patch("requests.post", return_value=mock_resp):
            result = developer_agent(state)

        assert result["status"] == "dev_done"
        assert "main.py" in result["code_files"]
        assert "def calculate():" in result["code_files"]["main.py"]
        assert any("[Developer]:" in log for log in result["logs"])

    def test_developer_agent_transport_error_handling(self, monkeypatch):
        """Jika terjadi transport error, developer_agent mengembalikan status transport_error secara aman."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-valid")

        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.json.return_value = {"error": {"message": "Invalid API key"}}

        state = {
            "task": "Tugas apa saja",
            "developer_backend": "openrouter",
            "developer_model": "qwen/qwen-2.5-coder-32b-instruct",
            "logs": []
        }

        with patch("requests.post", return_value=mock_resp):
            result = developer_agent(state)

        assert result["status"] == "transport_error"
        assert result["error"]["error_code"] == "MODEL_TRANSPORT_ERROR"
        assert result["error"]["status_code"] == 401
        assert any("Transport Error" in log for log in result["logs"])

    def test_graph_routing_on_transport_error(self):
        """route_after_developer harus menghentikan alur ke END jika status transport_error."""
        state = {
            "status": "transport_error",
            "iteration_count": 0,
            "test_files": {}
        }
        next_node = route_after_developer(state)
        assert next_node == END
