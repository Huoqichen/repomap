from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class AnalyzeRequest(BaseModel):
    repo_url: HttpUrl = Field(description="GitHub repository URL to analyze.")
    branch: str | None = Field(default=None, description="Optional branch name.")


class GraphStats(BaseModel):
    nodes: int
    edges: int
    layers: int


class AnalyzeResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    architecture_map: dict
    mermaid: str
    stats: GraphStats
