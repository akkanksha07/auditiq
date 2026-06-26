# Deploying AuditIQ

AuditIQ is a Streamlit app — it needs a long-running server with WebSocket support. It runs
great on **Streamlit Community Cloud**, any **container host**, or a VM, but **not** on
static/serverless hosts (Vercel, Netlify, GitHub Pages, AWS Lambda).

> **Secrets:** set `ANTHROPIC_API_KEY` as a platform secret. Never commit `.env` or
> `.streamlit/secrets.toml` (both gitignored). AI features (PDF extraction, news, narrative
> summary) need the key; the deterministic engines and **demo mode** work without it.

---

## Option A — Streamlit Community Cloud (fastest, free)

1. Push this repo to GitHub.
2. Go to <https://share.streamlit.io> → **Create app** → pick this repo, branch `main`, main file `app.py`.
3. **Advanced settings** → Python version **3.12**.
4. **Secrets** → paste (TOML), per `.streamlit/secrets.toml.example`:
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-..."
   ```
   `app.py` bridges Streamlit secrets into environment variables automatically.
5. **Deploy.** Streamlit installs `requirements.txt` and serves `app.py`.

> ⚠️ Free apps get a **public URL** and sleep when idle (~1 GB RAM). For confidential
> financial PDFs, prefer a private deployment (Option B/C).

---

## Option B — Docker (any host, one command)

```bash
# Put your key in .env first:
echo 'ANTHROPIC_API_KEY=sk-ant-...' > .env

# One command — builds and runs:
docker compose up --build
# → open http://localhost:8501
```

Without compose:
```bash
docker build -t auditiq .
docker run -p 8501:8501 -e ANTHROPIC_API_KEY=sk-ant-... auditiq
```

---

## Option C — Managed container hosts (private, production)

The same image runs anywhere containers do. Enable **session affinity / sticky sessions**
(Streamlit uses WebSockets), allow **≥ 1 GB RAM**, and expose port **8501**.

- **Google Cloud Run** (scales to zero):
  ```bash
  gcloud run deploy auditiq --source . --region <region> \
    --port 8501 --session-affinity --min-instances 1 \
    --set-secrets ANTHROPIC_API_KEY=ANTHROPIC_API_KEY:latest
  # add --allow-unauthenticated only if you want it public
  ```
- **Fly.io:** `fly launch` → `fly secrets set ANTHROPIC_API_KEY=sk-ant-...` → `fly deploy`
- **Render:** New → **Web Service** → Docker runtime → add `ANTHROPIC_API_KEY` env var.

---

## Pre-deploy checklist
- [ ] `ANTHROPIC_API_KEY` set as a secret (not committed)
- [ ] Python **3.12** (Streamlit Cloud advanced settings, or the Docker base image)
- [ ] ≥ 1 GB RAM; port 8501; sticky sessions if scaling > 1 instance
- [ ] Confidential data → private host, not the public Streamlit Cloud URL
- [ ] `.venv/`, `.env`, `data/` contents are gitignored (already configured)
