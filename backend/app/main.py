from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Pressella Pitch Guardrail")


class HealthResponse(BaseModel):
    status: str


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok")
