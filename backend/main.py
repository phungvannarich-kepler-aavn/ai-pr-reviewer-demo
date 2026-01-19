"""
FastAPI application for AI PR Reviewer Demo.
"""

from dotenv import load_dotenv
import os
import logging

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import httpx

from models import (
    ReviewRequest,
    ReviewResponse,
    APIStatusResponse,
    ErrorResponse
)
from logic import review_pull_request, get_config_status, logger

# Initialize FastAPI app
app = FastAPI(
    title="AI PR Reviewer API",
    description="API for AI-powered GitHub Pull Request code reviews",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS for Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for demo purposes
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_model=APIStatusResponse)
async def root():
    """
    Root endpoint - returns API status and configuration.
    """
    logger.info("Health check / root endpoint access")
    config = get_config_status()
    return APIStatusResponse(
        status="ok",
        version="1.0.0",
        github_configured=config["github_configured"],
        openrouter_configured=config["openrouter_configured"],
        llm_model=config["llm_model"]
    )


@app.get("/health", response_model=APIStatusResponse)
async def health_check():
    """
    Health check endpoint for monitoring.
    """
    # Reduced logging noise for health checks
    config = get_config_status()
    return APIStatusResponse(
        status="ok",
        version="1.0.0",
        github_configured=config["github_configured"],
        openrouter_configured=config["openrouter_configured"],
        llm_model=config["llm_model"]
    )


@app.post(
    "/review",
    response_model=ReviewResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        404: {"model": ErrorResponse, "description": "PR not found"},
        500: {"model": ErrorResponse, "description": "Server error"},
        502: {"model": ErrorResponse, "description": "External API error"}
    }
)
async def create_review(request: ReviewRequest):
    """
    Review a GitHub Pull Request.
    
    Accepts a GitHub PR URL, fetches the diff, and returns an AI-generated
    structured code review with file-level comments and a final decision.
    """
    logger.info(f"Received review request for URL: {request.pr_url}")
    
    try:
        result = await review_pull_request(request.pr_url)
        logger.info("Review request processed successfully")
        return result
    
    except ValueError as e:
        # Invalid URL format or configuration issues
        logger.error(f"ValueError during review: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTPStatusError from external API: {e.response.status_code} - {e}")
        # Handle different HTTP error codes
        if e.response.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail=f"PR not found or inaccessible. If this is a private repository, please ensure GITHUB_TOKEN is set in .env"
            )
        elif e.response.status_code == 401:
            raise HTTPException(
                status_code=502,
                detail="Authentication failed. Check your GITHUB_TOKEN or OPENROUTER_API_KEY."
            )
        elif e.response.status_code == 403:
            raise HTTPException(
                status_code=502,
                detail="Access forbidden. You may have hit a rate limit or lack permissions."
            )
        else:
            raise HTTPException(
                status_code=502,
                detail=f"External API error: {e.response.status_code} - {str(e)}"
            )
    
    except httpx.RequestError as e:
        # Network/connection errors
        logger.error(f"Httpx RequestError: {str(e)}")
        raise HTTPException(
            status_code=502,
            detail=f"Failed to connect to external service: {str(e)}"
        )
    
    except Exception as e:
        # Catch-all for unexpected errors
        logger.exception("Unexpected error during review processing")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    # Use standard logging config for uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
