import json
from pathlib import Path

import pytest

from portal.decode import devalue_parse, parse_meter_page

FIXTURE = Path(__file__).parent / "fixtures" / "meter_J100001_data.json"


@pytest.fixture
def payload():
    return json.loads(FIXTURE.read_text())


def test_references_are_resolved():
    flat = [{"a": 1, "b": 2}, "x", [1, 1]]
    assert devalue_parse(flat) == {"a": "x", "b": ["x", "x"]}


def test_failed_login_body_decodes():
    # `data` inside a failed login response is itself a JSON string.
    inner = '[{"email":1,"error":2},"operator@urja.local","Invalid email or password."]'
    assert devalue_parse(json.loads(inner)) == {
        "email": "operator@urja.local",
        "error": "Invalid email or password.",
    }


def test_meter_page_nameplate(payload):
    meter = parse_meter_page(payload)
    assert meter["meterId"] == "J100001"
    assert meter["nameplate"] == {
        "Meter ID": "J100001",
        "Serial No": "GE84132",
        "Make": "L&T",
        "Phase Type": "single",
        "Installation Status": "Installed",
        "Installation Type": "CT Operated",
    }


def test_meter_page_hierarchy(payload):
    h = parse_meter_page(payload)["hierarchy"]
    assert h["Zone"] == "Jaipur Zone 2 (Z-02)"
    assert h["Feeder"] == "Feeder 2 (F-002)"
    assert h["DT"] == "Mansarovar DT 2 (DT-002)"
