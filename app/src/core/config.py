from pathlib import Path
from pydantic import (
    BaseModel,
    Field,
)
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


class BcryptSettings(BaseModel):
    default_rounds_value: int = 12


class AppConfigure(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    reload_mode: bool = True


class DB_Config(BaseModel):
    db_name: str
    db_user: str
    db_password: str
    db_port: int
    db_port_for_host: int
    db_host: str
    echo: bool = False
    echo_pool: bool = False
    max_overflow: int = 10
    pool_size: int = 50

    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


class Auth(BaseModel):
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    refresh_token_expire_days: int
    
class TestUserConfig(BaseModel):
    admin_password: str
    manager_password: str
    employee_password: str


class ApiPrefix(BaseModel):
    user: str = "/api/users"
    auth: str = "/api/auth"

ROOT_DIR = Path(__file__).parent.parent.parent.parent
class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            ROOT_DIR / ".env.template", 
            ROOT_DIR / ".env"
        ),
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_nested_delimiter="__",
    )
    db_config: DB_Config = Field(..., alias="DB_CONFIG")
    test_db_config: DB_Config = Field(..., alias="TEST_DB_CONFIG")
    api_prefix: ApiPrefix = ApiPrefix()
    app_config: AppConfigure = AppConfigure()
    bcrypt_settings: BcryptSettings = BcryptSettings()
    auth: Auth
    test_user_config: TestUserConfig


settings = Config()
