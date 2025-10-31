Dưới đây là file `README.md` hoàn chỉnh cho dự án của bạn, được tổng hợp từ toàn bộ lịch sử trò chuyện và quá trình gỡ lỗi của chúng ta.

-----

# AI Planning Assistant (Google Cloud + LangChain Edition)

Một trợ lý AI cá nhân, bảo mật, được triển khai hoàn toàn trên hạ tầng Serverless của Google Cloud và điều khiển bởi LangChain. Dự án này được tối ưu hóa để chạy 100% trong Gói Miễn phí (Free Tier) của GCP.

## 1\. Giới thiệu

Dự án này xây dựng một bot AI cá nhân trên Telegram, hoạt động như một "bộ não" thứ hai. Thay vì sử dụng nhiều ứng dụng khác nhau (ghi chú, lịch, nhắc nhở), trợ lý này cung cấp một giao diện trò chuyện duy nhất để:

  * Quản lý lịch biểu và lời nhắc thông qua Google Calendar.
  * Lưu trữ và truy vấn kiến thức cá nhân (ghi chú, ý tưởng, tài liệu) bằng cách sử dụng pipeline RAG (Retrieval-Augmented Generation).
  * Thực hiện các tác vụ quản trị hệ thống cơ bản.

Mục tiêu cốt lõi là tạo ra một trợ lý AI mạnh mẽ, hoàn toàn riêng tư (chỉ phản hồi cho chủ nhân) và có chi phí vận hành bằng 0 bằng cách tận dụng tối đa các dịch vụ trong Gói Miễn phí của Google Cloud.

## 2\. Kiến trúc Tổng quan

Hệ thống bao gồm hai Cloud Functions (Thế hệ 2) riêng biệt, chạy trên cùng một cơ sở mã nguồn.

### Luồng 1: Tương tác Bot (HTTP Trigger)

Luồng chính xử lý tin nhắn của người dùng qua Telegram.

```
Người dùng (Telegram)
      |
      v
Telegram Webhook (Gửi tin nhắn POST)
      |
      v
[GCP Cloud Function 1: telegram_webhook] (HTTP Trigger)
      |
      1. Xác thực (Webhook Token & User ID)
      |
      v
[LangChain Agent (Vertex AI)]
      |
      2. Phân tích tin nhắn, chọn Tool (Công cụ)
      |
      +------------------+------------------+------------------+
      |                  |                  |                  |
      v                  v                  v                  v
[Tool: Calendar]   [Tool: RAG]        [Tool: Admin]      (Các Tool khác)
      |                  |                  |
<-> [Google Calendar API]  <-> [Firestore Vector DB]  <-> [GCS / Firestore]
      |                  |                  |
      +------------------+------------------+
      |
      v
[LangChain Agent (Vertex AI)]
      |
      3. Tổng hợp kết quả, tạo phản hồi
      |
      v
[GCP Cloud Function 1]
      |
      4. Gửi phản hồi (via Telegram Bot API)
      |
      v
Người dùng (Telegram)
```

### Luồng 2: Dọn dẹp tự động (Pub/Sub Trigger)

Một luồng nền, chạy hàng ngày để dọn dẹp các file export cũ (nếu có) trong Cloud Storage.

```
[GCP Cloud Scheduler] (Chạy lúc 2:00 sáng)
      |
      v
[GCP Pub/Sub Topic: run-cleanup-job]
      |
      v
[GCP Cloud Function 2: cleanup_exports] (Pub/Sub Trigger)
      |
      v
[Google Cloud Storage (GCS)]
      |
      1. Liệt kê file
      2. Xóa file cũ (ví dụ: > 7 ngày)
```

## 3\. Các thành phần chính (Tech Stack)

  * **Orchestration (Điều phối):** LangChain (`langchain`)
  * **AI Models (LLM & Embeddings):** Google Vertex AI
      * **LLM:** `gemini-2.5-flash`
      * **Embedding:** `text-embedding-004`
  * **Serverless (Compute):** Google Cloud Functions (2nd Gen)
  * **Database (Chính & Vector):** Google Cloud Firestore (Native Mode, hỗ trợ Vector Search)
  * **File Storage:** Google Cloud Storage (GCS)
  * **Scheduling & Events:** Google Calendar API, Google Cloud Scheduler, Google Cloud Pub/Sub
  * **Security & Secrets:** Google Secret Manager, Google Cloud IAM
  * **Interface:** Telegram Bot API
  * **Python Libraries:** `python-telegram-bot`, `langchain-google-vertexai`, `google-cloud-firestore`, v.v. (xem `requirements.txt`)

## 4\. Hướng dẫn Cài đặt và Triển khai

### Bước 1: Cấu hình Google Cloud Project

1.  Tạo một Project mới trên [Google Cloud Console](https://console.cloud.google.com/). Ghi lại **Project ID** (ví dụ: `gen-lang-client-0606372086`).
2.  Kích hoạt (Enable) tất cả các API sau trong mục "APIs & Services" -\> "Library":
      * Cloud Functions API
      * Cloud Build API
      * Artifact Registry API
      * Cloud Run API (Cloud Functions Gen 2 chạy trên Cloud Run)
      * Vertex AI API
      * Cloud Firestore API
      * Cloud Storage
      * Secret Manager API
      * Google Calendar API
      * Cloud Scheduler API
      * Cloud Pub/Sub API

### Bước 2: Cấu hình Bảo mật và IAM

1.  **Tạo Service Account (Tài khoản Dịch vụ):**

      * Đi đến "IAM & Admin" -\> "Service Accounts".
      * Tạo một Service Account mới (ví dụ: `ai-assistant-service-account`).
      * Cấp cho Service Account này các vai trò (Roles) sau:
          * `Cloud Functions Invoker` (Để gọi các function, nếu cần)
          * `Vertex AI User` (Để gọi mô hình Gemini)
          * `Cloud Datastore User` (Để đọc/ghi Firestore)
          * `Storage Admin` (Để đọc/ghi/xóa file trên GCS)
          * `Secret Manager Secret Accessor` (Để đọc secrets)
          * `Eventarc Event Receiver` (Để nhận sự kiện Pub/Sub)
      * Ghi lại email của Service Account này (ví dụ: `ai-assistant-service-account@...iam.gserviceaccount.com`).

2.  **Lấy OAuth 2.0 cho Google Calendar:**

      * Đi đến "APIs & Services" -\> "Credentials".
      * Tạo "OAuth 2.0 Client ID", chọn loại "Desktop app".
      * Tải file `credentials.json` về máy.
      * Chạy một script Python (ví dụ `get_refresh_token.py`) trên máy local của bạn để thực hiện quy trình OAuth một lần. (Script này không có trong repo).
      * Kết quả, bạn sẽ nhận được 3 giá trị: `GCAL_CLIENT_ID`, `GCAL_CLIENT_SECRET`, và `GCAL_REFRESH_TOKEN`.

### Bước 3: Cấu hình Bot và Secrets

1.  **Telegram:**
      * Nói chuyện với `@BotFather` trên Telegram để tạo bot mới. Lấy `BOT_TOKEN`.
      * Nói chuyện với `@userinfobot` để lấy `MY_TELEGRAM_ID` (chỉ bot này mới phản hồi ID này).
      * Tạo một chuỗi ngẫu nhiên dài (ví dụ: 64 ký tự) để làm `WEBHOOK_SECRET`.
2.  **Secret Manager:**
      * Đi đến dịch vụ "Secret Manager".
      * Tạo các secret sau và lưu trữ các giá trị tương ứng:
          * `BOT_TOKEN`
          * `MY_TELEGRAM_ID`
          * `WEBHOOK_SECRET`
          * `GCAL_REFRESH_TOKEN`
          * `GCAL_CLIENT_ID`
          * `GCAL_CLIENT_SECRET`
          * `PROJECT_ID` (Lưu Project ID của bạn)

### Bước 4: Cấu hình Firestore

1.  **Tạo Database:**
      * Đi đến "Firestore", tạo Database, chọn **"Native Mode"** và chọn khu vực (ví dụ: `asia-southeast1`).
      * Ghi lại tên Database ID (ví dụ: `vector-database-test`).
2.  **Tạo TTL Policies (Tự động xóa logs):**
      * Trong Firestore, vào tab "Time-to-live (TTL)".
      * Tạo policy cho `message_logs`, chọn trường `timestamp`.
      * Tạo policy cho `security_logs`, chọn trường `timestamp`.
3.  **Tạo Indexes (Bắt buộc):**
      * Chạy các lệnh `gcloud` sau để tạo chỉ mục cho RAG và logs. (Thay thế Project ID và Database ID của bạn).
      * **Index cho RAG (Vector Search):**
    <!-- end list -->
    ```bash
    gcloud firestore indexes composite create \
      --project=gen-lang-client-0606372086 \
      --database="vector-database-test" \
      --collection-group=rag_documents \
      --query-scope=COLLECTION \
      --field-config=vector-config='{"dimension":"768","flat": "{}"}',field-path=embedding
    ```
      * **Index cho Logs (Rate Limit):**
    <!-- end list -->
    ```bash
    gcloud firestore indexes composite create \
      --project=gen-lang-client-0606372086 \
      --database="vector-database-test" \
      --collection-group=message_logs \
      --field-config=field-path=user_id,order=ASCENDING \
      --field-config=field-path=timestamp_created,order=ASCENDING
    ```

### Bước 5: Cài đặt Thư viện

Trên máy local, cài đặt các thư viện cần thiết:

```bash
pip install -r requirements.txt
```

### Bước 6: Triển khai

(Đảm bảo `gcloud` CLI đã được cài đặt và xác thực: `gcloud auth login` và `gcloud config set project YOUR_PROJECT_ID`).

1.  **Deploy Function 1 (Bot chính):**

    ```bash
    gcloud functions deploy telegram_webhook \
      --gen2 \
      --runtime=python311 \
      --region=asia-southeast1 \
      --source=. \
      --entry-point=telegram_webhook \
      --trigger-http \
      --allow-unauthenticated \
      --service-account=ai-assistant-service-account@gen-lang-client-0606372086.iam.gserviceaccount.com \
      --set-env-vars=PROJECT_ID=gen-lang-client-0606372086 \
      --memory=1Gi
    ```

2.  **Deploy Function 2 (Dọn dẹp):**

    ```bash
    gcloud functions deploy cleanup_exports \
      --gen2 \
      --runtime=python311 \
      --region=asia-southeast1 \
      --source=. \
      --entry-point=cleanup_exports \
      --trigger-topic=run-cleanup-job \
      --service-account=ai-assistant-service-account@gen-lang-client-0606372086.iam.gserviceaccount.com \
      --set-env-vars=PROJECT_ID=gen-lang-client-0606372086 \
      --memory=1Gi
    ```

### Bước 7: Cấu hình cuối cùng

1.  **Tạo Lịch (Scheduler):**
      * Đi đến "Cloud Scheduler".
      * Tạo Job mới, đặt tên (ví dụ: `daily-cleanup-job`), đặt tần suất (`0 2 * * *` cho 2 giờ sáng hàng ngày).
      * Target type: `Pub/Sub`.
      * Topic: `run-cleanup-job`.
      * Message body: `{}`
2.  **Kết nối Webhook:**
      * Lấy URL của function `telegram_webhook` (output từ Bước 6.1).
      * Lấy `BOT_TOKEN` và `WEBHOOK_SECRET` của bạn.
      * Mở trình duyệt và dán URL đã định dạng:
        `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=<YOUR_FUNCTION_URL>?token=<YOUR_WEBHOOK_SECRET>`
      * Nếu trình duyệt báo `{"ok":true...}`, bot của bạn đã hoạt động.

## 5\. Cấu trúc Thư mục

```
.
├── main.py             # Entry point cho cả telegram_webhook và cleanup_exports
├── requirements.txt    # Danh sách thư viện Python
├── tools/
│   ├── __init__.py
│   ├── admin_tool.py   # Công cụ: /status, /cleanup
│   ├── calendar_tool.py # Công cụ: Thêm/Xem lịch Google Calendar
│   └── rag_tool.py     # Công cụ: Thêm/Hỏi kiến thức RAG
└── utils/
    ├── __init__.py
    ├── secrets.py      # Hàm helper để tải secrets từ Secret Manager
    └── security.py     # Hàm helper: check_rate_limit, log_message
```

## 6\. Giải thích Chi tiết (Low-Level Workflow)

### Khởi tạo "Lười" (Lazy Initialization)

Để vượt qua lỗi `Container Healthcheck failed` (do hết bộ nhớ hoặc lỗi mạng khi khởi động), dự án này không khởi tạo bất kỳ client (VertexAI, Firestore, Telegram Bot) nào ở cấp độ toàn cục. Thay vào đó, các client được khởi tạo bên trong các hàm `_get_...()` (ví dụ: `get_agent_and_secrets()`) và được cache lại trong các biến toàn cục. Lần gọi đầu tiên (cold start) sẽ khởi tạo, các lần gọi sau (warm start) sẽ sửu dụng lại client đã cache.

### Xử lý Bất đồng bộ (Asyncio)

Thư viện `python-telegram-bot` yêu cầu `asyncio` (các hàm `await`). Tuy nhiên, Google Cloud Functions (HTTP) là một framework đồng bộ (dựa trên Flask). Điều này dẫn đến lỗi `Event loop is closed` khi cố gắng tái sử dụng client.

  * **Giải pháp:** Bot *không* được khởi tạo và cache lại. Thay vào đó, một hàm `async def send_telegram_message(...)` riêng biệt được tạo ra. Hàm này tự khởi tạo một `telegram.Bot` object mới, `await` nó, và `await bot.shutdown()` **mỗi khi** cần gửi tin nhắn. Hàm `telegram_webhook` (đồng bộ) gọi hàm này bằng `asyncio.run()`, tạo ra một vòng lặp sự kiện mới, sạch sẽ cho mỗi lần phản hồi.

### Luồng RAG (Tool: `rag_tool.py`)

1.  **Lưu (`add_to_rag`):**
      * Client `VertexAIEmbeddings` (`text-embedding-004`) được gọi để chuyển văn bản của người dùng thành một vector 768 chiều.
      * `FirestoreVectorStore` lưu tài liệu (văn bản gốc) và vector `embedding` vào collection `rag_documents`.
2.  **Hỏi (`ask_rag`):**
      * `_get_rag_chain()` được gọi (khởi tạo lười).
      * Hàm này tạo một `RetrievalChain` của LangChain.
      * Nó lấy câu hỏi, tạo vector cho câu hỏi.
      * `FirestoreVectorStore.as_retriever()` thực hiện tìm kiếm vector tương đồng trong Firestore (yêu cầu Index Vector đã tạo ở Bước 4).
      * Các tài liệu (context) được tìm thấy, cùng với câu hỏi gốc, được đưa vào prompt.
      * `ChatVertexAI` (`gemini-2.5-flash`) được gọi để trả lời câu hỏi *chỉ dựa trên* context được cung cấp.

### Luồng Lịch (Tool: `calendar_tool.py`)

1.  `_get_calendar_service()` được gọi (khởi tạo lười).
2.  Hàm này sử dụng `GCAL_REFRESH_TOKEN` (lấy từ Secret Manager) để tạo `Credentials`.
3.  Nó gọi `creds.refresh()` (nếu cần) để lấy `access_token` mới.
4.  Nó khởi tạo Google Calendar API client (`build('calendar', 'v3', ...)`).
5.  Các hàm `add_calendar_event` và `list_calendar_events` sử dụng client này để tương tác trực tiếp với API của Google.

### Luồng Bảo mật (File: `utils/security.py`)

1.  **Rate Limit:** Hàm `check_rate_limit` query collection `message_logs` để đếm số tài liệu có `user_id` trùng khớp và `timestamp_created` trong vòng 1 giờ qua. Nó dùng `query.count()` (chỉ tốn 1 read) thay vì tải toàn bộ tài liệu.
2.  **TTL (Time-to-Live):** Khi `log_message` hoặc `log_security_event` ghi một log, nó ghi 2 trường thời gian:
      * `timestamp_created`: (Thời gian hiện tại) Dùng cho query rate limit.
      * `timestamp`: (Thời gian hiện tại + 7 ngày) Dùng cho TTL. Firestore tự động xóa tài liệu này khi thời gian `timestamp` đến, giúp tiết kiệm dung lượng.

## 7\. Ví dụ Demo

Dưới đây là các ví dụ về cách bot hoạt động.

### Tương tác RAG và Calendar

(Nơi này để chèn ảnh demo `image_ae91f8.png` và `image_ae999d.png`)

### Tương tác Admin

(Nơi này để chèn ảnh demo `image_ae999d.png`)

## 8\. Hướng phát triển trong Tương lai

  * **Thêm Tools:** Tích hợp Google Search, API Thời tiết, hoặc Google Drive (để RAG trên file .pdf).
  * **Web UI:** Xây dựng một giao diện web đơn giản (ví dụ: Streamlit/Flask) chạy trên cùng một Cloud Run Service để xem logs, quản lý các tài liệu RAG, hoặc xem trạng thái hệ thống.
  * **Multi-Modal:** Nâng cấp `rag_tool` để sử dụng model Gemini Pro Vision, cho phép người dùng gửi ảnh (ví dụ: ảnh chụp màn hình code) và yêu cầu bot lưu lại/giải thích.
  * **Multi-User:** Mở rộng hệ thống bảo mật để hỗ trợ nhiều người dùng, thay vì chỉ hardcode `MY_TELEGRAM_ID`.
  * **CI/CD:** Tự động hóa các lệnh `gcloud functions deploy` bằng cách sử dụng GitHub Actions.
