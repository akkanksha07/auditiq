# AuditIQ — forensic audit intelligence platform
#   Build:  docker build -t auditiq .
#   Run:    docker run -p 8501:8501 -e ANTHROPIC_API_KEY=sk-ant-... auditiq
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHERUSAGESTATS=false

WORKDIR /app

# Install dependencies first for better layer caching.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application.
COPY . .

EXPOSE 8501

# Use Streamlit's own health endpoint.
HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
