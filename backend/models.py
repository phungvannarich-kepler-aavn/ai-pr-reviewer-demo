"""
Pydantic models for the AI PR Reviewer API.
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl


class ReviewDecision(str, Enum):
    """Enum for PR review decisions."""
    APPROVE = "APPROVE"
    REQUEST_CHANGES = "REQUEST_CHANGES"


class FileComment(BaseModel):
    """A single comment on a specific file and line."""
    file: str = Field(..., description="The file path being commented on")
    line: int = Field(..., ge=1, description="The line number of the issue")
    issue: str = Field(..., description="Description of the issue found")
    suggestion: str = Field(..., description="Suggested fix or improvement")


class ReviewResponse(BaseModel):
    """The structured response from the LLM review."""
    summary: str = Field(..., description="High-level summary of the PR review")
    comments: List[FileComment] = Field(
        default_factory=list,
        description="List of file-level comments"
    )
    decision: ReviewDecision = Field(
        ...,
        description="Final review decision: APPROVE or REQUEST_CHANGES"
    )


class ReviewRequest(BaseModel):
    """Request body for the /review endpoint."""
    pr_url: str = Field(
        ...,
        description="GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)",
        examples=["https://github.com/facebook/react/pull/1"]
    )


class APIStatusResponse(BaseModel):
    """Response for API health check."""
    status: str = Field(default="ok")
    version: str = Field(default="1.0.0")
    github_configured: bool = Field(
        ...,
        description="Whether GitHub token is configured"
    )
    openrouter_configured: bool = Field(
        ...,
        description="Whether OpenRouter API key is configured"
    )
    llm_model: str = Field(
        ...,
        description="The configured LLM model"
    )


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Additional error details")
