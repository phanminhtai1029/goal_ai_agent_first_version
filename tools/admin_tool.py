# File: tools/admin_tool.py
from langchain.tools import tool
from google.cloud import storage, pubsub_v1, firestore
from utils.secrets import get_secret, PROJECT_ID # Import PROJECT_ID

_storage_client = None
_db = None
_publisher = None
_topic_path = None

def _get_clients():
    """Khởi tạo các client admin một lần."""
    global _storage_client, _db, _publisher, _topic_path
    if _storage_client is None:
        _storage_client = storage.Client()
    if _db is None:
        _db = firestore.Client(database="vector-database-test")
    if _publisher is None:
        _publisher = pubsub_v1.PublisherClient()
        _topic_path = _publisher.topic_path(PROJECT_ID, "run-cleanup-job")
    return _storage_client, _db, _publisher, _topic_path

@tool
def trigger_manual_cleanup():
    """Kích hoạt dọn dẹp thủ công."""
    try:
        _, _, publisher, topic_path = _get_clients()
        future = publisher.publish(topic_path, b"Triggered by admin")
        message_id = future.result() 
        return f"Đã kích hoạt dọn dẹp thủ công. Message ID: {message_id}"
    except Exception as e:
        return f"Lỗi khi kích hoạt cleanup: {e}"

@tool
def get_system_status():
    """Lấy tình trạng hệ thống."""
    try:
        storage_client, db, _, _ = _get_clients()
        
        rag_docs_query = db.collection('rag_documents').count()
        logs_query = db.collection('message_logs').count()
        sec_logs_query = db.collection('security_logs').count()
        
        rag_result = rag_docs_query.get()
        logs_result = logs_query.get()
        sec_logs_result = sec_logs_query.get()
        
        rag_count = rag_result[0][0].value if rag_result and rag_result[0] else 0
        logs_count = logs_result[0][0].value if logs_result and logs_result[0] else 0
        sec_logs_count = sec_logs_result[0][0].value if sec_logs_result and sec_logs_result[0] else 0
        
        bucket_name = "ai-assistant-exports-kource-123" # <--- SỬA TÊN BUCKET CỦA BẠN
        bucket = storage_client.get_bucket(bucket_name)
        blobs = list(bucket.list_blobs())
        total_size_bytes = sum([blob.size for blob in blobs])
        total_size_mb = total_size_bytes / (1024 * 1024)
        
        return (
            f"**Báo cáo Hệ thống:**\n"
            f"**Firestore (Số lượng):**\n"
            f"- Tài liệu RAG: {rag_count}\n"
            f"- Logs tin nhắn: {logs_count}\n"
            f"- Logs bảo mật: {sec_logs_count}\n"
            f"**Cloud Storage (Bucket: {bucket_name}):**\n"
            f"- Tổng số file: {len(blobs)}\n"
            f"- Tổng dung lượng: {total_size_mb:.2f} MB"
        )
    except Exception as e:
        return f"Lỗi khi lấy status: {e}"