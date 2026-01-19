"""
Streamlit UI for AI PR Reviewer Demo.
"""

import os
import streamlit as st
import requests
from typing import Optional

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")


def check_api_status() -> Optional[dict]:
    """Check if the backend API is running and get its status."""
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        if response.status_code == 200:
            return response.json()
    except requests.RequestException:
        pass
    return None


def submit_review(pr_url: str, post_to_github: bool = False) -> dict:
    """Submit a PR URL for review."""
    response = requests.post(
        f"{API_URL}/review",
        json={"pr_url": pr_url, "post_to_github": post_to_github},
        timeout=120  # LLM calls can take a while
    )
    return response.json(), response.status_code


def render_decision_badge(decision: str):
    """Render a colored badge for the review decision."""
    if decision == "APPROVE":
        st.markdown(
            """
            <div style="
                display: inline-block;
                background: linear-gradient(135deg, #10b981, #059669);
                color: white;
                padding: 12px 24px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 18px;
                box-shadow: 0 4px 12px rgba(16, 185, 129, 0.4);
            ">
                ✅ APPROVED
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            """
            <div style="
                display: inline-block;
                background: linear-gradient(135deg, #ef4444, #dc2626);
                color: white;
                padding: 12px 24px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 18px;
                box-shadow: 0 4px 12px rgba(239, 68, 68, 0.4);
            ">
                ⚠️ CHANGES REQUESTED
            </div>
            """,
            unsafe_allow_html=True
        )


def render_comments_table(comments: list):
    """Render file comments as a styled table."""
    if not comments:
        st.info("No specific issues found. The code looks good! 🎉")
        return
    
    st.markdown("### 📝 File Comments")
    
    for i, comment in enumerate(comments, 1):
        with st.expander(f"**{comment['file']}** (Line {comment['line']})", expanded=True):
            st.markdown(f"**🔍 Issue:**\n{comment['issue']}")
            st.markdown(f"**💡 Suggestion:**\n{comment['suggestion']}")


def main():
    # Page configuration
    st.set_page_config(
        page_title="AI PR Reviewer",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS for better aesthetics
    st.markdown("""
        <style>
        .main-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            font-size: 2.5rem;
            font-weight: 800;
            margin-bottom: 0.5rem;
        }
        .subtitle {
            color: #6b7280;
            font-size: 1.1rem;
            margin-bottom: 2rem;
        }
        .stTextInput > div > div > input {
            border-radius: 8px;
        }
        .summary-box {
            background: linear-gradient(135deg, #f0f9ff, #e0f2fe);
            border-left: 4px solid #0ea5e9;
            padding: 1rem;
            border-radius: 0 8px 8px 0;
            margin: 1rem 0;
        }
        .status-ok {
            color: #10b981;
            font-weight: bold;
        }
        .status-error {
            color: #ef4444;
            font-weight: bold;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Sidebar for API Status
    with st.sidebar:
        st.markdown("## ⚙️ System Status")
        st.divider()
        
        api_status = check_api_status()
        
        if api_status:
            st.markdown('<p class="status-ok">🟢 API Connected</p>', unsafe_allow_html=True)
            st.markdown(f"**Version:** {api_status.get('version', 'N/A')}")
            st.markdown(f"**LLM Model:** `{api_status.get('llm_model', 'N/A')}`")
            
            st.divider()
            st.markdown("**Configuration:**")
            
            github_ok = api_status.get('github_configured', False)
            openrouter_ok = api_status.get('openrouter_configured', False)
            
            if github_ok:
                st.markdown("✅ GitHub Token configured")
            else:
                st.markdown("⚠️ GitHub Token not set (public repos only)")
            
            if openrouter_ok:
                st.markdown("✅ OpenRouter API configured")
            else:
                st.markdown("❌ OpenRouter API key missing")
        else:
            st.markdown('<p class="status-error">🔴 API Disconnected</p>', unsafe_allow_html=True)
            st.warning("Backend API is not running. Start the FastAPI server first.")
        
        st.divider()
        st.markdown("### 📖 How to Use")
        st.markdown("""
        1. Paste a GitHub PR URL
        2. (Optional) Check the box to post review to GitHub
        3. Click **Run Review**
        4. View results here and/or on GitHub
        """)
        
        st.divider()
        st.markdown("### 🔗 Example PRs")
        st.code("https://github.com/facebook/react/pull/28457", language=None)
    
    # Main content area
    st.markdown('<h1 class="main-header">🤖 AI PR Reviewer</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Intelligent code review powered by AI. Paste a GitHub PR URL to get instant, structured feedback.</p>', unsafe_allow_html=True)
    
    # Input section
    col1, col2 = st.columns([4, 1])
    
    with col1:
        pr_url = st.text_input(
            "GitHub PR URL",
            placeholder="https://github.com/owner/repo/pull/123",
            label_visibility="collapsed"
        )
    
    with col2:
        review_button = st.button(
            "🚀 Run Review",
            type="primary",
            use_container_width=True
        )
    
    # Add checkbox for posting to GitHub
    post_to_github = st.checkbox(
        "💬 **Post review as comment directly to GitHub PR**",
        value=False,
        help="Requires GITHUB_TOKEN to be configured. The review will be posted as a comment on the PR in addition to showing results here."
    )
    
    st.divider()
    
    # Review logic
    if review_button:
        if not pr_url:
            st.error("Please enter a GitHub PR URL")
        elif not pr_url.startswith("https://github.com/"):
            st.error("Invalid URL. Please enter a valid GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)")
        else:
            # Check API status first
            if not check_api_status():
                st.error("❌ Cannot connect to the backend API. Please ensure the FastAPI server is running.")
            else:
                with st.spinner("🔍 Analyzing Pull Request... This may take 30-60 seconds."):
                    try:
                        result, status_code = submit_review(pr_url, post_to_github)
                        
                        if status_code == 200:
                            # Success - display results
                            st.success("Review completed successfully!")
                            
                            # Show GitHub comment status if posting was requested
                            if post_to_github:
                                if result.get("github_comment_posted", False):
                                    comment_url = result.get("github_comment_url")
                                    if comment_url:
                                        st.success(f"✅ Review posted to GitHub! [View comment]({comment_url})")
                                    else:
                                        st.success("✅ Review posted to GitHub!")
                                else:
                                    st.warning("⚠️ Review generated but could not be posted to GitHub. Check that GITHUB_TOKEN is configured and has write permissions.")
                            
                            # Decision badge
                            st.markdown("### 📊 Review Decision")
                            render_decision_badge(result.get("decision", "REQUEST_CHANGES"))
                            
                            st.markdown("<br>", unsafe_allow_html=True)
                            
                            # Summary
                            st.markdown("### 📋 Summary")
                            st.markdown(
                                f'<div class="summary-box">{result.get("summary", "No summary available")}</div>',
                                unsafe_allow_html=True
                            )
                            
                            # Comments table
                            render_comments_table(result.get("comments", []))
                            
                            # Raw JSON expander for debugging
                            with st.expander("🔧 Raw API Response"):
                                st.json(result)
                        
                        else:
                            # Error response
                            error_msg = result.get("detail", "Unknown error occurred")
                            st.error(f"❌ Review failed: {error_msg}")
                    
                    except requests.Timeout:
                        st.error("❌ Request timed out. The PR might be too large or the LLM is taking too long.")
                    
                    except requests.RequestException as e:
                        st.error(f"❌ Network error: {str(e)}")
                    
                    except Exception as e:
                        st.error(f"❌ Unexpected error: {str(e)}")
    
    # Footer
    st.divider()
    st.markdown(
        "<div style='text-align: center; color: #9ca3af; font-size: 0.875rem;'>"
        "AI PR Reviewer Demo • Powered by OpenRouter & FastAPI"
        "</div>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
