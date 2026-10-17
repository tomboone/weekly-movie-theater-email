import httpx
import respx

from monitor import kuma_push

PUSH = "http://uptime-kuma:3001/api/push/abc123"


@respx.mock
async def test_push_sends_status_msg_and_ping():
    route = respx.get(PUSH).mock(return_value=httpx.Response(200, json={"ok": True}))
    await kuma_push(PUSH, "up", "OK", 1234)
    assert route.called
    params = route.calls.last.request.url.params
    assert params["status"] == "up"
    assert params["msg"] == "OK"
    assert params["ping"] == "1234"


@respx.mock
async def test_push_replaces_kumas_default_query():
    """A URL pasted from Kuma carries ?status=up&msg=OK&ping=; ours must replace it, not append."""
    route = respx.get(PUSH).mock(return_value=httpx.Response(200, json={"ok": True}))
    await kuma_push(f"{PUSH}?status=up&msg=OK&ping=", "down", "boom")
    params = route.calls.last.request.url.params
    assert params.get_list("status") == ["down"]
    assert params["msg"] == "boom"
    assert "ping" not in params


@respx.mock
async def test_push_skipped_when_url_empty():
    route = respx.get(PUSH)
    await kuma_push("", "up", "OK")
    assert not route.called


@respx.mock
async def test_push_failure_does_not_raise():
    respx.get(PUSH).mock(side_effect=httpx.ConnectError("refused"))
    await kuma_push(PUSH, "up", "OK")  # must not raise


@respx.mock
async def test_push_http_error_does_not_raise():
    respx.get(PUSH).mock(return_value=httpx.Response(404, json={"ok": False, "msg": "Monitor not found"}))
    await kuma_push(PUSH, "up", "OK")  # must not raise


@respx.mock
async def test_push_truncates_long_message():
    route = respx.get(PUSH).mock(return_value=httpx.Response(200, json={"ok": True}))
    await kuma_push(PUSH, "down", "x" * 500)
    assert len(route.calls.last.request.url.params["msg"]) == 200
