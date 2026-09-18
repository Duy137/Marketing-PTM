"""
content_writer.py — Node 2: Gọi LLM để viết bài đăng fanpage.

Dùng LLM profile 'content_writer' được cấu hình trong settings.py / .env.
Thay đổi model/provider: Sửa biến LLM_CONTENT_WRITER_* trong .env.

Nhận vào: chủ đề + mode từ state
Trả về: bài viết hoàn chỉnh đã có CTA và địa chỉ đầy đủ
"""

from langchain_core.messages import SystemMessage, HumanMessage

from config.settings import SYSTEM_PROMPT_FILE, LLM_CONTENT_WRITER_PROVIDER, LLM_CONTENT_WRITER_MODEL
from shared.llm_factory import create_llm_for_task
from agents.state import PostState



def _load_system_prompt() -> str:
    """Đọc system prompt từ file. Chỉnh sửa prompt mà không cần sửa code."""
    return SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")


def _strip_markdown(text: str) -> str:
    """
    Post-processing: Xóa toàn bộ ký tự Markdown trong output của LLM.
    GPT-4o được fine-tune mặc định dùng Markdown nên cần strip sau khi nhận response.
    Lớp phòng thủ cuối cùng — đảm bảo 100% output sạch.
    """
    import re
    # **bold** hoặc __bold__ → chữ bình thường
    text = re.sub(r'(\*\*|__)(.*?)\1', r'\2', text)
    # *italic* hoặc _italic_ → chữ bình thường
    text = re.sub(r'(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)', r'\1', text)
    text = re.sub(r'(?<!_)_(?!_)(.*?)(?<!_)_(?!_)', r'\1', text)
    # ### Tiêu đề → bỏ ký tự #
    text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)
    # ```code block``` → bỏ
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    # `inline code` → bỏ backtick, giữ nội dung
    text = re.sub(r'`(.*?)`', r'\1', text)
    return text.strip()


# ==============================================
# NODE FUNCTION
# ==============================================

def write_content(state: PostState) -> PostState:
    """
    Gọi LLM (profile 'content_writer' trong settings.py) để viết bài fanpage.
    """
    print(f"[content_writer] Dùng {LLM_CONTENT_WRITER_PROVIDER.upper()} ({LLM_CONTENT_WRITER_MODEL})")
    print(f"[content_writer] Đang viết bài: [{state['mode']}] {state['topic_title']}")

    llm = create_llm_for_task("content_writer")

    user_prompt = (
        f"Mode: {state['mode']}\n"
        f"Sản phẩm: {state['san_pham']}\n"
        f"Chủ đề bài viết: {state['topic_title']}\n\n"
        f"Hãy viết bài fanpage hoàn chỉnh theo đúng mode và chủ đề trên. "
        f"Tuân thủ đúng quy tắc và cấu trúc của mode đã được định nghĩa trong System Prompt.\n\n"
        f"YÊU CẦU ĐỊNH DẠNG OUTPUT (bắt buộc tuân thủ):\n"
        f"Output dành cho Facebook — nền tảng chỉ hiển thị plain text và emoji, "
        f"không render Markdown. Vì vậy:\n"
        f"✦ Chỉ được dùng ký tự Unicode thuần và emoji.\n"
        f"✦ Ký tự * # _ ` hoàn toàn không được xuất hiện trong output.\n"
        f"✦ Để làm nổi bật: dùng emoji (ví dụ 🔥 ✨ 💎) thay vì in đậm.\n"
        f"✦ Để đánh số: dùng 1️⃣ 2️⃣ 3️⃣ thay vì '1.' '2.' '3.'\n"
        f"✦ Để liệt kê: dùng ✅ 👉 🔹 ⚡ thay vì dấu gạch đầu dòng."
    )

    messages = [
        SystemMessage(content=_load_system_prompt()),
        HumanMessage(content=user_prompt),
    ]
    response = llm.invoke(messages)
    post_content = _strip_markdown(response.content)

    print(f"[content_writer] Viết bài xong ({len(post_content)} ký tự)")

    return {
        **state,
        "post_content": post_content,
    }
