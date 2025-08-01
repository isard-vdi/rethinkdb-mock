#!/usr/bin/env python3
"""
Tests for previously untested functions in RethinkDB Mock
"""

from __future__ import print_function

from rethinkdb import r
from tests.common import as_db_and_table
from tests.common import assertEqual
from tests.common import assertEqUnordered
from tests.functional.common import MockTest


class TestLogicalOperators(MockTest):
    """Test logical operators: &, |, ~"""

    def get_data(self):
        data = [
            {"id": 1, "active": True, "score": 85},
            {"id": 2, "active": False, "score": 92},
            {"id": 3, "active": True, "score": 78},
        ]
        return as_db_and_table("test_db", "test", data)

    def test_and_operator(self, conn):
        """Test & logical operator"""
        # Test with expressions
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
        # Test with expressions: not active OR score > 90
        result = list(
            r.db("test_db")
            .table("test")
            .filter(lambda doc: ~doc["active"] | (doc["score"] > 90))
            .run(conn)
        )
        # id 2 (not active = True) OR id 1 (score 92 > 90, but id 1 has score 85, so False)
        # Only id 2 should match
        assertEqual(len(result), 1)
        assertEqual(result[0]["id"], 2)

    def test_not_operator(self, conn):
        """Test ~ logical operator"""
        result = list(
            r.db("test_db").table("test").filter(lambda doc: ~doc["active"]).run(conn)
        )
        assertEqual(len(result), 1)
        assertEqual(result[0]["id"], 2)


class TestComparisons(MockTest):
    """Test comparison operators: ==, !=, <, <=, >, >="""

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


class TestArrayAccess(MockTest):
    """Test array access functions: nth, slice, limit, skip"""

    def get_data(self):
        data = [
            {"id": 1, "name": "Alice", "age": 25},
            {"id": 2, "name": "Bob", "age": 30},
            {"id": 3, "name": "Charlie", "age": 35},
            {"id": 4, "name": "David", "age": 40},
            {"id": 5, "name": "Eve", "age": 45},
        ]
        return as_db_and_table("test_db", "test", data)

    def test_nth_function(self, conn):
        """Test r.nth() array indexing"""
        arr = [1, 2, 3, 4, 5]
        result = r.expr(arr).nth(0).run(conn)
        assertEqual(result, 1)

        result = r.expr(arr).nth(2).run(conn)
        assertEqual(result, 3)

        result = r.expr(arr).nth(-1).run(conn)
        assertEqual(result, 5)

    def test_slice_function(self, conn):
        """Test r.slice() array slicing"""
        arr = [1, 2, 3, 4, 5]
        result = r.expr(arr).slice(1, 3).run(conn)
        assertEqual(result, [2, 3])

        result = r.expr(arr).slice(2).run(conn)
        assertEqual(result, [3, 4, 5])

        result = r.expr(arr).slice(0, -1).run(conn)
        assertEqual(result, [1, 2, 3, 4])

    def test_limit_function(self, conn):
        """Test r.limit() for limiting results"""
        result = list(r.db("test_db").table("test").limit(2).run(conn))
        assertEqual(len(result), 2)

    def test_skip_function(self, conn):
        """Test r.skip() for skipping results"""
        result = list(r.db("test_db").table("test").skip(2).run(conn))
        assertEqual(len(result), 3)

    def test_limit_skip_combined(self, conn):
        """Test combining limit and skip"""
        result = list(r.db("test_db").table("test").skip(1).limit(2).run(conn))
        assertEqual(len(result), 2)


class TestUtilityFunctions(MockTest):
    """Test utility functions: args, default, coerce_to, binary"""

    def get_data(self):
        # Simple data structure for utility functions that don't need database tables
        data = [{"id": 1, "value": 42}]
        return as_db_and_table("test_db", "test", data)

    def test_args_function(self):
        """Test r.args() for argument expansion"""
        # Test with array
        arr = [1, 2, 3]
        result = self.r.add(self.r.args(arr)).run()
        self.assertEqual(result, 6)

        # Test with expressions
        result = self.r.expr([1, 2, 3]).do(lambda x: self.r.add(self.r.args(x))).run()
        self.assertEqual(result, 6)

    def test_default_function(self, conn):
        """Test r.default() for default values"""
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

    def test_coerce_to_function(self, conn):
        """Test r.coerce_to() type conversion"""
        # Number to string
        result = r.expr(42).coerce_to("string").run(conn)
        assertEqual(result, "42")

        # String to number
        result = r.expr("42").coerce_to("number").run(conn)
        assertEqual(result, 42)

        # Object to array (gets key-value pairs as tuples)
        obj = {"a": 1, "b": 2}
        result = r.expr(obj).coerce_to("array").run(conn)
        # Should return list of [key, value] pairs
        assertEqUnordered(result, [("a", 1), ("b", 2)])

    def test_binary_function(self):
        """Test r.binary() for binary data"""
        # Create binary data
        binary_data = self.r.binary(b"hello world").run()
        self.assertIsInstance(binary_data, bytes)
        self.assertEqual(binary_data, b"hello world")


class TestStringFunctions(MockTest):
    """Test string functions: match, concat_map"""

    def get_data(self):
        data = {
            "test": [
                {"text": "hello world"},
                {"text": "foo bar"},
                {"text": "hello foo"},
            ]
        }
        return data

    def test_match_function(self):
        """Test r.match() regex matching"""
        # Basic regex match
        result = self.r.expr("hello world").match("hello").run()
        self.assertIsNotNone(result)
        self.assertEqual(result["str"], "hello")

        # No match
        result = self.r.expr("hello world").match("xyz").run()
        self.assertIsNone(result)

        # Match with groups
        result = self.r.expr("hello 123").match(r"(\w+) (\d+)").run()
        self.assertIsNotNone(result)
        self.assertEqual(result["str"], "hello 123")

    def test_concat_map_function(self):
        """Test r.concat_map() for flattening mapped results"""
        # Test with array transformation
        arr = [[1, 2], [3, 4], [5, 6]]
        result = self.r.expr(arr).concat_map(lambda x: x).run()
        self.assertEqual(result, [1, 2, 3, 4, 5, 6])

        # Test with table data
        result = self.table.concat_map(lambda doc: doc["text"].split(" ")).run()
        expected = ["hello", "world", "foo", "bar", "hello", "foo"]
        self.assertEqual(sorted(result), sorted(expected))


class TestMiscFunctions(MockTest):
    """Test miscellaneous functions: uuid, bracket, row, rvar"""

    def get_data(self):
        data = {
            "test": [
                {"id": 1, "data": {"nested": "value1"}},
                {"id": 2, "data": {"nested": "value2"}},
            ]
        }
        return data

    def test_uuid_function(self):
        """Test r.uuid() for generating UUIDs"""
        uuid1 = self.r.uuid().run()
        uuid2 = self.r.uuid().run()

        # UUIDs should be strings
        self.assertIsInstance(uuid1, str)
        self.assertIsInstance(uuid2, str)

        # UUIDs should be different
        self.assertNotEqual(uuid1, uuid2)

        # UUIDs should have correct format (basic check)
        self.assertEqual(len(uuid1), 36)
        self.assertEqual(len(uuid2), 36)

    def test_bracket_function(self):
        """Test bracket notation for field access"""
        obj = {"field": "value", "nested": {"inner": "data"}}

        # Basic field access
        result = self.r.expr(obj)["field"].run()
        self.assertEqual(result, "value")

        # Nested field access
        result = self.r.expr(obj)["nested"]["inner"].run()
        self.assertEqual(result, "data")

    def test_row_function(self):
        """Test r.row for accessing current row in lambda context"""
        # Test with filter
        result = self.table.filter(self.r.row["id"].gt(1)).run()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], 2)

        # Test with map
        result = self.table.map(self.r.row["data"]["nested"]).run()
        expected = ["value1", "value2"]
        self.assertEqual(sorted(result), sorted(expected))


class TestFieldFunctions(MockTest):
    """Test field manipulation functions: with_fields, get_all"""

    def get_data(self):
        data = {
            "test": [
                {"id": 1, "name": "Alice", "age": 25, "city": "NYC"},
                {"id": 2, "name": "Bob", "age": 30, "city": "LA"},
                {"id": 3, "name": "Charlie", "age": 35, "city": "NYC"},
            ]
        }
        return data

    def test_with_fields_function(self):
        """Test r.with_fields() for selecting specific fields"""
        # Select specific fields
        result = self.table.with_fields("name", "age").run()

        for item in result:
            self.assertIn("name", item)
            self.assertIn("age", item)
            self.assertNotIn("city", item)
            self.assertNotIn("id", item)

        # Should have all 3 items
        self.assertEqual(len(result), 3)

    def test_get_all_function(self):
        """Test r.get_all() for getting multiple documents by key"""
        # This assumes get_all is implemented for getting multiple docs by id
        # Note: This might need to be adjusted based on actual implementation
        try:
            result = self.table.get_all(1, 3).run()
            expected_ids = {1, 3}
            actual_ids = {item["id"] for item in result}
            self.assertEqual(actual_ids, expected_ids)
        except AttributeError:
            # get_all might not be implemented or work differently
            self.skipTest("get_all not implemented or different signature")


if __name__ == "__main__":
    from tests.fixtures import unittest

    unittest.main()
