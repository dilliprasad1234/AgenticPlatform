FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app:/app/src

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY agents ./agents
COPY src ./src
COPY tools ./tools
COPY workflows ./workflows
COPY main.py .
COPY pyproject.toml .

CMD ["python", "main.py"]