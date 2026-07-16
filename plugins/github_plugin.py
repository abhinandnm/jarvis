"""
GitHub Plugin — Integrates with GitHub API to list repositories, issues, commits, and more.
Requires GITHUB_TOKEN in .env for authenticated access.
"""

import logging
from typing import Dict, Any, List
from plugins.base import PluginBase
from config.config import settings

logger = logging.getLogger("jarvis.plugins.github")


class GitHubPlugin(PluginBase):
    """JARVIS Plugin for GitHub operations."""

    @property
    def name(self) -> str:
        return "github"

    @property
    def description(self) -> str:
        return "Interact with GitHub: list repositories, issues, pull requests, and commits."

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "github_list_repos",
                "description": "Lists the authenticated user's GitHub repositories.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of repos to return",
                            "default": 10
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "github_list_issues",
                "description": "Lists open issues for a specific GitHub repository.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "repo": {
                            "type": "string",
                            "description": "Repository in 'owner/repo' format (e.g. 'octocat/Hello-World')"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of issues to return",
                            "default": 10
                        }
                    },
                    "required": ["repo"]
                }
            },
            {
                "name": "github_recent_commits",
                "description": "Lists recent commits for a specific GitHub repository.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "repo": {
                            "type": "string",
                            "description": "Repository in 'owner/repo' format"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Number of recent commits to return",
                            "default": 5
                        }
                    },
                    "required": ["repo"]
                }
            }
        ]

    async def execute(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Execute a GitHub tool action."""
        token = getattr(settings, "GITHUB_TOKEN", None)
        if not token:
            return (
                "GitHub plugin requires a GITHUB_TOKEN. "
                "Add GITHUB_TOKEN=your_token to your .env file."
            )

        try:
            import httpx
            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json"
            }

            async with httpx.AsyncClient(headers=headers, timeout=15) as client:
                if tool_name == "github_list_repos":
                    return await self._list_repos(client, args.get("limit", 10))
                elif tool_name == "github_list_issues":
                    return await self._list_issues(client, args["repo"], args.get("limit", 10))
                elif tool_name == "github_recent_commits":
                    return await self._recent_commits(client, args["repo"], args.get("limit", 5))
                else:
                    return f"Unknown GitHub tool: {tool_name}"

        except ImportError:
            return "GitHub plugin requires httpx. Run: pip install httpx"
        except Exception as e:
            logger.error(f"GitHub plugin error: {e}")
            return f"GitHub API error: {str(e)}"

    async def _list_repos(self, client, limit: int) -> str:
        r = await client.get("https://api.github.com/user/repos", params={"per_page": limit, "sort": "updated"})
        if r.status_code != 200:
            return f"GitHub API error: {r.status_code} — {r.text}"
        repos = r.json()
        if not repos:
            return "No repositories found."
        lines = ["Your GitHub repositories:"]
        for repo in repos[:limit]:
            stars = repo.get("stargazers_count", 0)
            lang = repo.get("language") or "Unknown"
            lines.append(f"• {repo['full_name']} ({lang}) ⭐{stars}")
        return "\n".join(lines)

    async def _list_issues(self, client, repo: str, limit: int) -> str:
        r = await client.get(f"https://api.github.com/repos/{repo}/issues", params={"per_page": limit, "state": "open"})
        if r.status_code != 200:
            return f"GitHub API error: {r.status_code} — {r.text}"
        issues = [i for i in r.json() if "pull_request" not in i]
        if not issues:
            return f"No open issues found in {repo}."
        lines = [f"Open issues in {repo}:"]
        for issue in issues[:limit]:
            lines.append(f"• #{issue['number']}: {issue['title']}")
        return "\n".join(lines)

    async def _recent_commits(self, client, repo: str, limit: int) -> str:
        r = await client.get(f"https://api.github.com/repos/{repo}/commits", params={"per_page": limit})
        if r.status_code != 200:
            return f"GitHub API error: {r.status_code} — {r.text}"
        commits = r.json()
        if not commits:
            return f"No commits found in {repo}."
        lines = [f"Recent commits in {repo}:"]
        for c in commits[:limit]:
            msg = c["commit"]["message"].split("\n")[0][:80]
            author = c["commit"]["author"]["name"]
            lines.append(f"• {author}: {msg}")
        return "\n".join(lines)
