import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from fastapi import FastAPI
from src.api.webhook import router as webhook_router

app = FastAPI(
    title="Agente Instagram",
    description="Webhook receiver for Instagram messages via Meta Graph API",
    version="1.0.0",
)

app.include_router(webhook_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
