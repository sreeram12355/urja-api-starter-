"""Session-managed client for the Urja Meter Ops portal.

Behaviour is based on what was observed (document it in PROTOCOL.md):
  * POST /login, form fields email+password, with Origin and
    x-sveltekit-action headers. HTTP 200 either way; the JSON body's "type"
    is "redirect" on success and "failure" on a bad login.
  * Session cookie lasts 1 hour and is NOT refreshed by use.
  * Calls without a valid session return 401 JSON.
  * Unknown meters return 404 JSON.
"""
import json
import os
import threading
import time

import httpx

from .decode import devalue_parse

DEFAULT_BASE_URL = "https://urja-ops.flockenergy.tech"
SESSION_TTL = 3600          # seconds, from Max-Age
REFRESH_MARGIN = 600        # re-login this long before expiry


class PortalError(Exception):
    """Base class for everything this client raises."""


class PortalAuthError(PortalError):
    """Login failed, or the session was rejected even after re-login."""


class PortalNotFound(PortalError):
    """The portal answered 404 (e.g. unknown meter id)."""


class PortalUnavailable(PortalError):
    """Network problem or 5xx that survived the retries."""


class PortalClient:
    def __init__(self, email=None, password=None, base_url=None,
                 timeout=15.0, max_retries=2, transport=None):
        self.email = email or os.environ["URJA_EMAIL"]
        self.password = password or os.environ["URJA_PASSWORD"]
        self.base_url = base_url or os.environ.get("URJA_BASE_URL", DEFAULT_BASE_URL)
        self.max_retries = max_retries
        self._http = httpx.Client(base_url=self.base_url, timeout=timeout,
                                  transport=transport)
        self._lock = threading.RLock()
        self._logged_in_at = None   # time.monotonic() of the last login

    # -- lifecycle ---------------------------------------------------------
    def close(self):
        self._http.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # -- public ------------------------------------------------------------
    def get_json(self, path, params=None):
        return self._request(path, params).json()

    def get_text(self, path, params=None):
        return self._request(path, params).text

    # -- session -----------------------------------------------------------
    def _session_is_stale(self):
        if self._logged_in_at is None:
            return True
        return time.monotonic() - self._logged_in_at > SESSION_TTL - REFRESH_MARGIN

    def _ensure_session(self):
        with self._lock:
            if self._session_is_stale():
                self._login()

    def _relogin_if_unchanged(self, seen_login_time):
        """After a 401: log in again, unless another thread already did."""
        with self._lock:
            if self._logged_in_at == seen_login_time:
                self._login()

    def _login(self):
        with self._lock:
            self._http.cookies.clear()
            try:
                r = self._http.post(
                    "/login",
                    data={"email": self.email, "password": self.password},
                    headers={"Accept": "application/json",
                             "Origin": self.base_url,
                             "x-sveltekit-action": "true"},
                )
            except httpx.TransportError as exc:
                raise PortalUnavailable(f"login request failed: {exc}") from exc
            try:
                body = r.json()
            except ValueError:
                raise PortalAuthError(f"login returned non-JSON (HTTP {r.status_code})")
            if body.get("type") != "redirect":
                raise PortalAuthError(f"login failed: {self._login_message(body)}")
            self._logged_in_at = time.monotonic()

    @staticmethod
    def _login_message(body):
        """Failure bodies carry a devalue-encoded string in 'data'."""
        try:
            return devalue_parse(json.loads(body["data"]))["error"]
        except Exception:
            return str(body)[:200]

    # -- requests ----------------------------------------------------------
    def _request(self, path, params=None):
        self._ensure_session()
        relogged = False
        attempt = 0
        while True:
            seen_login_time = self._logged_in_at
            try:
                r = self._http.get(path, params=params)
            except httpx.TransportError as exc:
                if attempt >= self.max_retries:
                    raise PortalUnavailable(f"GET {path} failed: {exc}") from exc
                self._backoff(attempt)
                attempt += 1
                continue

            if r.status_code == 401:
                if relogged:
                    raise PortalAuthError("still unauthorized after re-login")
                self._relogin_if_unchanged(seen_login_time)
                relogged = True
                continue
            if r.status_code == 404:
                raise PortalNotFound(f"GET {path}: not found")
            if r.status_code >= 500:
                if attempt >= self.max_retries:
                    raise PortalUnavailable(f"GET {path}: HTTP {r.status_code}")
                self._backoff(attempt)
                attempt += 1
                continue
            r.raise_for_status()
            return r

    @staticmethod
    def _backoff(attempt):
        time.sleep(0.5 * (2 ** attempt))
