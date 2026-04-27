import asyncio
import websockets
import json
import re
import math
import requests
import os


URL = "wss://neonhealth.software/agent-puzzle/challenge"
#NEON_CODE = ""
NEON_CODE = os.getenv("NEON_CODE")

SENT_SPEAK_TEXTS = []


RESUME_DATA = {
    "education": (
        "Adithya earned an MS in Computer Science and Engineering from UC Riverside "
        "and a B.Tech in Electronics and Communication Engineering from JNTU."
    ),
    "skills": (
        "Adithya is skilled in Python, Node.js, FastAPI, AWS, GCP, Docker, Kubernetes, "
        "SQL, RAG, FAISS, ChromaDB, CI/CD, AI agents, and scalable backend systems."
    ),
    "experience": (
        "Adithya has 4+ years of experience building backend systems, AI and LLM pipelines, "
        "microservices, automation workflows, Oracle HCM integrations, and scalable cloud services."
    ),
    "projects": (
        "Adithya built RAG pipelines, AI video generation workflows, Chrome extensions, "
        "ML prediction models, and an IEEE-published XOR CAM design."
    ),
}


def reconstruct_message(data):
    fragments = data.get("message", [])

    if not isinstance(fragments, list):
        return ""

    sorted_fragments = sorted(
        fragments,
        key=lambda x: x.get("timestamp", 0)
    )

    return " ".join(str(f.get("word", "")) for f in sorted_fragments).strip()


def extract_length_limits(text):
    text_l = text.lower()

    match = re.search(r"between\s+(\d+)\s+and\s+(\d+).*?characters", text_l)
    if match:
        return int(match.group(1)), int(match.group(2))

    match = re.search(r"exactly\s+(\d+).*?characters", text_l)
    if match:
        n = int(match.group(1))
        return n, n

    return 0, 256


def fit_length(text, min_len=0, max_len=256):
    text = " ".join(str(text).split())

    if max_len <= 0:
        return ""

    if len(text) > max_len:
        text = text[:max_len].rsplit(" ", 1)[0]
        if not text:
            text = str(text)[:max_len]

    while len(text) < min_len:
        text += "."

    return text[:max_len]


def smart_resume_answer(question):
    q = question.lower()

    if "education" in q:
        return RESUME_DATA["education"]

    if "skill" in q:
        return RESUME_DATA["skills"]

    if "project" in q:
        return RESUME_DATA["projects"]

    if "work experience" in q or "experience" in q:
        return RESUME_DATA["experience"]

    return RESUME_DATA["experience"]


def generate_resume_answer(question):
    min_len, max_len = extract_length_limits(question)
    answer = smart_resume_answer(question)
    return fit_length(answer, min_len, max_len)


def solve_math(text):
    """
    Handles expressions like:
    Math.floor((46173 + 49799 + 18231) * 774 / 96) % 1084
    """
    expr_match = re.search(r":\s*(.+)$", text)
    if not expr_match:
        return None

    expr = expr_match.group(1).strip()
    expr = expr.replace("Math.floor", "math.floor")

    # Security: allow only safe math characters/functions
    if not re.fullmatch(r"[0-9+\-*/%().,\s_mathfloor]+", expr):
        print("Unsafe expression blocked:", expr)
        return None

    try:
        result = eval(
            expr,
            {"__builtins__": {}},
            {"math": math}
        )
        return str(int(result))
    except Exception as e:
        print("Math error:", e)
        return None


def wiki_summary_word(text):
    title_match = re.search(r"'([^']+)'", text)
    if not title_match:
        title_match = re.search(r"for\s+([A-Za-z0-9_() -]+)", text, re.I)

    pos_match = re.search(r"(\d+)(?:st|nd|rd|th)\s+word", text, re.I)

    if not title_match or not pos_match:
        print("Wiki parse failed:", text)
        return None

    title = title_match.group(1).strip()
    pos = int(pos_match.group(1)) - 1

    try:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}"

        headers = {
            "User-Agent": "neon-agent/1.0 (contact: test@example.com)"
        }

        res = requests.get(url, headers=headers, timeout=8)

        if res.status_code != 200:
            print("Wiki API failed:", res.status_code)
            return None

        data = res.json()
        summary = data.get("extract", "")

        words = re.findall(r"\b[\w'-]+\b", summary)

        print(f"Wiki words count: {len(words)} | Requested index: {pos}")

        if 0 <= pos < len(words):
            return words[pos]

    except Exception as e:
        print("Wiki error:", e)

    return None


def recall_previous_word(text):
    pos_match = re.search(r"(\d+)(?:st|nd|rd|th)\s+word", text, re.I)

    if not pos_match or not SENT_SPEAK_TEXTS:
        return None

    pos = int(pos_match.group(1)) - 1

    # Prefer the most recent spoken answer
    for previous_text in reversed(SENT_SPEAK_TEXTS):
        words = re.findall(r"\b[\w'-]+\b", previous_text)
        if 0 <= pos < len(words):
            return words[pos]

    return None


def build_response(text):
    text_l = text.lower()

    # Frequency checkpoint
    match = re.search(
        r"excellent software engineer,\s*respond on frequency\s+(\d+)",
        text,
        re.I
    )
    if match:
        return {
            "type": "enter_digits",
            "digits": match.group(1)
        }

    # Vessel code checkpoint
    if "vessel authorization code" in text_l:
        digits = NEON_CODE
        if "pound key" in text_l:
            digits += "#"

        return {
            "type": "enter_digits",
            "digits": digits
        }

    # Math checkpoint
    if "math.floor" in text_l or "calculate" in text_l or "determine" in text_l:
        digits = solve_math(text)

        if digits is None:
            digits = "0"

        if "pound key" in text_l and not digits.endswith("#"):
            digits += "#"

        return {
            "type": "enter_digits",
            "digits": digits
        }

    # Wikipedia / Knowledge Archive checkpoint
    if any(k in text_l for k in ["knowledge archive", "wikipedia", "entry summary", "entry for"]):
        answer = wiki_summary_word(text) or "unknown"

        return {
            "type": "speak_text",
            "text": fit_length(answer, *extract_length_limits(text))
        }

    # Memory checkpoint
    if any(k in text_l for k in ["recall", "previous", "earlier", "transmission verification"]):
        answer = recall_previous_word(text) or "unknown"

        return {
            "type": "speak_text",
            "text": fit_length(answer, *extract_length_limits(text))
        }

    # Resume checkpoint
    if any(k in text_l for k in [
        "resume",
        "crew",
        "manifest",
        "experience",
        "skills",
        "projects",
        "education"
    ]):
        return {
            "type": "speak_text",
            "text": generate_resume_answer(text)
        }

    # Safe default
    return {
        "type": "speak_text",
        "text": "acknowledged"
    }


async def run():
    async with websockets.connect(URL) as ws:
        print("Connected to NEON")

        while True:
            try:
                msg = await ws.recv()
            except websockets.exceptions.ConnectionClosed:
                print("Connection closed by NEON")
                break

            print("RAW:", msg)

            try:
                data = json.loads(msg)
            except json.JSONDecodeError:
                print("Invalid JSON received")
                continue

            if data.get("type") == "error":
                print("ERROR:", data.get("message"))
                continue

            if data.get("type") == "success":
                print("SUCCESS:", data)
                break

            text = reconstruct_message(data)
            print("RECONSTRUCTED:", text)

            response = build_response(text)

            # Store spoken responses for memory checkpoint
            if response["type"] == "speak_text":
                SENT_SPEAK_TEXTS.append(response["text"])

            print("SENDING:", response)
            await ws.send(json.dumps(response))


asyncio.run(run())
