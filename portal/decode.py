"""Decoder for the portal's SvelteKit data (`/meters/{id}/__data.json`).

YOUR TASK. The tests in tests/test_decode.py describe what is expected.

How the format works (this is SvelteKit's "devalue"; you saw it in the
failed-login body too):
  * `data` is one flat list.
  * Item 0 is the root.
  * Inside lists and dicts, every number is NOT a value; it is the index of
    another item in the flat list that holds the real value.
  * The same string can be referenced from several places.

Things to think about:
  * Recursion: resolve an index by looking at flat[index]; if that is a list
    or dict, resolve each of its children the same way.
  * Plain strings, numbers, booleans and None at flat[index] are values.
  * Negative numbers are special markers in devalue (-1 = undefined, etc.).
    This data may never use them; decide whether to raise or ignore, and say
    which in PROTOCOL.md.
  * `nodes` in __data.json is a list; do not hard-code which node holds the
    page data. Find it by what it contains.
"""

HIERARCHY_KEYS = ["Zone", "Circle", "Division", "Subdivision",
                  "Sub Station", "Feeder", "DT"]


def devalue_parse(flat):
    """Turn the flat reference list into ordinary nested Python data."""
    raise NotImplementedError("write me (see docstring and tests)")


def parse_meter_page(payload):
    """Take the parsed JSON of /meters/{id}/__data.json.

    Return {"meterId": str, "nameplate": {name: value}, "hierarchy": {...}}.
    """
    raise NotImplementedError("write me (see tests)")
