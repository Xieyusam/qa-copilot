from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # LLM 配置
    llm_api_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"

    # Embedding 后端：openai 或 sentence-transformers
    embedding_backend: str = "sentence-transformers"
    embedding_model: str = "all-MiniLM-L6-v2"
    # 独立的 Embedding API 配置（支持接入与 LLM 不同的厂商，如果不填默认使用 LLM 的配置）
    embedding_api_url: str | None = None
    embedding_api_key: str | None = None

    # 存储路径
    chroma_path: str = "./data/chroma"
    sqlite_url: str = "sqlite:///./data/knowledge_base.db"
    file_storage_path: str = "./data/files"

    # 文件上传限制
    max_file_size_mb: int = 50

    # JWT 鉴权配置
    secret_key: str = "supersecretkey_please_change_in_production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Jira 配置
    jira_url: str | None = None
    jira_username: str | None = None  # Jira 用户名（邮箱）
    jira_password: str | None = None  # Jira 密码或 Personal Access Token

    # 飞书配置
    feishu_app_id: str | None = None
    feishu_app_secret: str | None = None
    feishu_app_token: str | None = None
    feishu_enable: bool = False

    # 报表配置
    reports_dir: str = "./data/reports"
    reports_base_url: str = "/reports"

    # 附件配置
    attachments_dir: str = "./data/attachments"
    max_attachment_size: int = 10 * 1024 * 1024  # 10MB
    max_attachments_per_message: int = 5

    # 日志配置
    log_level: str = "INFO"
    log_dir: str = "./logs"
    log_rotation: str = "100 MB"
    log_retention: int = 10
    log_format: str = "json"


settings = Settings()