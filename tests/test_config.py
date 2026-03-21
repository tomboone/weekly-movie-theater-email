from config import Settings


def test_settings_loads_required_fields(monkeypatch):
    monkeypatch.setenv("REGAL_CINEMA_ID", "0985")
    monkeypatch.setenv("TMDB_API_KEY", "test-tmdb-key")

    monkeypatch.setenv("ACS_CONNECTION_STRING", "endpoint=https://test.communication.azure.com/;accesskey=dGVzdA==")
    monkeypatch.setenv("EMAIL_FROM", "from@example.com")
    monkeypatch.setenv("EMAIL_TO", "to@example.com")

    settings = Settings()  # type: ignore[reportCallIssue]
    assert settings.regal_cinema_id == "0985"
    assert settings.tmdb_api_key == "test-tmdb-key"
    assert settings.email_from == "from@example.com"
    assert settings.email_to == "to@example.com"


def test_settings_defaults(monkeypatch):
    monkeypatch.setenv("REGAL_CINEMA_ID", "0985")
    monkeypatch.setenv("TMDB_API_KEY", "test-tmdb-key")

    monkeypatch.setenv("ACS_CONNECTION_STRING", "endpoint=https://test.communication.azure.com/;accesskey=dGVzdA==")
    monkeypatch.setenv("EMAIL_FROM", "from@example.com")
    monkeypatch.setenv("EMAIL_TO", "to@example.com")
    settings = Settings()  # type: ignore[reportCallIssue]
    assert isinstance(settings.exclude_patterns, list)
    assert settings.send_empty_email is False
    assert settings.schedule_cron == "0 10 * * 5"
    assert settings.schedule_timezone == "America/New_York"


def test_settings_exclude_patterns_parsed(monkeypatch):
    monkeypatch.setenv("REGAL_CINEMA_ID", "0985")
    monkeypatch.setenv("TMDB_API_KEY", "k")

    monkeypatch.setenv("ACS_CONNECTION_STRING", "endpoint=https://test.communication.azure.com/;accesskey=dGVzdA==")
    monkeypatch.setenv("EMAIL_FROM", "f@x.com")
    monkeypatch.setenv("EMAIL_TO", "t@x.com")
    monkeypatch.setenv("EXCLUDE_PATTERNS", "Fathom,Special Event")

    settings = Settings()  # type: ignore[reportCallIssue]
    assert settings.exclude_patterns == ["Fathom", "Special Event"]
