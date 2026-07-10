from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    google_sheet_id: str = "1mvKqzfzS7qL69NRg6_6ER_DZdiyUP4LfFYkfCDab9po"
    google_sheet_name: str = "考題_Cloud Practitioner"
    allowed_origins: str = "http://localhost:3000"

    @property
    def allowed_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    model_config = SettingsConfigDict(
        env_file=("../../.env.local", "../../.env", ".env", ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
