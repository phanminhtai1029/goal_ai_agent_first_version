# File: tools/calendar_tool.py (Đã thêm docstring)

from langchain.tools import tool
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from utils.secrets import get_secret
import datetime

_calendar_service = None

def _get_calendar_service():
    # ... (code bên trong hàm này giữ nguyên) ...
    global _calendar_service
    if _calendar_service:
        return _calendar_service
    GCAL_CLIENT_ID = get_secret("GCAL_CLIENT_ID")
    GCAL_CLIENT_SECRET = get_secret("GCAL_CLIENT_SECRET")
    GCAL_REFRESH_TOKEN = get_secret("GCAL_REFRESH_TOKEN")
    creds = Credentials.from_authorized_user_info({
        "client_id": GCAL_CLIENT_ID, "client_secret": GCAL_CLIENT_SECRET, "refresh_token": GCAL_REFRESH_TOKEN
    }, ['https://www.googleapis.com/auth/calendar'])
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
    _calendar_service = build('calendar', 'v3', credentials=creds)
    return _calendar_service

@tool
def add_calendar_event(event_summary: str, start_time_str: str, end_time_str: str = None):
    """
    Dùng để thêm một sự kiện hoặc nhắc nhở vào Google Calendar.
    Ví dụ: "Nhắc tôi 8h sáng mai đi học", "Thêm lịch họp team lúc 3h chiều nay".
    Input:
        event_summary (str): Tóm tắt sự kiện (ví dụ: 'Đi học').
        start_time_str (str): Thời gian bắt đầu (format ISO 8601, ví dụ: '2025-10-28T09:00:00+07:00').
        end_time_str (str, optional): Thời gian kết thúc. Nếu không có, sự kiện kéo dài 1 giờ.
    """
    # ... (code bên trong hàm giữ nguyên) ...
    try:
        service = _get_calendar_service()
        start_time = datetime.datetime.fromisoformat(start_time_str)
        if end_time_str:
            end_time = datetime.datetime.fromisoformat(end_time_str)
        else:
            end_time = start_time + datetime.timedelta(hours=1)
        event = {
            'summary': event_summary,
            'start': {'dateTime': start_time.isoformat(), 'timeZone': 'Asia/Ho_Chi_Minh'},
            'end': {'dateTime': end_time.isoformat(), 'timeZone': 'Asia/Ho_Chi_Minh'},
        }
        event = service.events().insert(calendarId='primary', body=event).execute()
        return f"Đã thêm sự kiện thành công: {event.get('htmlLink')}"
    except Exception as e:
        return f"Lỗi khi thêm sự kiện: {e}."

@tool
def list_calendar_events(start_time_str: str, end_time_str: str):
    """
    Dùng để xem các sự kiện trong một khoảng thời gian cụ thể trên Google Calendar.
    Ví dụ: 'Xem lịch của tôi ngày mai', 'Thứ 7 này tôi có bận gì không?', 'Lịch tuần tới của tôi thế nào?'.
    Input:
        start_time_str (str): Thời gian bắt đầu khoảng cần xem (ISO 8601).
        end_time_str (str): Thời gian kết thúc khoảng cần xem (ISO 8601).
    """
    # ... (code bên trong hàm giữ nguyên) ...
    try:
        service = _get_calendar_service()
        events_result = service.events().list(
            calendarId='primary', timeMin=start_time_str, timeMax=end_time_str,
            singleEvents=True, orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])
        if not events:
            return "Không có sự kiện nào trong khoảng thời gian này."
        event_list = [f"- {e['start'].get('dateTime', e['start'].get('date'))}: {e['summary']}" for e in events]
        return "Các sự kiện của bạn:\n" + "\n".join(event_list)
    except Exception as e:
        return f"Lỗi khi xem lịch: {e}."