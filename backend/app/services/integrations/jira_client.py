"""
Jira client using the official jira Python library.
Supports username/password authentication.
"""
from typing import Any

from jira import JIRA, JIRAError

from app.config import settings
from app.services.observability.logger import get_logger

logger = get_logger(__name__)


class JiraClient:
    """Jira client using the jira Python library with username/password auth."""

    def __init__(self) -> None:
        self._client: JIRA | None = None
        self._url = settings.jira_url
        self._username = settings.jira_username
        self._password = settings.jira_password

    def _get_client(self) -> JIRA | None:
        """Get or create JIRA client instance."""
        if self._client is not None:
            return self._client

        if not all([self._url, self._username, self._password]):
            logger.warning("Jira credentials not fully configured")
            return None

        try:
            # For Jira Cloud: use basic auth with username(email) and password/API token
            # For Jira Server/Data Center: use basic auth with username and password
            self._client = JIRA(
                server=self._url,
                basic_auth=(self._username, self._password),
                options={
                    "server": self._url,
                    "verify": True,  # Verify SSL certificates
                },
                max_retries=1,
            )
            logger.info("Jira client initialized successfully")
            return self._client
        except JIRAError as e:
            logger.error(f"Failed to initialize Jira client: {e}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error initializing Jira client: {e}")
            return None

    def _is_configured(self) -> bool:
        """Check if Jira is properly configured."""
        return all([self._url, self._username, self._password])

    async def get_projects(self) -> dict[str, Any] | str:
        """Get all accessible Jira projects.

        Returns:
            Formatted string with project list or error message
        """
        if not self._is_configured():
            return "Jira credentials are not configured. Please configure JIRA_URL, JIRA_USERNAME, and JIRA_PASSWORD in .env."

        client = self._get_client()
        if client is None:
            return "Failed to connect to Jira. Please check your credentials."

        try:
            projects = client.projects()

            if not projects:
                return "No Jira projects found."

            result_lines = [f"Found {len(projects)} projects:\n"]
            for project in projects:
                result_lines.append(
                    f"- Project Key: {project.key}\n"
                    f"  Name: {project.name}\n"
                )

            return "\n".join(result_lines)

        except JIRAError as e:
            logger.error(f"Jira get projects error: {e}")
            return f"Error getting Jira projects: {e.text if hasattr(e, 'text') else str(e)}"
        except Exception as e:
            logger.exception("Unexpected error getting Jira projects")
            return f"Error getting Jira projects: {e}"

    async def search_issues(self, jql: str, max_results: int = 10) -> dict[str, Any] | str:
        """Execute a JQL search query against Jira.

        Args:
            jql: JQL query string (e.g., "project = PROJ AND status = Open")
            max_results: Maximum number of results to return

        Returns:
            Formatted string with search results or error message
        """
        if not self._is_configured():
            return "Jira credentials are not configured. Please configure JIRA_URL, JIRA_USERNAME, and JIRA_PASSWORD in .env."

        client = self._get_client()
        if client is None:
            return "Failed to connect to Jira. Please check your credentials."

        try:
            # jira library is synchronous, but we wrap it for async compatibility
            issues = client.search_issues(jql, maxResults=max_results)

            if not issues:
                return f"No Jira issues found for JQL: '{jql}'"

            result_lines = [f"Found {len(issues)} issues for JQL: '{jql}'\n"]
            for issue in issues:
                assignee = issue.fields.assignee
                assignee_name = assignee.displayName if assignee else "Unassigned"

                result_lines.append(
                    f"- Task ID: {issue.key}\n"
                    f"  Summary: {issue.fields.summary or 'No summary'}\n"
                    f"  Status: {issue.fields.status.name}\n"
                    f"  Assignee: {assignee_name}\n"
                )

            return "\n".join(result_lines)

        except JIRAError as e:
            logger.error(f"Jira search error: {e}")
            return f"Error searching Jira: {e.text if hasattr(e, 'text') else str(e)}"
        except Exception as e:
            logger.exception("Unexpected error searching Jira")
            return f"Error searching Jira: {e}"

    async def count_issues(self, jql: str) -> dict[str, Any] | str:
        """Count Jira issues matching a JQL query (returns count only).

        Args:
            jql: JQL query string (e.g., "project = PROJ AND status = Open")

        Returns:
            Count of matching issues or error message
        """
        if not self._is_configured():
            return "Jira credentials are not configured. Please configure JIRA_URL, JIRA_USERNAME, and JIRA_PASSWORD in .env."

        client = self._get_client()
        if client is None:
            return "Failed to connect to Jira. Please check your credentials."

        try:
            # Use search_issues with maxResults=0 to get total count only
            result = client.search_issues(jql, maxResults=0)
            total = result.total if hasattr(result, 'total') else len(result)
            return {"jql": jql, "count": total}

        except JIRAError as e:
            logger.error(f"Jira count error: {e}")
            return f"Error counting Jira issues: {e.text if hasattr(e, 'text') else str(e)}"
        except Exception as e:
            logger.exception("Unexpected error counting Jira issues")
            return f"Error counting Jira issues: {e}"

    async def get_issue(self, issue_key: str) -> dict[str, Any] | str:
        """Get details for a specific Jira issue.

        Args:
            issue_key: Issue key (e.g., "PROJ-123")

        Returns:
            Formatted string with issue details or error message
        """
        if not self._is_configured():
            return "Jira credentials are not configured."

        client = self._get_client()
        if client is None:
            return "Failed to connect to Jira. Please check your credentials."

        try:
            issue = client.issue(issue_key)

            assignee = issue.fields.assignee
            assignee_name = assignee.displayName if assignee else "Unassigned"

            # Handle description which might be a string or a dict (ADF format)
            description = issue.fields.description
            if description is None:
                description_text = "No description"
            elif isinstance(description, str):
                description_text = description
            elif isinstance(description, dict):
                # ADF (Atlassian Document Format) - extract text simply
                description_text = self._extract_text_from_adf(description) or "No description"
            else:
                description_text = str(description)

            return (
                f"Task ID: {issue.key}\n"
                f"Summary: {issue.fields.summary or 'No summary'}\n"
                f"Status: {issue.fields.status.name}\n"
                f"Assignee: {assignee_name}\n"
                f"Description: {description_text}\n"
            )

        except JIRAError as e:
            if e.status_code == 404:
                return f"Jira issue {issue_key} not found."
            logger.error(f"Jira get issue error: {e}")
            return f"Error fetching Jira issue {issue_key}: {e.text if hasattr(e, 'text') else str(e)}"
        except Exception as e:
            logger.exception(f"Unexpected error getting Jira issue {issue_key}")
            return f"Error fetching Jira issue {issue_key}: {e}"

    def _extract_text_from_adf(self, adf: dict) -> str:
        """Extract plain text from Atlassian Document Format (ADF).

        ADF is a JSON format used by Jira for rich text content.
        This is a simple extraction - for full ADF support, consider using
        the atlassian-document-format library.
        """
        if not adf or not isinstance(adf, dict):
            return ""

        def extract_text(node: dict | list) -> str:
            if isinstance(node, str):
                return node
            if isinstance(node, list):
                return " ".join(extract_text(item) for item in node)
            if isinstance(node, dict):
                text = node.get("text", "")
                content = node.get("content", [])
                return text + " " + extract_text(content)
            return ""

        return extract_text(adf).strip()