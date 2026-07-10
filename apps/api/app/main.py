from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.questions import router as questions_router
from app.core.config import settings

app = FastAPI(title="AWS Quiz Bank API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(questions_router, prefix="/api")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
