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

RESUME_TEXT = """
Summary
Software Engineer with 4 plus years of experience building scalable backend systems, AI and LLM pipelines, and production applications. Strong in Python, Node.js, and cloud platforms. Experienced in distributed systems, API design, automation, and CI CD. Delivers reliable systems in fast paced environments with full ownership from design to deployment. Focused on AI driven applications, workflow automation, and scalable architecture.

Skills
Programming languages include Python, C, PL SQL, JavaScript, CUDA C, C sharp, HTML, CSS, Bash.
Core computer science includes data structures, algorithms, object oriented programming, operating systems, computer networks, database management systems, system design, and problem solving.
AI and ML includes machine learning, natural language processing, retrieval augmented generation, and AI agents.
Frameworks and libraries include Flask, FastAPI, Selenium, Node.js, React.js, ASP.NET, and WPF basics.
Cloud and architecture includes AWS, GCP, OCI, monolithic systems, microservices, and distributed systems.
DevOps and CI CD includes Docker, Kubernetes, Git, GitHub, GitHub Actions, and CI CD pipelines.
Databases and tools include MongoDB, SQL, Oracle Database, DynamoDB, PostgreSQL, MATLAB, LabVIEW, Cadence, Proteus, Arduino, and Visual Studio.

Work Experience
Software Engineer at M9Market, Remote USA from January 2025 to present.
Own backend microservices using Python, Node.js, and AWS with focus on modular and reliable systems.
Built and integrated AI and LLM workflows in production including model selection, script generation, and automated video creation.
Implemented FastAPI, Docker, and GitHub Actions to improve development speed and deployment efficiency.
Designed and deployed CI CD pipelines to reduce release time and ensure stable deployments.
Worked with founders and cross functional teams to deliver production features under tight timelines.
Optimized APIs, data pipelines, and integrations for scalable AI driven applications.

Software and IT Support Student Assistant at University of California Riverside from March 2024 to March 2025.
Automated internal IT workflows using Python and Bash scripts.
Supported systems across Windows, macOS, and Linux environments.
Maintained infrastructure and improved internal processes through scripting.

Systems Software Engineer at Tata Consultancy Services in Hyderabad, India from January 2021 to July 2023.
Automated HR workflows using Python scripts and reduced manual effort by 40 percent.
Optimized SQL queries in Oracle HCM systems to reduce latency and improve reporting performance.
Integrated REST APIs for data exchange between Oracle HCM and external systems.
Performed performance tuning for high traffic modules to improve responsiveness.
Delivered production solutions in collaboration with cross functional teams and rapidly learned Oracle HCM domain.

Projects
Server side CRUD application using C sharp, .NET, WPF, Flask API, and SQLite. Built a client server system with API integration and used AI tools to accelerate development and debugging.
Retrieval augmented generation pipeline for document summarization and question answering using Python, Flask, ChromaDB, and FAISS. Designed for scalable document processing and retrieval.
YouTube timestamps jumper Chrome extension using JavaScript. Enabled bookmarking, jumping, and looping of video timestamps with persistent storage.
Full swing 8 by 8 XOR content addressable memory. Designed low power CAM in Cadence gpdk180 with optimized SRAM and achieved 20 nanosecond search delay.
SpaceX rocket landing prediction model using machine learning. Achieved 87 percent accuracy using scikit learn, feature engineering, and data analysis.

Education
Master of Science in Computer Science and Engineering from University of California Riverside with GPA 3.8 out of 4.0 from September 2023 to March 2025.
Bachelor of Technology in Electronics and Communication Engineering from JNTU Hyderabad with GPA 8.48 out of 10.0 from September 2016 to September 2020.

Certifications include IBM Data Science, Programming for Everybody, Python Data Structures, Using Python to Access Web Data, and Using Databases with Python.
"""

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