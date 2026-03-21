from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    regal_cinema_id: str
    tmdb_api_key: str
    acs_connection_string: str
    email_from: str
    email_to: str
    exclude_patterns: list[str] = ["Met Opera", "NT Live", "Bolshoi Ballet", "Fathom", "MARS:"]
    send_empty_email: bool = False
    movie_state_path: str = "/home/data/movie_state.json"
    schedule_cron: str = "0 10 * * 5"
    trigger_api_key: str = ""
    schedule_timezone: str = "America/New_York"

    @field_validator("schedule_cron", mode="after")
    @classmethod
    def validate_cron(cls, v):
        parts = v.split()
        if len(parts) != 5:
            raise ValueError(f"schedule_cron must have 5 parts, got {len(parts)}: '{v}'")
        return v

    @field_validator("exclude_patterns", mode="before")
    @classmethod
    def parse_exclude_patterns(cls, v: object) -> list[str]:
        if isinstance(v, str):
            return [p.strip() for p in v.split(",") if p.strip()]
        return v  # type: ignore[return-value]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: object,
        env_settings: object,
        dotenv_settings: object,
        file_secret_settings: object,
    ) -> tuple[object, ...]:
        from pydantic_settings.sources.providers.dotenv import DotEnvSettingsSource
        from pydantic_settings.sources.providers.env import EnvSettingsSource

        # Mixin that treats exclude_patterns as a plain string (not JSON)
        # so our field_validator can handle comma-splitting.
        class _PassthroughExcludePatterns:
            def decode_complex_value(self, field_name: str, field: object, value: object) -> object:
                if field_name == "exclude_patterns" and isinstance(value, str):
                    return value
                return super().decode_complex_value(field_name, field, value)  # type: ignore[reportAttributeAccessIssue]

        class _CustomEnvSource(_PassthroughExcludePatterns, EnvSettingsSource):
            pass

        class _CustomDotEnvSource(_PassthroughExcludePatterns, DotEnvSettingsSource):
            pass

        custom_env = _CustomEnvSource(settings_cls)
        custom_dotenv = _CustomDotEnvSource(settings_cls, env_file=cls.model_config.get("env_file", ".env"))
        return (init_settings, custom_env, custom_dotenv, file_secret_settings)
