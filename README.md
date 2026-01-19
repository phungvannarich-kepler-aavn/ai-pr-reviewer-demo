# 🤖 AI PR Reviewer Demo

An AI-powered GitHub Pull Request reviewer that provides structured code review feedback using LLMs.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.31-red.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## ✨ Features

- **🔍 PR Analysis**: Paste any GitHub PR URL to get instant AI-powered code review
- **� GitHub Integration**: Optionally post review comments directly to PRs using GitHub API
- **�📝 Structured Feedback**: Receive file-level comments with specific line numbers and suggestions
- **✅ Clear Decisions**: Get APPROVE or REQUEST_CHANGES verdict with reasoning
- **🎨 Modern UI**: Beautiful Streamlit interface with real-time status updates
- **🔒 Secure**: API keys managed via environment variables
- **🐳 Docker Ready**: One-command deployment with Docker Compose

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Streamlit UI  │────▶│  FastAPI Backend │────▶│   GitHub API    │
│   (Port 8501)   │     │   (Port 8000)    │     │   (Diff Fetch)  │
└─────────────────┘     └────────┬─────────┘     └─────────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │   OpenRouter    │
                        │   (LLM API)     │
                        └─────────────────┘
```

## 📁 Project Structure

```
ai-pr-reviewer-demo/
├── backend/
│   ├── main.py          # FastAPI app & routes
│   ├── logic.py         # GitHub & LLM integration
│   ├── models.py        # Pydantic schemas
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── app.py           # Streamlit UI
│   ├── requirements.txt
│   └── Dockerfile
├── .env.example
├── docker-compose.yml
└── README.md
```

## 🚀 Quick Start

### Option 1: Local Python Setup

#### Prerequisites
- Python 3.11+
- An [OpenRouter API key](https://openrouter.ai/keys)
- (Optional) A [GitHub Personal Access Token](https://github.com/settings/tokens) for private repos

#### Steps

1. **Clone and setup environment**
   ```bash
   cd ai-pr-reviewer-demo
   cp .env.example .env
   ```

2. **Edit `.env` with your API keys**
   ```env
   OPENROUTER_API_KEY=sk-or-v1-your-key-here
   GITHUB_TOKEN=ghp_your_token_here  # Optional
   LLM_MODEL=anthropic/claude-3-haiku
   ```

3. **Install backend dependencies**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

4. **Start the backend server**
   ```bash
   # From backend/ directory
   # Windows
   set OPENROUTER_API_KEY=your-key && python -m uvicorn main:app --reload
   
   # Linux/Mac
   OPENROUTER_API_KEY=your-key uvicorn main:app --reload
   ```
   
   Or use python-dotenv by adding this to the top of `main.py`:
   ```python
   from dotenv import load_dotenv
   load_dotenv("../.env")
   ```

5. **Install frontend dependencies** (new terminal)
   ```bash
   cd frontend
   pip install -r requirements.txt
   ```

6. **Start the frontend**
   ```bash
   # From frontend/ directory
   streamlit run app.py
   ```

7. **Open your browser**
   - Frontend: http://localhost:8501
   - API Docs: http://localhost:8000/docs

### Option 2: Docker Compose

```bash
# From project root
cp .env.example .env
# Edit .env with your API keys

docker-compose up --build
```

Access:
- **Frontend**: http://localhost:8501
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 📖 API Reference

### `POST /review`

Submit a PR for review.

**Request:**
```json
{
  "pr_url": "https://github.com/owner/repo/pull/123",
  "post_to_github": false  // Optional: Set to true to post review as GitHub comment
}
```

**Response:**
```json
{
  "summary": "This PR adds a new authentication module with JWT support...",
  "comments": [
    {
      "file": "src/auth.py",
      "line": 42,
      "issue": "Hardcoded secret key detected",
      "suggestion": "Use environment variable for SECRET_KEY"
    }
  ],
  "decision": "REQUEST_CHANGES",
  "github_comment_posted": false,  // Whether review was posted to GitHub
  "github_comment_url": null       // URL of GitHub comment if posted
}
```

### `GET /health`

Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "version": "1.0.0",
  "github_configured": true,
  "openrouter_configured": true,
  "llm_model": "anthropic/claude-3-haiku"
}
```

## 🧠 LLM System Prompt

The system prompt instructs the LLM to return structured JSON:

```
You are an expert code reviewer. Your task is to analyze a GitHub Pull Request 
diff and provide a structured review.

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

IMPORTANT: Return ONLY the JSON object, no markdown, no code blocks, no additional text.
```

## ⚙️ Configuration Options

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `OPENROUTER_API_KEY` | Your OpenRouter API key | - | ✅ Yes |
| `GITHUB_TOKEN` | GitHub PAT for private repos & posting comments | - | ❌ No |
| `LLM_MODEL` | OpenRouter model ID | `anthropic/claude-3-haiku` | ❌ No |
| `API_URL` | Backend URL (frontend only) | `http://localhost:8000` | ❌ No |

### GitHub Token Permissions

To post review comments directly to GitHub PRs, your `GITHUB_TOKEN` needs:
- **Read access**: To fetch PR diffs (for any repo, public or private)
- **Write access**: To post comments on issues/PRs (required for posting reviews)

Create a Personal Access Token at [GitHub Settings > Tokens](https://github.com/settings/tokens) with:
- Classic Token: Select `repo` scope (or `public_repo` for public repos only)
- Fine-grained Token: Grant `Contents: Read` and `Pull requests: Read & Write`

### How GitHub Comment Posting Works

1. User checks "Post review as comment to GitHub PR" in the UI
2. Backend generates the review using LLM
3. Review is formatted as markdown with emojis and sections
4. Backend posts the comment via GitHub API
5. User sees the review both in the UI and as a GitHub comment
6. GitHub comment URL is provided for quick access

### Supported LLM Models

- `anthropic/claude-3-haiku` - Fast and cost-effective (recommended)
- `anthropic/claude-3-sonnet` - Balanced performance
- `anthropic/claude-3-opus` - Highest quality
- `openai/gpt-4-turbo` - OpenAI's flagship
- `openai/gpt-3.5-turbo` - Fast and cheap
- `google/gemini-pro` - Google's model
- [See all models](https://openrouter.ai/models)

## 🔧 Troubleshooting

### "API Disconnected" in Sidebar
- Ensure the FastAPI backend is running on port 8000
- Check if `API_URL` environment variable is correct

### "Invalid GitHub PR URL"
- URL must match format: `https://github.com/owner/repo/pull/123`
- Ensure the PR exists and is accessible

### "Authentication failed"
- Verify your `OPENROUTER_API_KEY` is valid
- Check your `GITHUB_TOKEN` has correct permissions

### "Request timed out"
- Large PRs may take longer to process
- Try a smaller PR or increase timeout settings

### Rate Limits
- GitHub API: 60 requests/hour without token, 5000 with token
- OpenRouter: Depends on your plan

## 📝 Usage Examples

### Test with Public PRs

```bash
# React PR
https://github.com/facebook/react/pull/28457

# FastAPI PR  
https://github.com/tiangolo/fastapi/pull/10000

# VS Code PR
https://github.com/microsoft/vscode/pull/200000
```

### cURL Example

```bash
# Review only (show in UI)
curl -X POST http://localhost:8000/review \
  -H "Content-Type: application/json" \
  -d '{"pr_url": "https://github.com/owner/repo/pull/123"}'

# Review and post to GitHub
curl -X POST http://localhost:8000/review \
  -H "Content-Type: application/json" \
  -d '{"pr_url": "https://github.com/owner/repo/pull/123", "post_to_github": true}'
```

## 🛡️ Security Notes

- **Never commit `.env` files** - Use `.env.example` as template
- **API keys are server-side only** - Frontend never sees sensitive keys
- **Rate limiting not implemented** - Add for production use
- **No authentication** - Add for production deployments

## 📄 License

MIT License - feel free to use this for learning and demos.

---

Built with ❤️ using FastAPI, Streamlit, and OpenRouter
