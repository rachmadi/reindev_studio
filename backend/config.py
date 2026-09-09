import os
from dotenv import load_dotenv
from langchain_core.language_models.chat_models import BaseChatModel

load_dotenv()

def get_llm(role: str = "developer", provider: str = None) -> BaseChatModel:
    selected_provider = (provider or os.getenv("LLM_PROVIDER", "ollama")).lower()
    
    # Check if mock mode is requested for fast offline testing
    if os.getenv("MOCK_LLM", "false").lower() == "true":
        from langchain_core.language_models.fake_chat_models import FakeListChatModel
        if role == "pm":
            return FakeListChatModel(responses=[
                "# Spesifikasi Sistem\n## User Stories\n- Sebagai pengguna, saya ingin modul kalkulator vektor matematika.\n## Acceptance Criteria\n- Menghitung dot product dua vektor dengan benar.\n- Menghitung magnitude vektor."
            ])
        elif role == "architect":
            return FakeListChatModel(responses=[
                "# Rencana Arsitektur\n## File Tree:\n- vector_math.py: Modul utama operasi vektor\n## Interface Contract:\n- dot_product(v1: list[float], v2: list[float]) -> float\n- magnitude(v: list[float]) -> float"
            ])
        elif role == "tester":
            return FakeListChatModel(responses=[
                "=== FILE: test_vector_math.py ===\nimport pytest\nfrom vector_math import dot_product, magnitude\n\ndef test_dot_product():\n    assert dot_product([1.0, 2.0], [3.0, 4.0]) == 11.0\n\ndef test_magnitude():\n    assert magnitude([3.0, 4.0]) == 5.0\n=== END FILE ==="
            ])
        elif role == "reviewer":
            return FakeListChatModel(responses=[
                "# Laporan Review Kode\n- Status: [APPROVED]\n- Analisis: Kode modular, penanganan error dimensi vektor telah dipasang, pengujian lulus 100%."
            ])
        else:
            return FakeListChatModel(responses=[
                "=== FILE: vector_math.py ===\nimport math\n\ndef dot_product(v1: list[float], v2: list[float]) -> float:\n    if len(v1) != len(v2):\n        raise ValueError('Dimensi tidak sama')\n    return sum(a * b for a, b in zip(v1, v2))\n\ndef magnitude(v: list[float]) -> float:\n    return math.sqrt(sum(a * a for a in v))\n=== END FILE ==="
            ])
        
    if selected_provider == "openrouter":
        from langchain_openai import ChatOpenAI
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        
        if role in ["pm", "architect", "reviewer"]:
            model = os.getenv("OPENROUTER_REASONING_MODEL", "anthropic/claude-3.5-sonnet")
        else:
            model = os.getenv("OPENROUTER_CODER_MODEL", "deepseek/deepseek-chat")
            
        return ChatOpenAI(
            model=model,
            openai_api_key=api_key,
            openai_api_base=base_url,
            temperature=0.2,
        )
    else:
        # Default: Ollama Local (Single resident model for 6GB VRAM)
        from langchain_ollama import ChatOllama
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        model = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
        num_ctx = int(os.getenv("OLLAMA_NUM_CTX", "2048"))
        
        role_num_predict = {
            "pm": 300,
            "architect": 350,
            "developer": 1000,
            "tester": 1000,
            "reviewer": 1000,
        }
        num_predict = int(os.getenv("OLLAMA_NUM_PREDICT", str(role_num_predict.get(role, 600))))
        
        return ChatOllama(
            base_url=base_url,
            model=model,
            num_ctx=num_ctx,
            num_predict=num_predict,
            temperature=0.2,
        )
