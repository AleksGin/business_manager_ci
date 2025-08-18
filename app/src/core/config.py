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
    echo: bool = False
    echo_pool: bool = False
    max_overflow: int = 10
    pool_size: int = 50

    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@localhost:{self.db_port}/{self.db_name}"


class Auth(BaseModel):
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    refresh_token_expire_days: int


class ApiPrefix(BaseModel):
    user: str = "/api/users"
    auth: str = "/api/auth"


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env.template", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_nested_delimiter="__",
    )
    db_config: DB_Config = Field(..., alias="DB_CONFIG")
    test_db_config: DB_Config = Field(..., alias="TEST_DB_CONFIG")
    auth: Auth
    api_prefix: ApiPrefix = ApiPrefix()
    app_config: AppConfigure = AppConfigure()
    bcrypt_settings: BcryptSettings = BcryptSettings()


settings = Config()
