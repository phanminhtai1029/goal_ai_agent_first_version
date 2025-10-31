# File: utils/security.py (Đã sửa lỗi TTL)

from datetime import datetime, timedelta, timezone # Thêm timedelta và timezone
from google.cloud import firestore
from google.cloud.firestore_v1.aggregation import AggregationQuery
from google.cloud.firestore_v1.base_query import FieldFilter 

_db = None

def _get_db():
    """Khởi tạo DB một lần."""
    global _db
    if _db is None:
        _db = firestore.Client(database="vector-database-test")
    return _db

def check_rate_limit(user_id: str) -> bool:
    db = _get_db()
    
    # SỬA LỖI: Query theo trường "thời gian tạo"
    one_hour_ago = datetime.utcnow().replace(tzinfo=timezone.utc) - timedelta(hours=1)
    logs_ref = db.collection('message_logs')
    
    query = logs_ref.where(filter=FieldFilter("user_id", "==", user_id)) \
                    .where(filter=FieldFilter("timestamp_created", ">=", one_hour_ago)) # <--- SỬA TÊN TRƯỜNG
    
    aggregate_query = query.count()
    result = aggregate_query.get()
    
    count = result[0][0].value if result and result[0] else 0
    
    return count < 100

def log_message(user_id: str, text: str):
    db = _get_db()
    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    
    # SỬA LỖI: Tạo timestamp hết hạn sau 7 ngày
    expire_at = now + timedelta(days=7) 

    db.collection('message_logs').add({
        "user_id": user_id,
        "text": text,
        "timestamp_created": now, # <--- Trường mới để query
        "timestamp": expire_at     # <--- Trường cũ cho TTL (hết hạn sau 7 ngày)
    })

def log_security_event(user_id: str, event_type: str):
    db = _get_db()
    now = datetime.utcnow().replace(tzinfo=timezone.utc)

    # SỬA LỖI: Tạo timestamp hết hạn sau 30 ngày (log bảo mật có thể giữ lâu hơn)
    expire_at = now + timedelta(days=30) 

    db.collection('security_logs').add({
        "user_id": user_id,
        "event": event_type,
        "timestamp_created": now, # <--- Trường mới để query (nếu cần)
        "timestamp": expire_at     # <--- Trường cũ cho TTL (hết hạn sau 30 ngày)
    })