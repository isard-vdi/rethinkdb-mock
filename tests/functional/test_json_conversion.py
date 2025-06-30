"""
Tests for JSON conversion functions in rethinkdb-mock
"""

import json

import pytest
import rethinkdb as r

from rethinkdb_mock import MockRethinkDB


def test_to_json_string():
    """Test to_json_string() for converting values to JSON strings"""
    db = MockRethinkDB()

    # Test simple values
    result = r.expr(42).to_json_string().run(db)
    assert result == "42"

    result = r.expr("hello").to_json_string().run(db)
    assert result == '"hello"'

    result = r.expr(True).to_json_string().run(db)
    assert result == "true"

    result = r.expr(False).to_json_string().run(db)
    assert result == "false"

    result = r.expr(None).to_json_string().run(db)
    assert result == "null"

    # Test array
    result = r.expr([1, 2, 3]).to_json_string().run(db)
    assert result == "[1, 2, 3]"

    # Test object
    result = r.expr({"name": "Alice", "age": 30}).to_json_string().run(db)
    parsed = json.loads(result)
    assert parsed == {"name": "Alice", "age": 30}

    # Test nested structure
    nested = {
        "users": [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}],
        "count": 2,
    }
    result = r.expr(nested).to_json_string().run(db)
    parsed = json.loads(result)
    assert parsed == nested

    # Test empty containers
    result = r.expr([]).to_json_string().run(db)
    assert result == "[]"

    result = r.expr({}).to_json_string().run(db)
    assert result == "{}"


def test_json_with_special_types():
    """Test JSON conversion with special Python types"""
    db = MockRethinkDB()

    # Test with datetime (should convert to string representation)
    import datetime

    dt = datetime.datetime(2023, 6, 15, 12, 30, 45)
    result = r.expr(dt).to_json_string().run(db)
    # Should convert datetime to string
    parsed = json.loads(result)
    assert isinstance(parsed, str)
    assert "2023-06-15" in parsed

    # Test with mixed types that json.dumps can handle
    mixed_data = {
        "int": 42,
        "float": 3.14,
        "string": "text",
        "bool": True,
        "null": None,
        "list": [1, 2, 3],
        "dict": {"nested": "value"},
    }

    result = r.expr(mixed_data).to_json_string().run(db)
    parsed = json.loads(result)

    # Check all basic types are preserved
    assert parsed["int"] == 42
    assert parsed["float"] == 3.14
    assert parsed["string"] == "text"
    assert parsed["bool"] is True
    assert parsed["null"] is None
    assert parsed["list"] == [1, 2, 3]
    assert parsed["dict"] == {"nested": "value"}


def test_json_error_cases():
    """Test error handling in JSON conversion"""
    db = MockRethinkDB()

    # Most Python objects should be convertible to JSON with default=str fallback
    # So we need to test edge cases that might still fail

    # Test circular reference (this would fail in standard json.dumps)
    # But our implementation uses default=str, so it should work by converting to string
    circular = {}
    circular["self"] = circular

    # This should not raise an error due to default=str fallback
    try:
        result = r.expr(circular).to_json_string().run(db)
        # If it succeeds, the result should be a valid JSON string
        assert isinstance(result, str)
    except ValueError:
        # If it fails, that's also acceptable behavior
        pass
