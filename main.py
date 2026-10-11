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

# Load Knowledge Base
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

def get_specific_iiitm_link(query):
    q = query.lower().strip()
    
    # 1. Faculty Member Detection (e.g., Dr. Manoj Singh Parihar)
    faculty_match = re.search(r"(dr\.|prof\.|professor|dr)?\s*([a-z\s]+)", q)
    if any(name in q for name in ["parihar", "manoj singh parihar", "manoj parihar"]):
        return "http://www.iiitm.ac.in/staff/faculty/dr-manoj-singh-parihar"
    elif "sri niwas singh" in q or "sn singh" in q or "director" in q:
        return "https://iiitm.ac.in/whos-who"
    elif "faculty" in q or "professor" in q or "staff" in q or "teacher" in q or "hod" in q:
        return "https://iiitm.ac.in/staff"

    # 2. Specific Departments & Courses
    if "eee" in q or "electrical" in q:
        return "https://www.iiitm.ac.in/departments/electrical-electronics-engineering"
    elif "cse" in q or "computer science" in q:
        return "https://www.iiitm.ac.in/course/b-tech-in-computer-science-engineering"
    elif "management" in q or "mba" in q:
        return "https://www.iiitm.ac.in/departments/management-studies"
    elif "mtech" in q or "m.tech" in q:
        return "https://www.iiitm.ac.in/course/m-tech"
    elif "phd" in q or "ph.d" in q:
        return "https://www.iiitm.ac.in/index.php/admissions/archive"
    elif "btech" in q or "b.tech" in q or "jee" in q:
        return "https://www.iiitm.ac.in/course/b-tech-in-computer-science-engineering"

    # 3. Fees & Financials
    elif "fee" in q or "cost" in q or "tuition" in q or "scholarship" in q:
        return "https://www.iiitm.ac.in/index.php/academics/fee-structure"

    # 4. Hostel & Mess
    elif "hostel" in q or "mess" in q or "room" in q or "curfew" in q:
        return "https://www.iiitm.ac.in/index.php/facilities/hostel"

    # 5. Placements & Career
    elif "placement" in q or "package" in q or "ctc" in q or "company" in q or "recruiter" in q:
        return "https://www.iiitm.ac.in/index.php/placements/overview"

    # Default Official College Portal
    return "https://www.iiitm.ac.in/"

SYSTEM_PROMPT = """You are Vajra AI, the official campus assistant for ABV-IIITM Gwalior.

CRITICAL INSTRUCTIONS FROM DIRECTOR:
1. ALWAYS GIVE BRIEF & CONCISE ANSWERS: Never write long paragraphs. Present answers strictly in 2 to 3 short bullet points.
2. CREATOR ATTRIBUTION: If asked who created/built/founded you, state clearly that you were developed by **SUYOG** from the **2024 BEE (B.Tech Electrical & Electronics Engineering)** batch.
3. MANDATORY LINK ENDING: Every single response MUST conclude with this exact text on a new line:
   "For more info check out this link: {specific_link}"

Context:
{context}
"""

class QueryRequest(BaseModel):
    query: str

@app.post("/api/chat")
async def chat(request: QueryRequest):
    try:
        user_query = request.query.strip()
        if not user_query:
            return JSONResponse({"reply": "Please enter a valid question."})

        # Ambiguous admission inquiry disambiguation
        q_lower = user_query.lower()
        if q_lower in ["admission", "admissions", "admission?", "admissions?"]:
            return {
                "reply": "Which academic program admission are you inquiring about?\n\n• **B.Tech / Integrated B.Tech**\n• **M.Tech**\n• **MBA**\n• **Ph.D.**\n\nFor more info check out this link: https://www.iiitm.ac.in/index.php/admissions/archive"
            }

        # Creator attribution check
        if any(p in q_lower for p in ["who made you", "who created you", "who developed you", "who is your founder", "who built you", "built vajra"]):
            return {
                "reply": "• I was created and developed by **SUYOG** from the **2024 BEE (B.Tech Electrical & Electronics Engineering)** batch at ABV-IIITM Gwalior.\n\nFor more info check out this link: https://www.iiitm.ac.in/"
            }

        specific_link = get_specific_iiitm_link(user_query)
        matched_docs = retrieve_top_k(user_query, k=5)
        context = "\n\n".join(matched_docs)

        response = client.chat.completions.create(
            model=ACTIVE_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT.format(context=context, specific_link=specific_link)},
                {"role": "user", "content": user_query}
            ],
            temperature=0.1
        )
        return {"reply": response.choices[0].message.content}
    except Exception as e:
        traceback.print_exc()
        return JSONResponse({"reply": f"Internal error: {str(e)}"}, status_code=200)