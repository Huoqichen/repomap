from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from repomap_api.config import get_settings
from repomap_api.schemas import AnalyzeRequest, AnalyzeResponse
from repomap_api.service import analyze_remote_repository

settings = get_settings()
app = FastAPI(
    title="repomap API",
    description="Analyze a GitHub repository and return an interactive architecture graph model.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if "*" in settings.cors_origins else settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze(payload: AnalyzeRequest) -> AnalyzeResponse:
    repo_url = str(payload.repo_url)
    if "github.com/" not in repo_url:
        raise HTTPException(status_code=400, detail="Only GitHub repository URLs are supported.")

    try:
        return analyze_remote_repository(repo_url=repo_url, branch=payload.branch, clone_dir=settings.clone_dir)
    except FileExistsError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Analysis failed: {error}") from error
