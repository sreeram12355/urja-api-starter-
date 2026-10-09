# Starter

    python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    python -m pytest

Expected at first: the client tests pass, the decode tests fail with
NotImplementedError. Your first job is to make tests/test_decode.py pass by
writing portal/decode.py.

Credentials come from the environment, never from the repo:

    export URJA_EMAIL=...   URJA_PASSWORD=...

Quick live check once decode works:

    python - <<'PY'
    from portal.client import PortalClient
    with PortalClient() as c:
        print(c.get_json("/portal/meters/search", {"q": "", "page": 1})["total"])
    PY

Next steps, in order:
1. decode.py (you write it)
2. app.py: FastAPI app with GET /meters, GET /meters/{id}, GET /meters/{id}/consumption
3. audit.py: crawl all 403 meters once, save raw responses, report data quality
4. PROTOCOL.md, README.md; FastAPI serves /openapi.json for the spec
