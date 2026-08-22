from fastapi import FastAPI
from pydantic import BaseModel

from app.routes.drafts import router as drafts_router

app = FastAPI(title="Pressella Pitch Guardrail")
app.include_router(drafts_router)


class HealthResponse(BaseModel):
    status: str


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok")

