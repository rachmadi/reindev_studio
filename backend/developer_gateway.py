"""
Developer Gateway & Model Adapters
ReinDev Studio — Frontier & Local Model Integration Gateway

Menyediakan abstraksi seragam bagi Developer Agent untuk berkomunikasi
dengan model lokal (Ollama) maupun cloud/frontier (OpenRouter) tanpa
mengubah pipeline, graph, kontrak, atau diagnostic parser ReinDev.

Prinsip Utama:
1. QWEN/OLLAMA TETAP DEFAULT: Tidak mengubah atau menghapus alur lokal eksisting.
2. ZERO PROMPT TAMPERING: Mengirim prompt asli ReinDev tanpa modifikasi atau instruksi tambahan.
3. ISOLASI KREDENSIAL MUTLAK: OPENROUTER_API_KEY hanya dibaca dari environment. Dilarang bocor ke log/source/artifact.
4. PEMISAHAN KEGAGALAN: MODEL_TRANSPORT_ERROR dipisahkan tegas dari DEVELOPER_REASONING_FAILURE.
5. ZERO AUTOMATIC FALLBACK: Kegagalan akses model OpenRouter dicatat sebagai transport error, tidak berpindah model diam-diam.
"""

from __future__ import annotations

import os
import time
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from .tracer import get_tracer
except (ImportError, ValueError):
    try:
        from tracer import get_tracer
    except ImportError:
        def get_tracer(run_id: Optional[str] = None):
            return None


# ===========================================================================
# 1. Error & Response Contracts
# ===========================================================================

class DeveloperTransportError(Exception):
    """
    Error infrastruktur / jaringan / API (MODEL_TRANSPORT_ERROR):
    - Kredensial tidak ditemukan atau tidak valid (401/403)
    - Jaringan terputus / ConnectionRefused / DNS failure
    - HTTP Timeout
    - Rate limit (429)
    - OpenRouter / upstream provider failure (5xx)
    - Respons JSON tidak valid / malformed
    
    Dipisahkan secara tegas dari DEVELOPER_REASONING_FAILURE (kode salah secara logika).
    """
    def __init__(
        self,
        message: str,
        error_code: str = "MODEL_TRANSPORT_ERROR",
        status_code: Optional[int] = None,
        provider: str = "openrouter",
        model: Optional[str] = None,
        raw_error: Optional[Any] = None
    ):
        super().__init__(message)
        self.error_code = error_code
        self.status_code = status_code
        self.provider = provider
        self.model = model
        self.raw_error = raw_error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_code": self.error_code,
            "status_code": self.status_code,
            "provider": self.provider,
            "model": self.model,
            "message": str(self)
        }


@dataclass
class DeveloperResponse:
    """
    Standarisasi luaran Developer Gateway yang kompatibel ke belakang.
    Memiliki atribut `.content` sehingga dapat langsung dikonsumsi oleh `developer_agent`.
    """
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.content

    def __repr__(self) -> str:
        backend = self.metadata.get("developer_backend", "unknown")
        model = self.metadata.get("model", "unknown")
        return f"<DeveloperResponse backend={backend} model={model} length={len(self.content)}>"


# ===========================================================================
# 2. Base Adapter Interface
# ===========================================================================

class BaseDeveloperAdapter(ABC):
    """Antarmuka dasar bagi seluruh adaptor model Developer di ReinDev."""

    @abstractmethod
    def invoke(
        self,
        messages: Union[List[Any], str],
        run_id: Optional[str] = None,
        experiment_id: Optional[str] = None,
        **kwargs
    ) -> DeveloperResponse:
        """Kirim pesan/prompt ke model dan kembalikan DeveloperResponse."""
        pass


# ===========================================================================
# 3. Ollama Developer Adapter (Default Local)
# ===========================================================================

class OllamaDeveloperAdapter(BaseDeveloperAdapter):
    """
    Adaptor Developer untuk model lokal Ollama (Default: qwen2.5-coder:7b).
    Mempertahankan perilaku, batas konteks, dan konfigurasi lokal 100%.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.2,
        num_ctx: Optional[int] = None,
        num_predict: Optional[int] = None
    ):
        self.model = model or os.getenv("DEVELOPER_MODEL") or os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.temperature = temperature
        self.num_ctx = num_ctx or int(os.getenv("OLLAMA_NUM_CTX", "2048"))
        self.num_predict = num_predict or int(os.getenv("OLLAMA_NUM_PREDICT", "1000"))

    def invoke(
        self,
        messages: Union[List[Any], str],
        run_id: Optional[str] = None,
        experiment_id: Optional[str] = None,
        **kwargs
    ) -> DeveloperResponse:
        t0 = time.time()
        if os.getenv("MOCK_LLM", "false").lower() == "true":
            try:
                from .config import get_llm
            except (ImportError, ValueError):
                try:
                    from config import get_llm
                except ImportError:
                    get_llm = None
            if get_llm:
                llm = get_llm(role="developer", provider="ollama")
                response = llm.invoke(messages)
                latency = round(time.time() - t0, 3)
                raw_text = response.content if hasattr(response, "content") else str(response)
                return DeveloperResponse(
                    content=raw_text,
                    metadata={
                        "developer_backend": "ollama",
                        "provider": "ollama",
                        "model": self.model,
                        "latency_s": latency,
                        "is_mock": True,
                        "run_id": run_id,
                        "experiment_id": experiment_id
                    }
                )

        try:
            from langchain_ollama import ChatOllama
            llm = ChatOllama(
                base_url=self.base_url,
                model=self.model,
                num_ctx=self.num_ctx,
                num_predict=self.num_predict,
                temperature=self.temperature,
            )
            response = llm.invoke(messages)
            latency = round(time.time() - t0, 3)
            raw_text = response.content if hasattr(response, "content") else str(response)

            metadata = {
                "developer_backend": "ollama",
                "provider": "ollama",
                "model": self.model,
                "latency_s": latency,
                "generation_parameters": {
                    "temperature": self.temperature,
                    "num_ctx": self.num_ctx,
                    "num_predict": self.num_predict,
                },
                "run_id": run_id,
                "experiment_id": experiment_id
            }

            tracer = get_tracer(run_id)
            if tracer:
                tracer.log_event(
                    stage="developer",
                    event_type="gateway_call_completed",
                    iteration=kwargs.get("iteration", 0),
                    data=metadata
                )

            return DeveloperResponse(content=raw_text, metadata=metadata)

        except Exception as exc:
            latency = round(time.time() - t0, 3)
            # Jika Ollama down atau tidak dapat dijangkau
            err_msg = str(exc)
            if any(k in err_msg.lower() for k in ("connection refused", "timeout", "failed to connect", "not found")):
                raise DeveloperTransportError(
                    message=f"Gagal terhubung ke Ollama pada {self.base_url}: {err_msg}",
                    error_code="MODEL_TRANSPORT_ERROR",
                    provider="ollama",
                    model=self.model,
                    raw_error=exc
                ) from exc
            raise


# ===========================================================================
# 4. OpenRouter Developer Adapter (Cloud / Frontier Gateway)
# ===========================================================================

class OpenRouterDeveloperAdapter(BaseDeveloperAdapter):
    """
    Adaptor Developer berbasis OpenRouter API.
    Memungkinkan Developer Agent menggunakan model cloud/frontier tanpa mengubah
    pipeline ReinDev lainnya.
    
    Fitur Kritis:
    - Zero Prompt Tampering: Meneruskan pesan tanpa augmentasi instruksi tersembunyi.
    - Zero Automatic Fallback: Mengunci model secara eksplisit, tidak diam-diam pindah model.
    - Safe Credential Isolation: Kredensial tidak pernah diekspos dalam representasi objek atau log.
    - Deterministic Transport Error Handling: Mengklasifikasikan kegagalan jaringan/HTTP sebagai MODEL_TRANSPORT_ERROR.
    """

    DEFAULT_ENDPOINT = "https://openrouter.ai/api/v1"

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.2,
        timeout_sec: int = 120
    ):
        self.model = model or os.getenv("DEVELOPER_MODEL") or os.getenv("OPENROUTER_MODEL", "qwen/qwen-2.5-coder-32b-instruct")
        self._api_key = api_key or os.getenv("OPENROUTER_API_KEY", "").strip()
        self.base_url = (base_url or os.getenv("OPENROUTER_BASE_URL", self.DEFAULT_ENDPOINT)).rstrip("/")
        self.temperature = temperature
        self.timeout_sec = int(os.getenv("OPENROUTER_TIMEOUT", str(timeout_sec)))


    def __repr__(self) -> str:
        # Keamanan kredensial: TIDAK PERNAH mencetak API key di repr
        return f"<OpenRouterDeveloperAdapter model={self.model} endpoint={self.base_url}>"

    def _format_messages(self, messages: Union[List[Any], str]) -> List[Dict[str, str]]:
        """Mengonversi pesan LangChain atau string ke format OpenAI ChatCompletion."""
        if isinstance(messages, str):
            return [{"role": "user", "content": messages}]

        formatted = []
        for msg in messages:
            if hasattr(msg, "type") and hasattr(msg, "content"):
                role = "user"
                if msg.type in ("system", "system_message"):
                    role = "system"
                elif msg.type in ("ai", "assistant"):
                    role = "assistant"
                formatted.append({"role": role, "content": str(msg.content)})
            elif isinstance(msg, dict) and "role" in msg and "content" in msg:
                formatted.append({"role": msg["role"], "content": str(msg["content"])})
            else:
                formatted.append({"role": "user", "content": str(msg)})
        return formatted

    def invoke(
        self,
        messages: Union[List[Any], str],
        run_id: Optional[str] = None,
        experiment_id: Optional[str] = None,
        **kwargs
    ) -> DeveloperResponse:
        # 1. Verifikasi kredensial aman
        if not self._api_key:
            # Muat ulang dari environment jika belum terisi
            self._api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        
        if not self._api_key:
            raise DeveloperTransportError(
                message="OPENROUTER_API_KEY environment variable is not set. Cloud model execution cannot proceed.",
                error_code="MODEL_TRANSPORT_ERROR",
                provider="openrouter",
                model=self.model
            )

        import requests

        formatted_messages = self._format_messages(messages)
        endpoint = f"{self.base_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/reindev-studio",
            "X-Title": "ReinDev Studio",
        }

        # Kunci model secara eksplisit: tidak ada fallback array agar model tidak berganti diam-diam
        payload = {
            "model": self.model,
            "messages": formatted_messages,
            "temperature": self.temperature,
            # Matikan provider fallback OpenRouter jika didukung header
            "provider": {
                "allow_fallbacks": False
            }
        }

        t0 = time.time()
        try:
            resp = requests.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=self.timeout_sec
            )
            latency = round(time.time() - t0, 3)

        except requests.exceptions.Timeout as exc:
            latency = round(time.time() - t0, 3)
            raise DeveloperTransportError(
                message=f"OpenRouter request timed out after {self.timeout_sec}s for model '{self.model}'.",
                error_code="MODEL_TRANSPORT_ERROR",
                status_code=408,
                provider="openrouter",
                model=self.model,
                raw_error=exc
            ) from exc

        except requests.exceptions.ConnectionError as exc:
            latency = round(time.time() - t0, 3)
            raise DeveloperTransportError(
                message=f"Network connectivity error connecting to OpenRouter ({endpoint}).",
                error_code="MODEL_TRANSPORT_ERROR",
                provider="openrouter",
                model=self.model,
                raw_error=exc
            ) from exc

        except Exception as exc:
            latency = round(time.time() - t0, 3)
            raise DeveloperTransportError(
                message=f"Unexpected transport failure contacting OpenRouter: {exc}",
                error_code="MODEL_TRANSPORT_ERROR",
                provider="openrouter",
                model=self.model,
                raw_error=exc
            ) from exc

        # 2. Tangani status kode HTTP secara deterministik
        if resp.status_code != 200:
            err_text = ""
            try:
                err_data = resp.json()
                err_text = err_data.get("error", {}).get("message", resp.text[:300])
            except Exception:
                err_text = resp.text[:300]

            if resp.status_code == 401:
                msg = f"Authentication failure (401): Invalid or unauthorized OPENROUTER_API_KEY. Details: {err_text}"
            elif resp.status_code == 429:
                msg = f"Rate limit exceeded (429) on OpenRouter for model '{self.model}'. Details: {err_text}"
            elif resp.status_code >= 500:
                msg = f"OpenRouter / Upstream Provider Error ({resp.status_code}): {err_text}"
            else:
                msg = f"OpenRouter API request failed with status {resp.status_code}: {err_text}"

            raise DeveloperTransportError(
                message=msg,
                error_code="MODEL_TRANSPORT_ERROR",
                status_code=resp.status_code,
                provider="openrouter",
                model=self.model,
                raw_error=err_text
            )

        # 3. Ekstraksi response JSON & teks output
        try:
            res_json = resp.json()
            choices = res_json.get("choices", [])
            if not choices:
                raise DeveloperTransportError(
                    message=f"Malformed API response: 'choices' array is empty from OpenRouter for model '{self.model}'.",
                    error_code="MODEL_TRANSPORT_ERROR",
                    status_code=resp.status_code,
                    provider="openrouter",
                    model=self.model,
                    raw_error=res_json
                )
            
            raw_content = choices[0].get("message", {}).get("content", "")
            usage_data = res_json.get("usage", {})
            actual_model = res_json.get("model", self.model)

        except Exception as exc:
            raise DeveloperTransportError(
                message=f"Failed to parse OpenRouter JSON response: {exc}",
                error_code="MODEL_TRANSPORT_ERROR",
                status_code=resp.status_code,
                provider="openrouter",
                model=self.model,
                raw_error=exc
            ) from exc

        # 4. Susun metadata observabilitas (BEBAS KREDENSIAL)
        metadata = {
            "developer_backend": "openrouter",
            "provider": "openrouter",
            "model": actual_model,
            "requested_model": self.model,
            "latency_s": latency,
            "generation_parameters": {
                "temperature": self.temperature,
                "timeout_sec": self.timeout_sec
            },
            "usage": usage_data,
            "run_id": run_id,
            "experiment_id": experiment_id
        }

        tracer = get_tracer(run_id)
        if tracer:
            tracer.log_event(
                stage="developer",
                event_type="gateway_call_completed",
                iteration=kwargs.get("iteration", 0),
                data=metadata
            )

        return DeveloperResponse(content=raw_content, metadata=metadata)


# ===========================================================================
# 5. Configuration Loader & Factory Gateway
# ===========================================================================

def load_developer_config(
    config_source: Union[str, Path, Dict[str, Any], None] = None
) -> Dict[str, Any]:
    """
    Membaca konfigurasi developer dari dictionary, file YAML, atau environment variables.
    
    Contoh YAML yang didukung:
    developer:
      backend: openrouter
      model: qwen/qwen-2.5-coder-32b-instruct
    
    Default:
    backend: ollama
    model: qwen2.5-coder:7b
    """
    resolved_config = {
        "backend": "ollama",
        "model": "qwen2.5-coder:7b"
    }

    # 1. Baca dari file YAML jika path diberikan atau file default reindev_config.yaml ada
    yaml_data = {}
    target_path = None
    if isinstance(config_source, (str, Path)):
        target_path = Path(config_source)
    elif config_source is None:
        default_cfg = Path("reindev_config.yaml")
        if default_cfg.exists():
            target_path = default_cfg

    if target_path and target_path.exists():
        try:
            import yaml
            with open(target_path, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
                if isinstance(loaded, dict):
                    yaml_data = loaded.get("developer", loaded)
        except Exception:
            pass
    elif isinstance(config_source, dict):
        yaml_data = config_source.get("developer", config_source)

    if isinstance(yaml_data, dict):
        if "backend" in yaml_data:
            resolved_config["backend"] = str(yaml_data["backend"]).lower()
        if "model" in yaml_data:
            resolved_config["model"] = str(yaml_data["model"])

    # 2. Environment variable override (jika disetel secara eksplisit)
    env_backend = os.getenv("DEVELOPER_BACKEND") or os.getenv("LLM_PROVIDER")
    if env_backend:
        resolved_config["backend"] = env_backend.lower()

    env_model = os.getenv("DEVELOPER_MODEL")
    if env_model:
        resolved_config["model"] = env_model

    return resolved_config


class DeveloperGateway:
    """
    Pintu gerbang tunggal (Single Entrypoint) untuk Developer Agent.
    Mengisolasi seluruh dependensi backend/model dari Graph dan Reviewer.
    """

    @classmethod
    def create_adapter(
        cls,
        backend: Optional[str] = None,
        model: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        run_id: Optional[str] = None,
        **kwargs
    ) -> BaseDeveloperAdapter:
        """
        Factory untuk menginisialisasi adapter yang tepat sesuai urutan prioritas:
        1. Parameter argumen eksplisit (`backend`, `model`)
        2. Config dictionary / YAML
        3. Environment variables
        4. Default (Ollama: qwen2.5-coder:7b)
        """
        resolved = load_developer_config(config)

        chosen_backend = (backend or resolved.get("backend") or "ollama").lower()
        chosen_model = model or resolved.get("model")

        if chosen_backend == "openrouter":
            # Jika backend openrouter tetapi model belum dispesifikasikan, gunakan default coder openrouter
            if not chosen_model or chosen_model == "qwen2.5-coder:7b":
                chosen_model = os.getenv("OPENROUTER_MODEL", "qwen/qwen-2.5-coder-32b-instruct")
            return OpenRouterDeveloperAdapter(model=chosen_model, **kwargs)
        else:
            # Default ke Ollama
            if not chosen_model:
                chosen_model = "qwen2.5-coder:7b"
            return OllamaDeveloperAdapter(model=chosen_model, **kwargs)

    @classmethod
    def from_state(cls, state: Dict[str, Any]) -> BaseDeveloperAdapter:
        """Helper untuk menginisialisasi adapter langsung dari SquadState."""
        backend = (
            state.get("developer_backend") or 
            (state.get("provider") if state.get("provider") == "openrouter" else None) or 
            os.getenv("DEVELOPER_BACKEND") or 
            state.get("provider")
        )
        model = (
            state.get("developer_model") or 
            (os.getenv("DEVELOPER_MODEL") if backend == "openrouter" else None) or 
            state.get("model_name")
        )
        run_id = state.get("run_id")
        return cls.create_adapter(backend=backend, model=model, run_id=run_id)
