# Orchestrate: AI WhatsApp Notification Router

An AI-powered system for WhatsApp that intelligently decides which messages deserve immediate attention, which should wait, and which should be muted. It acts as a smart filter between the noisy WhatsApp stream and the user's notification tray.

## Architecture

```text
Incoming Message
       │
       ▼
┌──────────────────┐
│ Context Builder  │ (Merges historical data, user preferences, business status)
└────────┬─────────┘
         ▼
┌──────────────────┐
│ Fast Path Router │ ──(Deterministic Rule Match)──► Action (Notify/Digest/Mute)
└────────┬─────────┘
         │ (No match)
         ▼
┌──────────────────┐
│ Audio Extraction │ ──(Whisper local/fallback for voice notes)
└────────┬─────────┘
         ▼
┌──────────────────┐
│   Deep Router    │ ──(GPT-4o-mini multimodal reasoning)
└────────┬─────────┘
         ▼
┌──────────────────┐
│ Evidence Scorer  │ ──(Weighted retrieval of past reactions & messages)
└────────┬─────────┘
         ▼
       Action
```

## Hybrid Routing Approach
- **Fast Path:** Deterministic heuristic rules handle obvious cases instantly (e.g. scams, opted-out promotions, muted groups, direct mentions) with high confidence. It leverages personalized DND windows and historical dismissal rates.
- **Deep Path:** Complex reasoning and multimodal inputs (images, transcribed voice notes) fall back to a structured output LLM (GPT-4o-mini).
- **Evidence Scorer:** A weighted evidence retrieval engine considers jaccard similarity, sender matching, media types, and past user reactions (mutes/dismissals/opens) to surface the most relevant historical context.

## Performance Benchmarks

- **Accuracy**: 93.3%
- **Macro F1**: 93.5%
- **Notify FPR**: 4.8%
- **Avg Latency**: ~1307ms

## How to Run

### 1. Setup Environment
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Set OpenAI Key
Create a `.env` file in the `backend/` directory:
```
OPENAI_API_KEY="your-api-key"
```

### 3. Run Backend & Frontend
Start both the API and the React dashboard:
```bash
make start
```
- API: `http://localhost:8000`
- Dashboard: `http://localhost:5173`

### 4. Run Local Evaluation
Run the local evaluation script to validate the rules against the dataset:
```bash
cd backend
source venv/bin/activate
python ../scripts/run_eval_local.py
```
