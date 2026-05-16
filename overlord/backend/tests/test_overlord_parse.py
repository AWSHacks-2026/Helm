import pytest

from overlord_parse import extract_json_object


def test_extract_json_object_plain():
    raw = '{"conflict_type": "merge_conflict", "resolved_code": "x"}'
    assert extract_json_object(raw)["conflict_type"] == "merge_conflict"


def test_extract_json_object_from_markdown_fence():
    raw = """Here is the result:
```json
{"conflict_type": "merge_conflict", "resolved_code": "x"}
```
"""
    assert extract_json_object(raw)["resolved_code"] == "x"


def test_extract_json_object_raises_on_garbage():
    with pytest.raises(ValueError):
        extract_json_object("not json at all")
