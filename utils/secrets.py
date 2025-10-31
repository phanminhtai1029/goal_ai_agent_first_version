# File: utils/secrets.py
import os
from google.cloud import secretmanager

_client = None
_secrets_cache = {}
PROJECT_ID = os.environ.get("PROJECT_ID", "gen-lang-client-0606372086") # Đặt project ID của bạn làm mặc định

def _get_client():
    """Khởi tạo client một lần."""
    global _client
    if _client is None:
        _client = secretmanager.SecretManagerServiceClient()
    return _client

def get_secret(secret_id: str) -> str:
    """Lấy secret từ cache hoặc tải mới."""
    if secret_id in _secrets_cache:
        return _secrets_cache[secret_id]
    
    try:
        client = _get_client()
        name = f"projects/{PROJECT_ID}/secrets/{secret_id}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        value = response.payload.data.decode("UTF-8")
        _secrets_cache[secret_id] = value
        return value
    except Exception as e:
        print(f"Lỗi: Không thể lấy secret '{secret_id}'. {e}")
        # Trả về None hoặc raise lỗi tùy bạn
        return None

# --- KHÔNG KHỞI TẠO BẤT KỲ BIẾN NÀO Ở ĐÂY ---
# Xóa các dòng: BOT_TOKEN = get_secret(...)