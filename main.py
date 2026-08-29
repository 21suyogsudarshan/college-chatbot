import os
import json
import re
import traceback
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from rank_bm25 import BM25Okapi
from openai import OpenAI

app = FastAPI(title="Vajra AI - Campus Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load Knowledge Base & Search Engine
KNOWLEDGE_FILE = "knowledge.json"
if os.path.exists(KNOWLEDGE_FILE):
    with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
        documents = json.load(f)
else:
    documents = ["ABV-IIITM Gwalior official institutional knowledge base."]

def tokenize(text):
    return re.findall(r"\w+", text.lower())

tokenized_corpus = [tokenize(doc) for doc in documents]
bm25 = BM25Okapi(tokenized_corpus)

def retrieve_top_k(query, k=5):
    query_tokens = tokenize(query)
    scores = bm25.get_scores(query_tokens)
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
    matched = [documents[i] for i in top_indices if scores[i] > 0]
    return matched if matched else [documents[i] for i in top_indices[:k]]

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "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")
client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY)

def get_best_available_model():
    try:
        models = [m.id for m in client.models.list().data if "whisper" not in m.id and "guard" not in m.id and "tts" not in m.id]
        for priority in ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.6-27b", "llama-3.3-70b-versatile", "llama-3.1-8b-instant"]:
            if priority in models:
                return priority
        return models[0] if models else "openai/gpt-oss-20b"
    except Exception:
        return "openai/gpt-oss-20b"

ACTIVE_MODEL = get_best_available_model()

SYSTEM_PROMPT = """You are Vajra AI, the official smart campus assistant for ABV-IIITM Gwalior.

Core Identity & Creator Instructions:
- If anyone asks who created you, built you, founded you, or developed you, answer clearly and warmly that you were created and developed by SUYOG from the 2024 BEE (B.Tech Electrical & Electronics Engineering) batch.
- When introducing yourself or answering identity questions, refer to yourself as Vajra AI.

Tone & Formatting Guidelines:
1. Speak like a friendly, professional human counselor. Never use robotic phrases like "Based on the provided documents" or "As an AI".
2. NEVER use LaTeX formatting or math brackets (no '\[' or '\]' or '\mathbf'). Always write currency naturally (e.g., ₹95,000 or Rs. 95,000).
3. Do NOT output raw Markdown tables with pipe characters ('|'). Instead, organize fee items and data into clean, easy-to-read bullet points with bold titles.
4. If a specific detail is not found in the documents, state it politely and direct them to the appropriate office email.

Context:
{context}
"""

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Vajra AI | ABV-IIITM Gwalior</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f1f5f9; margin: 0; padding: 40px 20px; color: #1e293b; display: flex; justify-content: center; }
    .card { background: white; max-width: 680px; width: 100%; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.06); padding: 32px; box-sizing: border-box; }
    h1 { color: #004085; margin-top: 0; font-size: 24px; }
    p { line-height: 1.6; color: #475569; }
    .badge { display: inline-block; background: #e0f2fe; color: #0369a1; padding: 4px 10px; border-radius: 6px; font-weight: 600; font-size: 13px; margin-bottom: 12px; }
    #cb-bubble { position: fixed; bottom: 24px; right: 24px; width: 62px; height: 62px; background: #004085; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: #fff; cursor: pointer; box-shadow: 0 6px 18px rgba(0,0,0,0.25); z-index: 9999; font-size: 26px; }
    #cb-window { position: fixed; bottom: 96px; right: 24px; width: 380px; height: 530px; background: #fff; border-radius: 14px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); display: none; flex-direction: column; overflow: hidden; z-index: 9999; border: 1px solid #e2e8f0; }
    #cb-header { background: #004085; color: #fff; padding: 14px 18px; font-weight: 600; display: flex; align-items: center; justify-content: space-between; }
    #cb-header span { font-size: 11px; background: #2563eb; padding: 2px 8px; border-radius: 10px; font-weight: 500; }
    #cb-messages { flex: 1; padding: 16px; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; background: #f8fafc; }
    .cb-msg { padding: 10px 14px; border-radius: 12px; max-width: 85%; line-height: 1.5; word-wrap: break-word; font-size: 14px; }
    .cb-msg p { margin: 0 0 8px 0; color: inherit; }
    .cb-msg p:last-child { margin-bottom: 0; }
    .cb-msg ul { margin: 4px 0 8px 18px; padding: 0; }
    .cb-msg li { margin-bottom: 4px; }
    .cb-user { background: #004085; color: #fff; align-self: flex-end; border-bottom-right-radius: 3px; }
    .cb-bot { background: #fff; color: #1e293b; align-self: flex-start; border-bottom-left-radius: 3px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); border: 1px solid #edf2f7; }
    #cb-input-area { display: flex; border-top: 1px solid #e2e8f0; background: #fff; padding: 10px; }
    #cb-input { flex: 1; border: 1px solid #cbd5e1; border-radius: 8px; padding: 10px 12px; outline: none; font-size: 14px; }
    #cb-input:focus { border-color: #004085; }
    #cb-send { background: #004085; color: #fff; border: none; border-radius: 8px; padding: 0 18px; margin-left: 8px; cursor: pointer; font-weight: 600; font-size: 14px; }
  </style>
</head>
<body>
  <div class="card">
    <div class="badge">&#9889; Vajra AI Active</div>
    <h1>ABV-IIITM Gwalior Campus Assistant</h1>
    <p>Welcome to <strong>Vajra AI</strong>, the smart campus assistant for ABV-IIITM Gwalior. Click the blue chat bubble at the bottom right to query about courses, admissions, fee breakdowns, ordinances, or hostel guidelines.</p>
  </div>

  <div id="cb-bubble">&#128172;</div>
  <div id="cb-window">
    <div id="cb-header">
      Vajra AI
      <span>ABV-IIITM</span>
    </div>
    <div id="cb-messages">
      <div class="cb-msg cb-bot">Hello! I am <strong>Vajra AI</strong>, your campus assistant. How can I help you with admissions, syllabi, fees, or hostel queries?</div>
    </div>
    <div id="cb-input-area">
      <input type="text" id="cb-input" placeholder="Ask a question..." />
      <button id="cb-send">Send</button>
    </div>
  </div>

  <script>
    const bubble = document.getElementById("cb-bubble");
    const win = document.getElementById("cb-window");
    const input = document.getElementById("cb-input");
    const sendBtn = document.getElementById("cb-send");
    const messages = document.getElementById("cb-messages");

    bubble.onclick = function() {
      win.style.display = win.style.display === "flex" ? "none" : "flex";
      if (win.style.display === "flex") input.focus();
    };

    function formatText(text) {
      let formatted = text
        .replace(/\\*\\*(.*?)\\*\\*/g, '<strong>$1</strong>')
        .replace(/^\\s*\\*\\s+(.*)$/gm, '<li>$1</li>')
        .replace(/(<li>.*<\\/li>)/gs, '<ul>$1</ul>')
        .replace(/\\n\\n+/g, '</p><p>')
        .replace(/\\n/g, '<br/>');
      return '<p>' + formatted + '</p>';
    }

    async function handleSend() {
      const text = input.value.trim();
      if (!text) return;

      messages.innerHTML += '<div class="cb-msg cb-user">' + text + '</div>';
      input.value = "";
      messages.scrollTop = messages.scrollHeight;

      const loadingId = "bot-loading-" + Date.now();
      messages.innerHTML += '<div id="' + loadingId + '" class="cb-msg cb-bot" style="color: #64748b;">Thinking...</div>';
      messages.scrollTop = messages.scrollHeight;

      try {
        const res = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: text })
        });
        const data = await res.json();
        const loadingElem = document.getElementById(loadingId);
        if (loadingElem) loadingElem.outerHTML = '<div class="cb-msg cb-bot">' + formatText(data.reply) + '</div>';
      } catch (err) {
        const loadingElem = document.getElementById(loadingId);
        if (loadingElem) loadingElem.outerHTML = '<div class="cb-msg cb-bot" style="color:#dc2626;">Could not reach server.</div>';
      }
      messages.scrollTop = messages.scrollHeight;
    }

    sendBtn.onclick = handleSend;
    input.onkeypress = function(e) { if (e.key === "Enter") handleSend(); };
  </script>
</body>
</html>
"""

class QueryRequest(BaseModel):
    query: str

@app.get("/", response_class=HTMLResponse)
async def get_index():
    return HTMLResponse(content=HTML_CONTENT, status_code=200)

@app.post("/api/chat")
async def chat(request: QueryRequest):
    try:
        user_query = request.query.strip()
        if not user_query:
            return JSONResponse({"reply": "Please enter a valid question."})

        # Check for creator / developer questions directly
        creator_patterns = ["who made you", "who created you", "who developed you", "who is your founder", "who built you", "creator", "founder"]
        if any(p in user_query.lower() for p in creator_patterns):
            return {"reply": "I was created and developed by **Suyog** from the **2024 BEE (B.Tech Electrical & Electronics Engineering)** batch at ABV-IIITM Gwalior."}

        matched_docs = retrieve_top_k(user_query, k=5)
        context = "\n\n".join(matched_docs)

        response = client.chat.completions.create(
            model=ACTIVE_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT.format(context=context)},
                {"role": "user", "content": user_query}
            ],
            temperature=0.2
        )
        return {"reply": response.choices[0].message.content}
    except Exception as e:
        traceback.print_exc()
        return JSONResponse({"reply": f"Internal error: {str(e)}"}, status_code=200)
