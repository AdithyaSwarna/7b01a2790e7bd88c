FROM python:3.10-slim

WORKDIR /app

COPY . .

RUN pip install websockets requests PyPDF2

CMD ["python", "neon_agent.py"]