import httpx
import pytest

from portal.client import PortalAuthError, PortalClient, PortalNotFound, PortalUnavailable

LOGIN_OK = {"type": "redirect", "status": 303, "location": "/meters"}


def make_client(handler, **kw):
    return PortalClient(email="a@b.c", password="pw", base_url="https://portal.test",
                        transport=httpx.MockTransport(handler), **kw)


def test_logs_in_once_and_reuses_session():
    paths = []

    def handler(request):
        paths.append(request.url.path)
        if request.url.path == "/login":
            return httpx.Response(200, json=LOGIN_OK)
        return httpx.Response(200, json={"data": []})

    c = make_client(handler)
    c.get_json("/portal/meters/search", {"q": "", "page": 1})
    c.get_json("/portal/meters/search", {"q": "", "page": 2})
    assert paths.count("/login") == 1


def test_relogin_and_retry_after_401():
    state = {"logins": 0, "rejected": False}

    def handler(request):
        if request.url.path == "/login":
            state["logins"] += 1
            return httpx.Response(200, json=LOGIN_OK)
        if not state["rejected"]:
            state["rejected"] = True
            return httpx.Response(401, json={"error": "unauthorized"})
        return httpx.Response(200, json={"data": [1]})

    c = make_client(handler)
    assert c.get_json("/x") == {"data": [1]}
    assert state["logins"] == 2


def test_gives_up_if_401_persists():
    def handler(request):
        if request.url.path == "/login":
            return httpx.Response(200, json=LOGIN_OK)
        return httpx.Response(401, json={"error": "unauthorized"})

    with pytest.raises(PortalAuthError):
        make_client(handler).get_json("/x")


def test_bad_login_raises_auth_error():
    def handler(request):
        return httpx.Response(200, json={"type": "failure", "status": 401, "data": "[]"})

    with pytest.raises(PortalAuthError):
        make_client(handler).get_json("/x")


def test_404_becomes_not_found():
    def handler(request):
        if request.url.path == "/login":
            return httpx.Response(200, json=LOGIN_OK)
        return httpx.Response(404, json={"error": "not_found"})

    with pytest.raises(PortalNotFound):
        make_client(handler).get_json("/portal/meters/J999999/geo")


def test_5xx_is_unavailable_after_retries():
    def handler(request):
        if request.url.path == "/login":
            return httpx.Response(200, json=LOGIN_OK)
        return httpx.Response(503)

    with pytest.raises(PortalUnavailable):
        make_client(handler, max_retries=0).get_json("/x")
