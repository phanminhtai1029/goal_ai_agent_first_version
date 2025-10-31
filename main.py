# File: main.py (Phiên bản cuối cùng - Sửa lỗi Event Loop)

import functions_framework
import telegram
import os
import logging
from flask import Request
import datetime
import asyncio

# Langchain
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_vertexai import ChatVertexAI

# Utils và Tools
from utils.security import check_rate_limit, log_message, log_security_event
from utils.secrets import get_secret, PROJECT_ID

# === KHỞI TẠO LƯỜI (AGENT) ===
_agent_executor = None
_my_telegram_id = None
_webhook_secret = None
# SỬA LỖI: Xóa _bot khỏi đây

def get_agent_and_secrets():
    """
    Hàm này chỉ khởi tạo Agent và tải Secrets.
    Bot sẽ được tạo riêng.
    """
    global _agent_executor, _my_telegram_id, _webhook_secret
    
    # Nếu đã khởi tạo, trả về ngay lập tức
    if _agent_executor:
        return _agent_executor, _my_telegram_id, _webhook_secret

    logging.info("Đang thực hiện khởi tạo Agent (cold start)...")
    
    MY_TELEGRAM_ID = get_secret("MY_TELEGRAM_ID")
    WEBHOOK_SECRET = get_secret("WEBHOOK_SECRET")

    if not MY_TELEGRAM_ID or not WEBHOOK_SECRET:
         raise ValueError("Không thể tải MY_TELEGRAM_ID hoặc WEBHOOK_SECRET.")

    _my_telegram_id = MY_TELEGRAM_ID
    _webhook_secret = WEBHOOK_SECRET

    llm = ChatVertexAI(
        model_name="gemini-2.5-flash",
        location="asia-southeast1"
    )

    from tools.calendar_tool import add_calendar_event, list_calendar_events
    from tools.rag_tool import add_to_rag, ask_rag
    from tools.admin_tool import trigger_manual_cleanup, get_system_status

    tools = [
        add_calendar_event, list_calendar_events, add_to_rag,
        ask_rag, trigger_manual_cleanup, get_system_status
    ]

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", (
                "Bạn là một trợ lý AI cá nhân thông minh và bảo mật, tên là 'GCP-Assistant'.\n"
                "Bạn chỉ nói chuyện với chủ nhân của mình (admin).\n"
                "Nhiệm vụ của bạn là giúp admin quản lý lịch (Google Calendar), "
                "tra cứu thông tin đã lưu (RAG), và quản lý hệ thống.\n"
                "Bạn PHẢI sử dụng các công cụ (tools) được cung cấp khi có yêu cầu."
                "Khi sử dụng tool 'add_calendar_event' hoặc 'list_calendar_events', "
                "bạn phải suy luận ra thời gian `start_time_str` và `end_time_str` "
                "ở định dạng ISO 8601 (ví dụ: 2025-10-28T09:00:00+07:00) "
                "dựa trên tin nhắn của người dùng (ví dụ: 'ngày mai', '8h sáng')."
                "Thời gian hiện tại là: {current_time}"
            )),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ]
    )

    agent = create_tool_calling_agent(llm, tools, prompt)
    _agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    
    logging.info("...Khởi tạo Agent hoàn tất.")
    
    return _agent_executor, _my_telegram_id, _webhook_secret

# === HÀM GỬI TIN NHẮN (ASYNC) MỚI ===
async def send_telegram_message(chat_id: int, text: str):
    """
    Tạo Bot object mới và gửi tin nhắn.
    Điều này đảm bảo không dùng lại client từ event loop đã đóng.
    """
    bot_token = get_secret("BOT_TOKEN")
    if not bot_token:
        logging.error("❌ Không thể lấy BOT_TOKEN để gửi tin nhắn.")
        return

    bot = telegram.Bot(token=bot_token)
    try:
        await bot.send_message(chat_id=chat_id, text=text)
    except Exception as e:
        logging.error(f"❌ Lỗi khi gửi tin nhắn: {e}")
    finally:
        # Quan trọng: Đóng client sau khi gửi
        await bot.shutdown()


@functions_framework.http
def telegram_webhook(request: Request): # <--- Giữ hàm này là ĐỒNG BỘ (def)
    """HTTP Cloud Function để nhận webhook từ Telegram."""

    try:
        agent_executor, MY_TELEGRAM_ID, WEBHOOK_SECRET = get_agent_and_secrets()
    except Exception as e:
        logging.error(f"❌ LỖI KHỞI TẠO NGHIÊM TRỌNG: {e}")
        return ("OK", 200)

    token = request.args.get("token")
    if token != WEBHOOK_SECRET:
        logging.warning("⚠️ Lỗi xác thực Webhook! Token không hợp lệ.")
        return ("OK", 200)

    try:
        # SỬA LỖI: Không cần `bot` ở đây để parse
        update_json = request.get_json(force=True)
        if not update_json.get("message") or not update_json["message"].get("text"):
            return ("OK", 200)
        
        user_id = str(update_json["message"]["from"]["id"])
        chat_id = update_json["message"]["chat"]["id"]
        message_text = update_json["message"]["text"]

        if user_id != MY_TELEGRAM_ID:
            logging.warning(f"⚠️ Truy cập trái phép từ ID: {user_id}")
            log_security_event(user_id, "unauthorized_access")
            return ("OK", 200)

        if not check_rate_limit(user_id):
            logging.warning(f"⚠️ Rate limit cho admin: {user_id}")
            asyncio.run(send_telegram_message(chat_id, "Bạn thao tác quá nhanh, vui lòng thử lại sau 1 giờ."))
            return ("OK", 200)

        log_message(user_id, message_text)
        logging.info(f"Đang xử lý tin nhắn: {message_text}")

        current_time = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7))).isoformat()
        
        response = agent_executor.invoke({
            "input": message_text,
            "current_time": current_time
        })
        response_text = response.get("output", "Đã có lỗi xảy ra, không có output.")

        # SỬA LỖI: Gọi hàm helper mới
        asyncio.run(send_telegram_message(chat_id, response_text))
        return ("OK", 200)

    except Exception as e:
        logging.error(f"❌ Lỗi nghiêm trọng trong function: {e}")
        try:
            # SỬA LỖI: Gọi hàm helper mới
            asyncio.run(send_telegram_message(int(MY_TELEGRAM_ID), f"Bot gặp lỗi: {e}"))
        except Exception:
            pass
        return ("OK", 200)

# === PHẦN CODE CHO CLEANUP FUNCTION (Giữ nguyên) ===
@functions_framework.cloud_event
def cleanup_exports(cloud_event):
    # ... (Code hàm này giữ nguyên) ...
    logging.info("🧹 Bắt đầu job dọn dẹp file export...")
    try:
        from google.cloud import storage
        from datetime import datetime, timedelta, timezone
        storage_client = storage.Client()
        bucket_name = "ai-assistant-exports-kource-123" # <--- SỬA TÊN BUCKET CỦA BẠN
        bucket = storage_client.get_bucket(bucket_name)
        seven_days_ago = datetime.utcnow().replace(tzinfo=timezone.utc) - timedelta(days=7)
        blobs = bucket.list_blobs()
        deleted_count = 0
        for blob in blobs:
            if blob.time_created < seven_days_ago:
                logging.info(f"Đang xóa file: {blob.name} (Ngày tạo: {blob.time_created})")
                blob.delete()
                deleted_count += 1
        logging.info(f"✅ Dọn dẹp thành công. Đã xóa {deleted_count} file.")
    except Exception as e:
        logging.error(f"❌ Lỗi khi dọn dẹp: {e}")