"""
Core business logic for GitHub integration and LLM-based PR review.
"""

import json
import os
import re
import logging
from typing import Tuple

import httpx

from models import ReviewResponse, FileComment, ReviewDecision

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("ai_pr_reviewer")

# Configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "anthropic/claude-3-haiku")
MAX_DIFF_CHARS = 10_000

# System prompt for structured JSON output
SYSTEM_PROMPT = """You are an expert code reviewer. Your task is to analyze a GitHub Pull Request diff and provide a structured review.

CRITICAL: You MUST respond with ONLY valid JSON matching this exact schema:
{
  "summary": "A concise high-level summary of the PR review (1-3 sentences)",
  "comments": [
    {
      "file": "path/to/file.ext",
      "line": 42,
      "issue": "Clear description of the problem",
      "suggestion": "Specific suggestion to fix the issue"
    }
  ],
  "decision": "APPROVE" or "REQUEST_CHANGES"
}

Review Guidelines:
1. Focus on: bugs, security issues, performance problems, code quality, and best practices.
2. Be constructive and specific in your suggestions.
3. If the code looks good with no major issues, use "APPROVE".
4. If there are bugs, security issues, or significant problems, use "REQUEST_CHANGES".
5. For minor style issues, still use "APPROVE" but include helpful comments.
6. The "comments" array can be empty if no specific issues are found.
7. Always include a meaningful summary.

IMPORTANT: Return ONLY the JSON object, no markdown, no code blocks, no additional text."""


def parse_pr_url(pr_url: str) -> Tuple[str, str, int]:
    """
    Parse a GitHub PR URL to extract owner, repo, and PR number.
    """
    logger.info(f"Parsing PR URL: {pr_url}")
    # Match patterns like:
    # https://github.com/owner/repo/pull/123
    pattern = r"https?://github\.com/([^/]+)/([^/]+)/pull/(\d+)"
    match = re.match(pattern, pr_url.strip())
    
    if not match:
        logger.error(f"Invalid PR URL format: {pr_url}")
        raise ValueError(
            f"Invalid GitHub PR URL format. Expected: https://github.com/owner/repo/pull/123"
        )
    
    owner, repo, pr_number = match.groups()
    logger.info(f"Parsed: Owner={owner}, Repo={repo}, PR={pr_number}")
    return owner, repo, int(pr_number)


async def fetch_pr_diff(owner: str, repo: str, pr_number: int) -> str:
    """
    Fetch the diff content utilizing the GitHub API.
    """
    # Use the API endpoint which is more robust than the .diff URL
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    
    headers = {
        "Accept": "application/vnd.github.v3.diff",  # Request raw diff
        "User-Agent": "AI-PR-Reviewer-Demo/1.0",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    
    # Add auth header if token is available
    if GITHUB_TOKEN:
        logger.info("Using authenticated GitHub request")
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    else:
        logger.info("Using unauthenticated GitHub request (rate limits may apply)")
    
    logger.info(f"Fetching diff from: {url}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, headers=headers, follow_redirects=True)
        
        logger.info(f"GitHub API Response Status: {response.status_code}")
        
        if response.status_code == 404:
            logger.error(f"PR not found: {url}")
            raise httpx.HTTPStatusError(
                f"Pull Request not found (404). If this is a private repo, ensure GITHUB_TOKEN is set.", 
                request=response.request, 
                response=response
            )
            
        response.raise_for_status()
        
        diff_content = response.text
        logger.info(f"Successfully fetched diff. Size: {len(diff_content)} characters")
        return diff_content


def truncate_diff(diff_content: str, max_chars: int = MAX_DIFF_CHARS) -> str:
    """
    Truncate diff content to prevent LLM context overflows.
    """
    if len(diff_content) <= max_chars:
        return diff_content
    
    logger.warning(f"Diff too large ({len(diff_content)} chars). Truncating to {max_chars} chars.")
    truncated = diff_content[:max_chars]
    # Try to cut at a line boundary
    last_newline = truncated.rfind('\n')
    if last_newline > max_chars * 0.8:
        truncated = truncated[:last_newline]
    
    return truncated + "\n\n[... DIFF TRUNCATED DUE TO SIZE LIMIT ...]"


async def call_openrouter_llm(diff_content: str) -> str:
    """
    Send the diff to OpenRouter LLM and get the review response.
    """
    if not OPENROUTER_API_KEY:
        logger.error("OPENROUTER_API_KEY is missing")
        raise ValueError("OPENROUTER_API_KEY environment variable is not set")
    
    logger.info(f"Preparing LLM request using model: {LLM_MODEL}")
    
    user_message = f"""Please review the following Pull Request diff and provide your analysis:

```diff
{diff_content}
```

Remember to respond with ONLY valid JSON matching the required schema."""

    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ],
        "temperature": 0.2, # Lower temperature for more consistent JSON
        "max_tokens": 2000
    }
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://ai-pr-reviewer-demo.local",
        "X-Title": "AI PR Reviewer Demo"
    }
    
    logger.info("Sending request to OpenRouter...")
    
    async with httpx.AsyncClient(timeout=90.0) as client: # Increased timeout for LLM
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            json=payload,
            headers=headers
        )
        
        if response.status_code != 200:
            logger.error(f"OpenRouter API Error: {response.status_code} - {response.text}")
        
        response.raise_for_status()
        
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        logger.info("Received response from OpenRouter")
        logger.debug(f"Raw LLM Response: {content[:200]}...") # Log first 200 chars
        return content


def parse_llm_response(raw_response: str) -> ReviewResponse:
    """
    Parse the LLM response into a structured ReviewResponse.
    """
    logger.info("Parsing LLM response...")
    # Clean up common formatting issues
    cleaned = raw_response.strip()
    
    # Remove markdown code blocks if present
    if cleaned.startswith("```"):
        first_newline = cleaned.find("\n")
        if first_newline != -1:
            cleaned = cleaned[first_newline + 1:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()
            
    logger.debug(f"Cleaned JSON string: {cleaned[:100]}...")
    
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.warning(f"JSON Decode Error: {e}. Attempting regex extraction.")
        # Try to extract JSON from the response
        json_match = re.search(r'\{[\s\S]*\}', cleaned)
        if json_match:
            try:
                data = json.loads(json_match.group())
            except json.JSONDecodeError:
                logger.error("Failed to extract valid JSON via regex")
                raise ValueError(f"Failed to parse LLM response as JSON: {e}")
        else:
            logger.error("No JSON structure found in response")
            raise ValueError(f"No valid JSON found in LLM response: {e}")
    
    try:
        # Handle decision enum
        decision_str = data.get("decision", "REQUEST_CHANGES").upper()
        if decision_str not in ["APPROVE", "REQUEST_CHANGES"]:
            logger.warning(f"Invalid decision '{decision_str}', defaulting to REQUEST_CHANGES")
            decision_str = "REQUEST_CHANGES"
        
        # Parse comments
        comments = []
        for c in data.get("comments", []):
            comments.append(FileComment(
                file=str(c.get("file", "unknown")),
                line=max(1, int(c.get("line", 1))),
                issue=str(c.get("issue", "")),
                suggestion=str(c.get("suggestion", ""))
            ))
        
        logger.info(f"Successfully parsed review with {len(comments)} comments and decision {decision_str}")
        
        return ReviewResponse(
            summary=str(data.get("summary", "No summary provided")),
            comments=comments,
            decision=ReviewDecision(decision_str)
        )
    except Exception as e:
        logger.error(f"Error constructing ReviewResponse: {e}")
        raise ValueError(f"Failed to construct ReviewResponse: {e}")


async def review_pull_request(pr_url: str) -> ReviewResponse:
    """
    Main function to review a GitHub Pull Request.
    """
    logger.info(f"Starting review process for: {pr_url}")
    
    # Parse the PR URL
    owner, repo, pr_number = parse_pr_url(pr_url)
    
    # Fetch the diff
    diff_content = await fetch_pr_diff(owner, repo, pr_number)
    
    if not diff_content.strip():
        logger.warning("Fetched diff is empty")
        return ReviewResponse(
            summary="This PR appears to have no changes or an empty diff.",
            comments=[],
            decision=ReviewDecision.APPROVE
        )
    
    # Truncate if necessary
    diff_content = truncate_diff(diff_content)
    
    # Get LLM review
    raw_response = await call_openrouter_llm(diff_content)
    
    # Parse and return
    result = parse_llm_response(raw_response)
    logger.info("Review process completed successfully")
    return result


def get_config_status() -> dict:
    """
    Get current configuration status.
    """
    return {
        "github_configured": bool(GITHUB_TOKEN),
        "openrouter_configured": bool(OPENROUTER_API_KEY),
        "llm_model": LLM_MODEL
    }
