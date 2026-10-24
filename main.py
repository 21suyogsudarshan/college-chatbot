import os
import json
import re
import traceback
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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

# Google Gemini Client via OpenAI Compatibility Layer
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = OpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=GEMINI_API_KEY
)

ACTIVE_MODEL = "gemini-1.5-flash"

def get_specific_iiitm_link(query):
    q = query.lower().strip()
    
    # 1. Faculty Mappings & Slug Generator
    if "pinku" in q or "ranjan" in q:
        return "https://iiitm.ac.in/staff/faculty/dr-pinku-ranjan"
    elif "parihar" in q or "manoj" in q:
        return "https://www.iiitm.ac.in/staff/faculty/dr-manoj-singh-parihar"
    elif "sri niwas" in q or "sn singh" in q or "director" in q:
        return "https://iiitm.ac.in/whos-who"

    prof_match = re.search(r"(?:dr\.|prof\.|professor)?\s*([a-z]+)\s+([a-z]+(?:\s+[a-z]+)?)", q)
    stop_words = ["what", "where", "when", "which", "about", "tell", "does", "have", "total", "cost", "fee", "rule"]
    if prof_match:
        words = prof_match.group(0).replace("dr.", "").replace("prof.", "").replace("professor", "").strip().split()
        if len(words) >= 1 and words[0] not in stop_words and ("dr" in q or "prof" in q or "sir" in q or "faculty" in q):
            slug = "-".join(words)
            return f"https://iiitm.ac.in/staff/faculty/dr-{slug}"

    if "faculty" in q or "professor" in q or "staff" in q or "teacher" in q or "hod" in q:
        return "https://iiitm.ac.in/staff"

    # 2. Departments & Academic Programs
    if "eee" in q or "electrical" in q or "electronics" in q:
        return "https://www.iiitm.ac.in/departments/electrical-electronics-engineering"
    elif "cse" in q or "computer science" in q or "it" in q or "information technology" in q:
        return "https://www.iiitm.ac.in/course/b-tech-in-computer-science-engineering"
    elif "management" in q or "mba" in q or "business" in q:
        return "https://www.iiitm.ac.in/departments/management-studies"
    elif "mtech" in q or "m.tech" in q or "gate" in q:
        return "https://www.iiitm.ac.in/course/m-tech"
    elif "phd" in q or "ph.d" in q or "research" in q or "doctorate" in q:
        return "https://www.iiitm.ac.in/index.php/admissions/archive"
    elif "btech" in q or "b.tech" in q or "jee" in q or "josaa" in q or "csab" in q:
        return "https://www.iiitm.ac.in/course/b-tech-in-computer-science-engineering"

    # 3. Fees & Financial Aid
    elif any(k in q for k in ["fee", "cost", "tuition", "scholarship", "financial aid", "waiver"]):
        return "https://www.iiitm.ac.in/index.php/academics/fee-structure"

    # 4. Facilities & Campus
    elif any(k in q for k in ["hostel", "mess", "room", "curfew", "accommodation", "canteen"]):
        return "https://www.iiitm.ac.in/index.php/facilities/hostel"
    elif "library" in q or "book" in q or "journal" in q:
        return "https://www.iiitm.ac.in/index.php/facilities/library"
    elif "sports" in q or "gym" in q or "ground" in q or "club" in q:
        return "https://www.iiitm.ac.in/index.php/facilities/sports"

    # 5. Placements
    elif any(k in q for k in ["placement", "package", "ctc", "company", "recruiter", "salary", "internship"]):
        return "https://www.iiitm.ac.in/index.php/placements/overview"

    # 6. Admissions General
    elif "admission" in q or "apply" in q or "cutoff" in q or "rank" in q:
        return "https://www.iiitm.ac.in/index.php/admissions/archive"

    return "https://www.iiitm.ac.in/"

SYSTEM_PROMPT = """You are Vajra AI, the official campus assistant for ABV-IIITM Gwalior.

DIRECTOR REQUIREMENTS:
1. ALWAYS GIVE BRIEF & CONCISE ANSWERS: Maximum 2 to 3 bullet points.
2. CREATOR ATTRIBUTION: If asked who created/built/founded you, state clearly that you were developed by **SUYOG** from the **2024 BEE (B.Tech Electrical & Electronics Engineering)** batch.
3. MANDATORY LINK ENDING: Every single response MUST conclude strictly with:
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

        q_lower = user_query.lower()

        if q_lower in ["admission", "admissions", "admission?", "admissions?"]:
            return {
                "reply": "Which academic program admission are you inquiring about?\n\n• **B.Tech / Integrated B.Tech**\n• **M.Tech**\n• **MBA**\n• **Ph.D.**\n\nFor more info check out this link: https://www.iiitm.ac.in/index.php/admissions/archive"
            }

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
