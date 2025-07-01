#!/usr/bin/env python3
"""
Tests for specific functions that were flagged as potentially untested
"""

from __future__ import print_function

from rethinkdb import r
from tests.common import as_db_and_table
from tests.common import assertEqual
from tests.common import assertEqUnordered
from tests.functional.common import MockTest


class TestLogicalOperators(MockTest):
    """Test logical operators that use &, |, ~ syntax"""

    def get_data(self):
        data = [
            {"id": 1, "active": True, "score": 85},
            {"id": 2, "active": False, "score": 92},
            {"id": 3, "active": True, "score": 78},
        ]
        return as_db_and_table("test_db", "test", data)

    def test_and_operator(self, conn):
        """Test & logical operator"""
        result = list(
            r.db("test_db")
            .table("test")
            .filter(lambda doc: doc["active"] & (doc["score"] > 80))
            .run(conn)
        )
        assertEqual(len(result), 1)
        assertEqual(result[0]["id"], 1)

    def test_or_operator(self, conn):
        """Test | logical operator"""
        result = list(
            r.db("test_db")
            .table("test")
            .filter(lambda doc: ~doc["active"] | (doc["score"] > 90))
            .run(conn)
        )
        assertEqual(len(result), 1)
        assertEqual(result[0]["id"], 2)

    def test_not_operator(self, conn):
        """Test ~ logical operator"""
        result = list(
            r.db("test_db").table("test").filter(lambda doc: ~doc["active"]).run(conn)
        )
        assertEqual(len(result), 1)
        assertEqual(result[0]["id"], 2)


class TestComparisonOperators(MockTest):
    """Test comparison operators using ==, !=, >=, <= syntax"""

    def get_data(self):
        data = [
            {"id": 1, "value": 5},
            {"id": 2, "value": 10},
            {"id": 3, "value": 5},
        ]
        return as_db_and_table("test_db", "test", data)

    def test_eq_operator(self, conn):
        """Test == comparison operator"""
        result = list(
            r.db("test_db")
            .table("test")
            .filter(lambda doc: doc["value"] == 5)
            .run(conn)
        )
        assertEqual(len(result), 2)
        expected_ids = {1, 3}
        actual_ids = {item["id"] for item in result}
        assertEqual(actual_ids, expected_ids)

    def test_neq_operator(self, conn):
        """Test != comparison operator"""
        result = list(
            r.db("test_db")
            .table("test")
            .filter(lambda doc: doc["value"] != 5)
            .run(conn)
        )
        assertEqual(len(result), 1)
        assertEqual(result[0]["id"], 2)

    def test_gte_operator(self, conn):
        """Test >= comparison operator"""
        result = list(
            r.db("test_db")
            .table("test")
            .filter(lambda doc: doc["value"] >= 10)
            .run(conn)
        )
        assertEqual(len(result), 1)
        assertEqual(result[0]["id"], 2)

    def test_lte_operator(self, conn):
        """Test <= comparison operator"""
        result = list(
            r.db("test_db")
            .table("test")
            .filter(lambda doc: doc["value"] <= 5)
            .run(conn)
        )
        assertEqual(len(result), 2)
        expected_ids = {1, 3}
        actual_ids = {item["id"] for item in result}
        assertEqual(actual_ids, expected_ids)


class TestArrayFunctions(MockTest):
    """Test array functions like nth"""

    def get_data(self):
        data = [
            {"id": 1, "items": [10, 20, 30, 40, 50]},
            {"id": 2, "items": ["a", "b", "c"]},
        ]
        return as_db_and_table("test_db", "test", data)

    def test_nth_function(self, conn):
        """Test nth() array indexing"""
        # Test direct array access
        arr = [1, 2, 3, 4, 5]
        result = r.expr(arr).nth(0).run(conn)
        assertEqual(result, 1)

        result = r.expr(arr).nth(2).run(conn)
        assertEqual(result, 3)

        result = r.expr(arr).nth(-1).run(conn)
        assertEqual(result, 5)

    def test_nth_on_table_data(self, conn):
        """Test nth() on table field arrays"""
        result = r.db("test_db").table("test").get(1)["items"].nth(1).run(conn)
        assertEqual(result, 20)


class TestUtilityFunctions(MockTest):
    """Test utility functions like default, etc."""

    def get_data(self):
        data = [
            {"id": 1, "name": "Alice", "score": None},
            {"id": 2, "name": "Bob", "score": 95},
        ]
        return as_db_and_table("test_db", "test", data)

    def test_default_function(self, conn):
        """Test default() for providing default values"""
        # Test with null value
        result = r.expr(None).default("default_value").run(conn)
        assertEqual(result, "default_value")

        # Test with non-null value
        result = r.expr("actual_value").default("default_value").run(conn)
        assertEqual(result, "actual_value")

        # Test with missing field
        obj = {"a": 1}
        result = r.expr(obj)["b"].default("missing").run(conn)
        assertEqual(result, "missing")


# Functions like uuid, args, match, binary are not implemented in the rewrite layer
# These would need implementation in rql_rewrite.py first


class TestFieldAccess(MockTest):
    """Test field access and row functions"""

    def get_data(self):
        data = [
            {"id": 1, "data": {"nested": "value1"}, "active": True},
            {"id": 2, "data": {"nested": "value2"}, "active": False},
        ]
        return as_db_and_table("test_db", "test", data)

    def test_bracket_access(self, conn):
        """Test bracket notation for field access"""
        obj = {"field": "value", "nested": {"inner": "data"}}

        # Basic field access
        result = r.expr(obj)["field"].run(conn)
        assertEqual(result, "value")

        # Nested field access
        result = r.expr(obj)["nested"]["inner"].run(conn)
        assertEqual(result, "data")

    def test_row_access(self, conn):
        """Test r.row for accessing current row in lambda context"""
        # Test with filter
        result = list(r.db("test_db").table("test").filter(r.row["id"] > 1).run(conn))
        assertEqual(len(result), 1)
        assertEqual(result[0]["id"], 2)

        # Test with map
        result = list(
            r.db("test_db").table("test").map(r.row["data"]["nested"]).run(conn)
        )
        expected = ["value1", "value2"]
        assertEqUnordered(expected, result)


class TestCoercionFunctions(MockTest):
    """Test type coercion functions"""

    def get_data(self):
        return as_db_and_table("test_db", "test", [])

    def test_coerce_to_function(self, conn):
        """Test coerce_to() type conversion"""
        # Number to string
        result = r.expr(42).coerce_to("string").run(conn)
        assertEqual(result, "42")

        # String to number
        result = r.expr("42").coerce_to("number").run(conn)
        assertEqual(result, 42)

        # Float string to number
        result = r.expr("42.5").coerce_to("number").run(conn)
        assertEqual(result, 42.5)

        # Array to object
        arr = [["a", 1], ["b", 2]]
        result = r.expr(arr).coerce_to("object").run(conn)
        assertEqual(result, {"a": 1, "b": 2})


class TestTimezoneFunction(MockTest):
    """Test timezone function"""

    def get_data(self):
        return as_db_and_table("test_db", "test", [])

    def test_timezone_function(self, conn):
        """Test timezone() function"""
        # Test getting timezone from a time object
        time_obj = r.now().run(conn)
        tz = r.expr(time_obj).timezone().run(conn)
        assertEqual(tz, "+00:00")  # UTC timezone


if __name__ == "__main__":
    from tests.fixtures import unittest

    unittest.main()
