# NEON Agent Challenge Solution

## Key Design Decision
A local LLM (Ollama) was initially explored for resume-based responses.  
However, due to strict latency, formatting, and reliability constraints in the NEON protocol, the final system uses deterministic logic.

This decision ensures:
- Consistent low-latency responses
- Strict adherence to protocol formats
- Higher reliability under real-time conditions

---

## Overview
This project implements an AI co-pilot that communicates with the NEON system over WebSockets and completes a multi-step authentication protocol. The agent reconstructs fragmented transmissions, adheres to strict response formats, and operates under tight timing constraints.

---

## Key Features
- Fragment reconstruction using timestamp-based ordering  
- Deterministic math evaluation with safe expression parsing  
- Wikipedia API integration for knowledge-based queries  
- Resume-aware responses with strict character constraints  
- Stateful memory tracking for final verification checkpoint  
- Robust handling of noisy and inconsistent inputs  
- Dockerized for isolated and reproducible execution  

---

## Tech Stack
- Python  
- asyncio  
- websockets  
- requests  
- Docker  

---

## Architecture & Approach
The agent is designed with a reliability-first mindset:

- Uses deterministic logic instead of relying on slow or unpredictable LLM responses  
- Parses and routes incoming messages based on protocol patterns  
- Handles edge cases such as malformed fragments, timing issues, and API failures  
- Maintains internal state to support memory-based verification  

This ensures fast, predictable, and correct behavior under strict protocol constraints.

---

## Security Considerations
- The NEON authorization code is not hardcoded in the repository  
- It is injected at runtime using environment variables  
- This prevents accidental exposure of credentials in version control  

Example:

```bash
docker run --rm --network neon-net -e NEON_CODE=<your_code> neon-agent
