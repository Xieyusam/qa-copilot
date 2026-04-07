"""
Jira 客户端测试。
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from app.services.jira_client import JiraClient


class TestJiraClient:
    """JiraClient 测试类。"""

    def test_is_configured_true(self):
        """正确配置时应返回 True。"""
        with patch("app.services.jira_client.settings") as mock_settings:
            mock_settings.jira_url = "https://jira.example.com"
            mock_settings.jira_username = "user@example.com"
            mock_settings.jira_password = "password"

            client = JiraClient()
            assert client._is_configured() is True

    def test_is_configured_false_missing_url(self):
        """缺少 URL 时应返回 False。"""
        with patch("app.services.jira_client.settings") as mock_settings:
            mock_settings.jira_url = None
            mock_settings.jira_username = "user@example.com"
            mock_settings.jira_password = "password"

            client = JiraClient()
            assert client._is_configured() is False

    def test_is_configured_false_missing_credentials(self):
        """缺少凭据时应返回 False。"""
        with patch("app.services.jira_client.settings") as mock_settings:
            mock_settings.jira_url = "https://jira.example.com"
            mock_settings.jira_username = None
            mock_settings.jira_password = None

            client = JiraClient()
            assert client._is_configured() is False

    @pytest.mark.asyncio
    async def test_search_issues_not_configured(self):
        """未配置时应返回错误消息。"""
        with patch("app.services.jira_client.settings") as mock_settings:
            mock_settings.jira_url = None
            mock_settings.jira_username = None
            mock_settings.jira_password = None

            client = JiraClient()
            result = await client.search_issues("project = TEST")

            assert "not configured" in result.lower()

    @pytest.mark.asyncio
    async def test_search_issues_success(self):
        """成功搜索应返回格式化的结果。"""
        with patch("app.services.jira_client.settings") as mock_settings:
            mock_settings.jira_url = "https://jira.example.com"
            mock_settings.jira_username = "user@example.com"
            mock_settings.jira_password = "password"

            # Mock JIRA client
            mock_jira = MagicMock()
            mock_issue = MagicMock()
            mock_issue.key = "TEST-123"
            mock_issue.fields.summary = "Test issue"
            mock_issue.fields.status.name = "Open"
            mock_issue.fields.assignee = None
            mock_jira.search_issues.return_value = [mock_issue]

            client = JiraClient()
            client._client = mock_jira

            result = await client.search_issues("project = TEST", max_results=10)

            assert "TEST-123" in result
            assert "Test issue" in result
            assert "Open" in result
            assert "Unassigned" in result

    @pytest.mark.asyncio
    async def test_search_issues_empty_result(self):
        """无结果时应返回提示消息。"""
        with patch("app.services.jira_client.settings") as mock_settings:
            mock_settings.jira_url = "https://jira.example.com"
            mock_settings.jira_username = "user@example.com"
            mock_settings.jira_password = "password"

            mock_jira = MagicMock()
            mock_jira.search_issues.return_value = []

            client = JiraClient()
            client._client = mock_jira

            result = await client.search_issues("project = NONEXISTENT")

            assert "No Jira issues found" in result

    @pytest.mark.asyncio
    async def test_get_issue_success(self):
        """成功获取问题详情。"""
        with patch("app.services.jira_client.settings") as mock_settings:
            mock_settings.jira_url = "https://jira.example.com"
            mock_settings.jira_username = "user@example.com"
            mock_settings.jira_password = "password"

            mock_jira = MagicMock()
            mock_issue = MagicMock()
            mock_issue.key = "TEST-456"
            mock_issue.fields.summary = "Detail issue"
            mock_issue.fields.status.name = "In Progress"
            mock_issue.fields.assignee.displayName = "John Doe"
            mock_issue.fields.description = "Issue description"
            mock_jira.issue.return_value = mock_issue

            client = JiraClient()
            client._client = mock_jira

            result = await client.get_issue("TEST-456")

            assert "TEST-456" in result
            assert "Detail issue" in result
            assert "In Progress" in result
            assert "John Doe" in result
            assert "Issue description" in result

    @pytest.mark.asyncio
    async def test_get_issue_not_found(self):
        """问题不存在时应返回 404 提示。"""
        with patch("app.services.jira_client.settings") as mock_settings:
            mock_settings.jira_url = "https://jira.example.com"
            mock_settings.jira_username = "user@example.com"
            mock_settings.jira_password = "password"

            from jira import JIRAError

            mock_jira = MagicMock()
            mock_jira.issue.side_effect = JIRAError(status_code=404)

            client = JiraClient()
            client._client = mock_jira

            result = await client.get_issue("NONEXISTENT-999")

            assert "not found" in result.lower()

    @pytest.mark.asyncio
    async def test_get_projects_success(self):
        """成功获取项目列表。"""
        with patch("app.services.jira_client.settings") as mock_settings:
            mock_settings.jira_url = "https://jira.example.com"
            mock_settings.jira_username = "user@example.com"
            mock_settings.jira_password = "password"

            mock_jira = MagicMock()
            mock_proj1 = MagicMock()
            mock_proj1.key = "PROJ1"
            mock_proj1.name = "Project One"
            mock_proj2 = MagicMock()
            mock_proj2.key = "PROJ2"
            mock_proj2.name = "Project Two"
            mock_jira.projects.return_value = [mock_proj1, mock_proj2]

            client = JiraClient()
            client._client = mock_jira

            result = await client.get_projects()

            assert "PROJ1" in result
            assert "Project One" in result
            assert "PROJ2" in result
            assert "Project Two" in result
            assert "2 projects" in result

    @pytest.mark.asyncio
    async def test_count_issues_success(self):
        """成功统计问题数量。"""
        with patch("app.services.jira_client.settings") as mock_settings:
            mock_settings.jira_url = "https://jira.example.com"
            mock_settings.jira_username = "user@example.com"
            mock_settings.jira_password = "password"

            mock_jira = MagicMock()
            mock_result = MagicMock()
            mock_result.total = 42
            mock_jira.search_issues.return_value = mock_result

            client = JiraClient()
            client._client = mock_jira

            result = await client.count_issues("project = TEST AND resolution = Unresolved")

            assert result["count"] == 42
            assert "project = TEST" in result["jql"]

    @pytest.mark.asyncio
    async def test_create_issue_success(self):
        """成功创建问题。"""
        with patch("app.services.jira_client.settings") as mock_settings:
            mock_settings.jira_url = "https://jira.example.com"
            mock_settings.jira_username = "user@example.com"
            mock_settings.jira_password = "password"

            mock_jira = MagicMock()
            mock_issue = MagicMock()
            mock_issue.key = "TEST-789"
            mock_jira.create_issue.return_value = mock_issue

            client = JiraClient()
            client._client = mock_jira

            result = await client.create_issue(
                project="TEST",
                summary="New issue",
                description="Description",
                issue_type="Task"
            )

            assert "Created issue" in result
            assert "TEST-789" in result

    @pytest.mark.asyncio
    async def test_add_comment_success(self):
        """成功添加评论。"""
        with patch("app.services.jira_client.settings") as mock_settings:
            mock_settings.jira_url = "https://jira.example.com"
            mock_settings.jira_username = "user@example.com"
            mock_settings.jira_password = "password"

            mock_jira = MagicMock()
            mock_jira.add_comment.return_value = None

            client = JiraClient()
            client._client = mock_jira

            result = await client.add_comment("TEST-123", "This is a comment")

            assert "Comment added" in result
            assert "TEST-123" in result

    @pytest.mark.asyncio
    async def test_transition_issue_success(self):
        """成功转换问题状态。"""
        with patch("app.services.jira_client.settings") as mock_settings:
            mock_settings.jira_url = "https://jira.example.com"
            mock_settings.jira_username = "user@example.com"
            mock_settings.jira_password = "password"

            mock_jira = MagicMock()
            mock_jira.transition_issue.return_value = None

            client = JiraClient()
            client._client = mock_jira

            result = await client.transition_issue("TEST-123", "Done")

            assert "transitioned" in result.lower()
            assert "TEST-123" in result
            assert "Done" in result

    def test_extract_text_from_adf_simple(self):
        """从 ADF 格式提取纯文本。"""
        client = JiraClient()

        adf = {
            "type": "doc",
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": "Hello "}]},
                {"type": "paragraph", "content": [{"type": "text", "text": "World"}]}
            ]
        }

        result = client._extract_text_from_adf(adf)
        assert "Hello" in result
        assert "World" in result

    def test_extract_text_from_adf_empty(self):
        """空 ADF 应返回空字符串。"""
        client = JiraClient()

        assert client._extract_text_from_adf(None) == ""
        assert client._extract_text_from_adf({}) == ""