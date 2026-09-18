"""
llm_factory.py — Factory trung tâm để tạo LLM client cho từng task.

Tất cả agent trong hệ thống đều gọi hàm này thay vì tự tạo LLM.
Cấu hình model/provider/temperature được kéo từ settings.py (đọc từ .env).

Cách dùng:
    from shared.llm_factory import create_llm_for_task

    llm = create_llm_for_task("content_writer")   # Dùng model mạnh (gpt-4o)
    llm = create_llm_for_task("image_picker")     # Dùng model rẻ (gpt-4o-mini)

Thêm task mới:
    1. Khai báo profile trong settings.py (3 dòng: PROVIDER, MODEL, TEMP)
    2. Thêm entry vào TASK_PROFILES trong file này
    3. Trong agent: llm = create_llm_for_task("ten_task_moi")
"""

from langchain_core.language_models import BaseChatModel
from config.settings import (
    # Global default
    LLM_PROVIDER, LLM_MODEL,
    GEMINI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY,
    # Per-task profiles
    LLM_CONTENT_WRITER_PROVIDER, LLM_CONTENT_WRITER_MODEL, LLM_CONTENT_WRITER_TEMP,
    LLM_IMAGE_PICKER_PROVIDER,   LLM_IMAGE_PICKER_MODEL,   LLM_IMAGE_PICKER_TEMP,
)


# ==============================================
# REGISTRY: Mapping task name → LLM profile
# ==============================================
# Khi thêm task mới vào settings.py, thêm entry tương ứng ở đây.
TASK_PROFILES: dict[str, dict] = {
    "content_writer": {
        "provider":    LLM_CONTENT_WRITER_PROVIDER,
        "model":       LLM_CONTENT_WRITER_MODEL,
        "temperature": LLM_CONTENT_WRITER_TEMP,
    },
    "image_picker": {
        "provider":    LLM_IMAGE_PICKER_PROVIDER,
        "model":       LLM_IMAGE_PICKER_MODEL,
        "temperature": LLM_IMAGE_PICKER_TEMP,
    },
    # ── Thêm task mới bên dưới theo đúng pattern ──────────────────────────
    # "ten_task": {
    #     "provider":    LLM_TEN_TASK_PROVIDER,
    #     "model":       LLM_TEN_TASK_MODEL,
    #     "temperature": LLM_TEN_TASK_TEMP,
    # },
}

# Global fallback (dùng khi task name không có trong registry)
_DEFAULT_PROFILE: dict = {
    "provider":    LLM_PROVIDER,
    "model":       LLM_MODEL,
    "temperature": 0.7,
}


def _get_api_key(provider: str) -> str:
    """Lấy API key tương ứng với provider."""
    key_map = {
        "gemini": GEMINI_API_KEY,
        "openai": OPENAI_API_KEY,
        "claude": ANTHROPIC_API_KEY,
    }
    key = key_map.get(provider, "")
    if not key:
        raise ValueError(
            f"API key cho provider '{provider}' chưa được cấu hình trong .env. "
            f"Kiểm tra: GEMINI_API_KEY / OPENAI_API_KEY / ANTHROPIC_API_KEY"
        )
    return key


def create_llm_for_task(task_name: str) -> BaseChatModel:
    """
    Tạo và trả về LLM client theo profile của task.

    Args:
        task_name: Tên task đã đăng ký trong TASK_PROFILES.
                   Nếu không tìm thấy → dùng global default và cảnh báo.

    Returns:
        BaseChatModel ready to use với .invoke() / .stream()

    Raises:
        ValueError: Nếu provider không hợp lệ hoặc thiếu API key.
    """
    profile = TASK_PROFILES.get(task_name)
    if profile is None:
        print(f"[llm_factory] ⚠️ Task '{task_name}' chưa có profile riêng. Dùng global default.")
        profile = _DEFAULT_PROFILE

    provider    = profile["provider"].lower()
    model       = profile["model"]
    temperature = profile["temperature"]
    api_key     = _get_api_key(provider)

    print(f"[llm_factory] Task '{task_name}' → {provider.upper()} / {model} (temp={temperature})")

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=api_key,
            temperature=temperature,
        )

    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model,
            api_key=api_key,
            temperature=temperature,
        )

    elif provider == "claude":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=model,
            api_key=api_key,
            temperature=temperature,
        )

    else:
        raise ValueError(
            f"LLM provider '{provider}' không hợp lệ. "
            f"Chỉ nhận: 'gemini', 'openai', 'claude'"
        )
