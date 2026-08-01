# Project Specification: WhatsApp Message Notification Router

## 1. Overall Project Overview and Objectives

The objective of this project is to build an intelligent, multi-stage, cost-optimized backend routing engine and evaluation dashboard for WhatsApp messages. The system ingests multimodal messages (text, image posters, audio voice notes) and routes them into one of three categories: `notify` (urgent/interrupting), `digest` (batch for later), or `mute` (spam/noise).

The system utilizes a hybrid architecture:

1. **Deterministic Fast Path:** Evaluates regex/metadata rules to bypass expensive inference for obvious spam or direct mentions.
2. **Local C++ Audio Engine:** Compiles and executes `whisper.cpp` locally for sub-second, memory-efficient speech-to-text extraction without cloud API limits.
3. **Cloud Vision & LLM Routing (Deep Path):** Uses Google's `gemini-2.5-flash` model via the `google-genai` SDK to reason over user history, text, and image payloads dynamically.
4. **Evaluation Engine & Dashboard:** A web-based interface for administrators to visualize the routing decisions, view multimodal payload artifacts, and calculate system performance metrics against golden evaluation datasets.

## 2. Tech Stack Recommendations & Justification

### 2.1 Backend Engine & API

* **Language:** Python 3.11+
* **Framework:** FastAPI (High performance, async execution, built-in Pydantic v2 validation, automatic OpenAPI documentation).
* **Audio Processing:** C++ Native (`whisper.cpp`). Avoids Python wrapper overhead; executes as a detached subprocess for memory isolation and absolute zero API costs.
* **Audio Transcoding:** FFmpeg (Standard for converting `.ogg`/WhatsApp formats to 16kHz `.wav`).
* **LLM / VLM API:** `google-genai` SDK targeting `gemini-2.5-flash`. Chosen for its permanent free tier, extremely fast time-to-first-token (TTFT), and native capability to ingest images alongside text while outputting strict JSON schemas.

### 2.2 Database Layer

* **Database:** SQLite3 (Local) / DuckDB. Chosen for zero-setup local deployments, single-file portability, and sufficiently fast ACID compliance for local evaluation loops.
* **ORM/Query Builder:** SQLAlchemy 2.0.
* **Migrations:** Alembic.

### 2.3 Frontend Dashboard

* **Framework:** Next.js 14+ (App Router), React 18+.
* **Styling:** Tailwind CSS (Utility-first, rapid prototyping).
* **Component Library:** shadcn/ui (Accessible, headless Radix UI components, heavily customizable).
* **State Management:** React Query (Server state sync) + Zustand (Local UI state).
* **API Client:** Axios.

---

## 3. Architecture & System Flow

### 3.1 Message Routing Pipeline

1. **Ingestion:** API receives `POST /api/v1/route-message` containing message metadata (Sender, History, Text) and optional media file paths.
2. **Fast Path Rules Engine:**
* If `is_flagged_scam == true` -> Return `mute`.
* If text contains `@username` -> Return `notify`.
* If bypassed, proceed to Deep Path.


3. **Multimodal Extraction Layer:**
* **Audio:** If `audio_file_path` exists, subprocess executes FFmpeg (to 16kHz WAV) -> executes compiled `./whisper.cpp/main` -> returns transcript.
* **Image:** If `image_file_path` exists, the file is loaded into memory as a `PIL.Image` object.


4. **LLM Context Assembly:** Text, Audio Transcript, Image Object, and User Context are injected into a strict prompt.
5. **Inference Execution:** `gemini-2.5-flash` is invoked enforcing a strict Pydantic JSON `response_schema`.
6. **Persistence:** The decision, exact reasoning, and execution times are logged to SQLite.
7. **Response:** API returns JSON payload to client.

---

## 4. Folder and File Structure

```text
/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── routes/
│   │   │   │   ├── messages.py    # Ingestion API
│   │   │   │   ├── eval.py        # Evaluation API
│   │   ├── core/
│   │   │   ├── config.py          # Pydantic BaseSettings (Env vars)
│   │   │   ├── security.py        # Dashboard API auth
│   │   ├── db/
│   │   │   ├── database.py        # SQLAlchemy session & engine
│   │   │   ├── models.py          # SQLAlchemy tables
│   │   ├── schemas/
│   │   │   ├── message.py         # Pydantic models (Input/Output)
│   │   ├── services/
│   │   │   ├── router.py          # Core logic (Fast Path + Deep Path)
│   │   │   ├── audio_engine.py    # whisper.cpp subprocess wrapper
│   │   │   ├── vision_llm.py      # Google GenAI SDK implementation
│   │   │   ├── metrics.py         # Precision/Recall/F1 calculator
│   ├── dataset/
│   │   ├── messages.csv           # Provided test data
│   │   ├── media/                 # Local images/audio files
│   ├── whisper.cpp/               # Git submodule (compiled C++)
│   ├── requirements.txt
│   ├── main.py                    # FastAPI entrypoint
│   ├── alembic.ini
│   ├── alembic/                   # Migrations directory
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx         
│   │   │   ├── page.tsx           # Dashboard Overview
│   │   │   ├── logs/page.tsx      # Paginated Logs View
│   │   │   ├── eval/page.tsx      # Performance metrics UI
│   │   ├── components/
│   │   │   ├── ui/                # shadcn primitives
│   │   │   ├── shared/            # Layout, Nav, Sidebar
│   │   │   ├── message-card.tsx   # Visualizes message + reasoning
│   │   ├── lib/
│   │   │   ├── api.ts             # Axios instances
│   │   │   ├── utils.ts           # Tailwind merge utils
│   ├── package.json
│   ├── tailwind.config.ts
├── scripts/
│   ├── build_whisper.sh           # Script to compile C++ binary
│   ├── run_eval.py                # Headless CLI evaluation script
├── .env.example
├── docker-compose.yml

```

---

## 5. Database Schema (SQLite / SQLAlchemy)

### 5.1 Table: `messages`

Stores the raw input data and the resulting routing decision.

| Column | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | String(UUID) | Primary Key | Unique message identifier |
| `sender_name` | String | Not Null | Name of the sender |
| `sender_type` | String | Not Null | `contact`, `group`, `business`, `unknown` |
| `historical_engagement` | String | Nullable | Text summary of user interaction |
| `text_content` | Text | Nullable | Original text payload |
| `image_path` | String | Nullable | Path to local image |
| `audio_path` | String | Nullable | Path to local audio file |
| `audio_transcript` | Text | Nullable | Output generated by whisper.cpp |
| `is_flagged_scam` | Boolean | Default False | Upstream rule flag |
| `routing_decision` | String | Nullable | Enum: `notify`, `digest`, `mute` |
| `routing_reasoning` | Text | Nullable | CoT reasoning from LLM |
| `processing_time_ms` | Integer | Not Null | Time taken to evaluate |
| `created_at` | DateTime | Default UTC.now() | Timestamp |

### 5.2 Table: `evaluations`

Stores golden labels to compare against predictions.

| Column | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | String(UUID) | Primary Key | - |
| `message_id` | String(UUID) | Foreign Key(`messages.id`) | Links to message |
| `expected_decision` | String | Not Null | Golden label (`notify`, `digest`, `mute`) |

---

## 6. API Endpoints Specification

### 6.1 `POST /api/v1/route-message`

**Purpose:** Ingests a new message, processes multimodality, routes it, and persists the result.
**Authentication:** `Bearer Token` (Environment variable configured API key).
**Request Body (application/json):**

```json
{
  "message_id": "msg_12345",
  "sender_name": "John Doe",
  "sender_type": "contact",
  "historical_engagement": "User replies to this contact daily",
  "text": "Are we still on for 5pm?",
  "image_file_path": null,
  "audio_file_path": null,
  "is_flagged_scam": false
}

```

**Response Format (200 OK):**

```json
{
  "message_id": "msg_12345",
  "decision": "notify",
  "reasoning": "Direct contact with high engagement history asking a time-sensitive scheduling question.",
  "processing_time_ms": 842,
  "metrics": { "audio_ms": 0, "llm_ms": 840 }
}

```

### 6.2 `POST /api/v1/batch-eval`

**Purpose:** Triggers processing of the entire `messages.csv` payload and returns calculated metrics.
**Query Params:** `force_recalculate` (boolean, default false).
**Response Format (200 OK):**

```json
{
  "total_processed": 500,
  "accuracy": 0.94,
  "macro_f1": 0.92,
  "class_metrics": {
    "notify": { "precision": 0.95, "recall": 0.98, "f1": 0.96 },
    "mute": { "precision": 0.99, "recall": 0.91, "f1": 0.95 }
  }
}

```

### 6.3 `GET /api/v1/logs`

**Purpose:** Paginated fetching of processed messages for the dashboard.
**Query Params:** `page` (int, default 1), `limit` (int, default 50), `decision_filter` (string, optional).
**Response:** Paginated array of `messages` table rows.

---

## 7. Backend Logic & Services

### 7.1 Deterministic Rules Engine (`services/router.py`)

```python
def execute_fast_track(payload: MessageInput) -> str | None:
    if payload.is_flagged_scam:
        return "mute"
    
    user_handle = "@Rafay" # Parameterized in config
    if payload.text and user_handle.lower() in payload.text.lower():
        return "notify"
        
    return None # Fallthrough to LLM

```

### 7.2 Audio Engine Subprocess (`services/audio_engine.py`)

* **Dependency Check:** On startup, the API must verify `./whisper.cpp/main` exists. If missing, log a critical warning but do not crash (fail gracefully by skipping audio extraction).
* **Execution:**
1. Generate UUID for temporary `.wav`.
2. `subprocess.run(["ffmpeg", "-i", input_path, "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", tmp_wav])`
3. `subprocess.run(["./whisper.cpp/main", "-m", "./whisper.cpp/models/ggml-base.en.bin", "-f", tmp_wav, "-nt"], capture_output=True, text=True)`
4. Cleanup temporary WAV files via a `finally` block to prevent disk space leaks.



### 7.3 Google GenAI Vision/LLM Integration (`services/vision_llm.py`)

* **Initialization:** `from google import genai; client = genai.Client(api_key=settings.GEMINI_API_KEY)`
* **Prompt Construction:** Map input strictly to a template. Do not include raw media paths; pass the `PIL.Image` directly to the `contents` array.
* **Structured Output Constraint:** Use `genai.types.GenerateContentConfig`:
```python
from pydantic import BaseModel, Field
class RoutingDecision(BaseModel):
    reasoning: str = Field(description="Step-by-step reasoning")
    decision: str = Field(description="Must be exactly: notify, digest, or mute")

response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents=[prompt_text, PIL.Image.open(image_path)],
    config=genai.types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=RoutingDecision,
        temperature=0.1
    )
)

```


* **Error Handling:** If API throws a `ResourceExhausted` error, implement an exponential backoff retry mechanism (max 3 retries). If it fails on validation, default fallback is `digest` to prevent message loss.

---

## 8. Frontend UI/UX Requirements (Dashboard)

### 8.1 Overview & Global Layout

* **Theme:** Light/Dark mode toggle. Default to Dark Mode.
* **Colors:** Slate-900 backgrounds, Tailwind standard success (Green-500 for `notify`), warning (Yellow-500 for `digest`), and destructive (Red-500 for `mute`).
* **Navigation:** Left vertical sidebar (collapsible on mobile). Links: "Dashboard Overview", "Message Logs", "Evaluation Benchmark".

### 8.2 Page: Dashboard Overview (`/`)

* **Purpose:** High-level metrics visualization.
* **Layout:** Top row of three KPI cards (Total Processed, Overall Accuracy, Avg Processing Time).
* **Component:** A Recharts bar chart showing the distribution of routing decisions over the last 7 days.
* **Interaction:** Hovering over bars shows exact counts via a Tooltip.

### 8.3 Page: Message Logs (`/logs`)

* **Purpose:** Audit trail of every processed message.
* **Layout:** A data table (using TanStack Table).
* **Columns:** Time, Sender, Media Icons (Mic icon if audio present, Image icon if image present), Decision Badge, Processing Time.
* **Interaction:** Clicking a row opens a right-side Slide-Over (Sheet component).
* **Slide-Over Content:**
* Original Text.
* Extracted Audio Transcript (displayed in a distinct quotation block).
* Rendered Image (if `image_path` exists, serve via a static file route `GET /media/{filename}`).
* The LLM's full `reasoning` string formatted in a gray code-like block.



### 8.4 Error & Loading States

* **Loading:** Use skeleton loaders mimicking the row structure for tables. Button clicks trigger a spinning icon inside the button and disable the button to prevent duplicate submissions.
* **Empty States:** If no logs exist, show an illustration (SVG) with text "No messages processed yet." and a button "Run Evaluation Pipeline".
* **Errors:** Network errors trigger a Toast Notification (shadcn toaster) on the bottom right: "Failed to connect to backend. Please check server status."

---

## 9. Evaluation Workflow & Metrics Calculation

### 9.1 Purpose

To prove the model's reliability during the hackathon judging, the system must evaluate its predictions against expected outputs.

### 9.2 Metrics Logic (`services/metrics.py`)

* Join the `messages` table with the `evaluations` table on `message_id`.
* Calculate:
* **True Positives (TP), False Positives (FP), False Negatives (FN)** per class.
* **Precision:** $TP / (TP + FP)$
* **Recall:** $TP / (TP + FN)$
* **F1-Score:** $2 \times \frac{Precision \times Recall}{Precision + Recall}$


* **Critical Requirement:** Output the False Positive Rate for `notify` specifically, as incorrect interruptions degrade user experience heavily.

---

## 10. Deployment & Execution Workflow

### 10.1 Environment Variables (`.env`)

```env
GEMINI_API_KEY=your_google_api_key_here
API_BEARER_TOKEN=secure_random_string
DATABASE_URL=sqlite:///./messages.db
MEDIA_STORAGE_PATH=./dataset/media

```

### 10.2 CI/CD & Build Scripts

Create a `Makefile` in the root directory to automate the setup for the AI IDE and the evaluator:

```makefile
.PHONY: setup install-backend build-whisper start

setup: install-backend build-whisper

install-backend:
	cd backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt

build-whisper:
	git submodule update --init --recursive
	cd backend/whisper.cpp && make && bash ./models/download-ggml-model.sh base.en

start-backend:
	cd backend && source venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000

start-frontend:
	cd frontend && npm install && npm run dev

```

---

## 11. Edge Cases & Mitigation Strategies

1. **Audio format is not supported by FFmpeg:**
* *Mitigation:* Try/catch the subprocess run. On failure, pass an empty transcript to the LLM and rely purely on text metadata. Log warning.


2. **LLM Hallucinates a 4th Category:**
* *Mitigation:* Pydantic structural validation ensures the response crashes immediately if the category is not `notify`, `digest`, or `mute`. The FastAPI exception handler will catch the validation error, trigger an automatic retry via `vision_llm.py`, and default to `digest` on max retries.


3. **Huge Image Payloads (>5MB):**
* *Mitigation:* Python's `PIL` should downscale the image to a maximum dimension of 1024x1024 before passing it to `google-genai` to save latency and bandwidth.


4. **Empty Messages:**
* *Mitigation:* A message with no text, audio, or image should instantly be routed to `mute` by the Fast Path engine to prevent wasting an API call.



---

## 12. Coding Standards & Naming Conventions

* **Python:** Follow PEP 8. Use `snake_case` for variables and functions. Use `PascalCase` for classes and Pydantic models. Use strict type hinting (`-> str`, `| None`).
* **React/TypeScript:** Use `PascalCase` for components. Use `camelCase` for variables. Define strict Types/Interfaces for all API responses.
* **Git:** Use semantic commit messages (e.g., `feat(api): implement whisper integration`, `fix(ui): correct tooltip z-index`).
* **Logging:** Avoid standard `print()`. Use Python's `logging` module configured at the `INFO` level. Output logs to standard out (stdout) and append to `log.txt` to satisfy the hackathon submission requirements.