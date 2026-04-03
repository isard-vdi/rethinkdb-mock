#!/usr/bin/env python3
"""
Tests for additional untested functions - Part 2
"""

from __future__ import print_function

from rethinkdb import r
from tests.common import as_db_and_table
from tests.common import assertEqual
from tests.common import assertEqUnordered
from tests.functional.common import MockTest


class TestLogicalMethodOperators(MockTest):
    """Test logical operators as methods: and_(), or_(), not_()"""

    def get_data(self):
        data = [
            {"id": 1, "active": True, "score": 85, "verified": True},
            {"id": 2, "active": False, "score": 92, "verified": True},
            {"id": 3, "active": True, "score": 78, "verified": False},
            {"id": 4, "active": False, "score": 65, "verified": False},
        ]
        return as_db_and_table("test_db", "test", data)

    def test_and_method(self, conn):
        """Test .and_() method for logical AND"""
        # Test with boolean fields
        result = list(
            r.db("test_db")
            .table("test")
            .filter(lambda doc: doc["active"].and_(doc["verified"]))
            .run(conn)
        )
        assertEqual(len(result), 1)
        assertEqual(result[0]["id"], 1)

        # Test with expressions
        result = list(
            r.db("test_db")
            .table("test")
            .filter(lambda doc: doc["score"].gt(80).and_(doc["verified"]))
            .run(conn)
        )
        assertEqual(len(result), 2)
        expected_ids = {1, 2}
        actual_ids = {item["id"] for item in result}
        assertEqual(actual_ids, expected_ids)

    def test_or_method(self, conn):
        """Test .or_() method for logical OR"""
        # Test with boolean fields
        result = list(
            r.db("test_db")
            .table("test")
            .filter(lambda doc: doc["active"].or_(doc["verified"]))
            .run(conn)
        )
        assertEqual(len(result), 3)  # All except id=4
        expected_ids = {1, 2, 3}
        actual_ids = {item["id"] for item in result}
        assertEqual(actual_ids, expected_ids)

        # Test with expressions
        result = list(
            r.db("test_db")
            .table("test")
            .filter(lambda doc: doc["score"].gt(90).or_(doc["active"]))
            .run(conn)
        )
        assertEqual(len(result), 3)  # id=1,3 (active) + id=2 (score>90)
        expected_ids = {1, 2, 3}
        actual_ids = {item["id"] for item in result}
        assertEqual(actual_ids, expected_ids)

    def test_not_method(self, conn):
        """Test .not_() method for logical NOT"""
        # Test with boolean field
        result = list(
            r.db("test_db")
            .table("test")
            .filter(lambda doc: doc["active"].not_())
            .run(conn)
        )
        assertEqual(len(result), 2)
        expected_ids = {2, 4}
        actual_ids = {item["id"] for item in result}
        assertEqual(actual_ids, expected_ids)

        # Test with expression
        result = list(
            r.db("test_db")
            .table("test")
            .filter(lambda doc: doc["score"].gt(80).not_())
            .run(conn)
        )
        assertEqual(len(result), 2)  # id=3,4 have scores <= 80
        expected_ids = {3, 4}
        actual_ids = {item["id"] for item in result}
        assertEqual(actual_ids, expected_ids)


class TestComparisonMethods(MockTest):
    """Test comparison operators as methods: eq(), ne(), ge(), le()"""

    def get_data(self):
        data = [
            {"id": 1, "value": 10, "name": "Alice"},
            {"id": 2, "value": 20, "name": "Bob"},
            {"id": 3, "value": 10, "name": "Charlie"},
            {"id": 4, "value": 30, "name": "Alice"},
        ]
        return as_db_and_table("test_db", "test", data)

    def test_eq_method(self, conn):
        """Test .eq() method for equality"""
        # Test with numbers
        result = list(
            r.db("test_db")
            .table("test")
            .filter(lambda doc: doc["value"].eq(10))
            .run(conn)
        )
        assertEqual(len(result), 2)
        expected_ids = {1, 3}
        actual_ids = {item["id"] for item in result}
        assertEqual(actual_ids, expected_ids)

        # Test with strings
        result = list(
            r.db("test_db")
            .table("test")
            .filter(lambda doc: doc["name"].eq("Alice"))
            .run(conn)
        )
        assertEqual(len(result), 2)
        expected_ids = {1, 4}
        actual_ids = {item["id"] for item in result}
        assertEqual(actual_ids, expected_ids)

    def test_ne_method(self, conn):
        """Test .ne() method for inequality"""
        result = list(
            r.db("test_db")
            .table("test")
            .filter(lambda doc: doc["value"].ne(10))
            .run(conn)
        )
        assertEqual(len(result), 2)
        expected_ids = {2, 4}
        actual_ids = {item["id"] for item in result}
        assertEqual(actual_ids, expected_ids)

    def test_ge_method(self, conn):
        """Test .ge() method for greater than or equal"""
        result = list(
            r.db("test_db")
            .table("test")
            .filter(lambda doc: doc["value"].ge(20))
            .run(conn)
        )
        assertEqual(len(result), 2)
        expected_ids = {2, 4}
        actual_ids = {item["id"] for item in result}
        assertEqual(actual_ids, expected_ids)

    def test_le_method(self, conn):
        """Test .le() method for less than or equal"""
        result = list(
            r.db("test_db")
            .table("test")
            .filter(lambda doc: doc["value"].le(10))
            .run(conn)
        )
        assertEqual(len(result), 2)
        expected_ids = {1, 3}
        actual_ids = {item["id"] for item in result}
        assertEqual(actual_ids, expected_ids)


class TestArrayDifference(MockTest):
    """Test difference() array operation"""

    def get_data(self):
        data = [
            {"id": 1, "tags": ["red", "blue", "green"], "nums": [1, 2, 3, 4, 5]},
            {"id": 2, "tags": ["blue", "yellow"], "nums": [3, 4, 5, 6, 7]},
            {"id": 3, "tags": ["red", "yellow", "purple"], "nums": [1, 3, 5, 7, 9]},
        ]
        return as_db_and_table("test_db", "test", data)

    def test_difference_arrays(self, conn):
        """Test difference() between arrays"""
        # Test basic array difference
        arr1 = [1, 2, 3, 4, 5]
        arr2 = [3, 4, 5, 6, 7]
        result = r.expr(arr1).difference(arr2).run(conn)
        assertEqual(sorted(result), [1, 2])

        # Test with string arrays
        arr3 = ["red", "blue", "green"]
        arr4 = ["blue", "yellow"]
        result = r.expr(arr3).difference(arr4).run(conn)
        assertEqual(sorted(result), ["green", "red"])

    def test_difference_on_table_data(self, conn):
        """Test difference() on table field arrays"""
        # Test difference with a specific array
        subtract_tags = ["blue", "yellow"]
        result = list(
            r.db("test_db")
            .table("test")
            .map(lambda doc: doc["tags"].difference(subtract_tags))
            .run(conn)
        )

        # Check that we get the expected results
        assertEqual(len(result), 3)
        # First row: ["red", "blue", "green"] - ["blue", "yellow"] = ["red", "green"]
        # Second row: ["blue", "yellow"] - ["blue", "yellow"] = []
        # Third row: ["red", "yellow", "purple"] - ["blue", "yellow"] = ["red", "purple"]

        # Verify the content (order might vary)
        assertEqUnordered(result[0], ["red", "green"])
        assertEqual(result[1], [])
        assertEqUnordered(result[2], ["red", "purple"])


class TestForEach(MockTest):
    """Test for_each() iteration function"""

    def get_data(self):
        data = [
            {"id": 1, "items": [1, 2, 3]},
            {"id": 2, "items": [4, 5, 6]},
        ]
        return as_db_and_table("test_db", "test", data)

    def test_for_each_function(self, conn):
        """Test for_each() for iterating over sequences"""
        # Test for_each with an array
        arr = [1, 2, 3]
        result = r.expr(arr).for_each(lambda x: r.expr([x, x * 2])).run(conn)
        # for_each should flatten the results
        assertEqual(result, [1, 2, 2, 4, 3, 6])

        # Test for_each with table data
        result = list(
            r.db("test_db").table("test").for_each(lambda doc: doc["items"]).run(conn)
        )
        # Should flatten all items arrays
        assertEqual(sorted(result), [1, 2, 3, 4, 5, 6])


class TestRowAndBracket(MockTest):
    """Test row reference and bracket access"""

    def get_data(self):
        data = [
            {"id": 1, "info": {"name": "Alice", "details": {"age": 25, "city": "NYC"}}},
            {"id": 2, "info": {"name": "Bob", "details": {"age": 30, "city": "LA"}}},
            {
                "id": 3,
                "info": {"name": "Charlie", "details": {"age": 35, "city": "Chicago"}},
            },
        ]
        return as_db_and_table("test_db", "test", data)

    def test_row_reference(self, conn):
        """Test r.row for accessing current document"""
        # Test r.row with field access
        result = list(r.db("test_db").table("test").filter(r.row["id"] > 1).run(conn))
        assertEqual(len(result), 2)
        expected_ids = {2, 3}
        actual_ids = {item["id"] for item in result}
        assertEqual(actual_ids, expected_ids)

        # Test r.row with nested access
        result = list(
            r.db("test_db").table("test").map(r.row["info"]["name"]).run(conn)
        )
        expected_names = ["Alice", "Bob", "Charlie"]
        assertEqUnordered(result, expected_names)

    def test_bracket_access_nested(self, conn):
        """Test bracket notation for deep nested access"""
        # Test deep bracket access
        result = list(
            r.db("test_db")
            .table("test")
            .map(lambda doc: doc["info"]["details"]["city"])
            .run(conn)
        )
        expected_cities = ["NYC", "LA", "Chicago"]
        assertEqUnordered(result, expected_cities)

        # Test bracket access with computation
        result = list(
            r.db("test_db")
            .table("test")
            .filter(lambda doc: doc["info"]["details"]["age"] >= 30)
            .run(conn)
        )
        assertEqual(len(result), 2)
        expected_ids = {2, 3}
        actual_ids = {item["id"] for item in result}
        assertEqual(actual_ids, expected_ids)


class TestGetAll(MockTest):
    """Test get_all() function for multiple document retrieval"""

    def get_data(self):
        data = [
            {"id": 1, "category": "A", "value": 10},
            {"id": 2, "category": "B", "value": 20},
            {"id": 3, "category": "A", "value": 30},
            {"id": 4, "category": "C", "value": 40},
            {"id": 5, "category": "B", "value": 50},
        ]
        return as_db_and_table("test_db", "test", data)

    def test_get_all_by_id(self, conn):
        """Test get_all() by primary key (id)"""
        # Test getting multiple documents by id
        result = list(r.db("test_db").table("test").get_all(1, 3, 5).run(conn))
        assertEqual(len(result), 3)
        expected_ids = {1, 3, 5}
        actual_ids = {item["id"] for item in result}
        assertEqual(actual_ids, expected_ids)

        # Test getting single document (should still return array)
        result = list(r.db("test_db").table("test").get_all(2).run(conn))
        assertEqual(len(result), 1)
        assertEqual(result[0]["id"], 2)


class TestGetAllWithArgs(MockTest):
    """Test get_all() with r.args() for dynamic key expansion"""

    def get_data(self):
        data = [
            {"id": "a", "name": "Alice"},
            {"id": "b", "name": "Bob"},
            {"id": "c", "name": "Charlie"},
            {"id": "d", "name": "Diana"},
        ]
        return as_db_and_table("test_db", "test", data)

    def test_get_all_with_args_by_id(self, conn):
        """r.args() expands a list into get_all arguments"""
        ids = ["a", "c"]
        result = list(r.db("test_db").table("test").get_all(r.args(ids)).run(conn))
        assertEqual(len(result), 2)
        actual_ids = {item["id"] for item in result}
        assertEqual(actual_ids, {"a", "c"})

    def test_get_all_with_args_by_index(self, conn):
        """r.args() works with secondary indexes"""
        r.db("test_db").table("test").index_create("name").run(conn)
        r.db("test_db").table("test").index_wait("name").run(conn)

        names = ["Alice", "Diana"]
        result = list(
            r.db("test_db").table("test").get_all(r.args(names), index="name").run(conn)
        )
        assertEqual(len(result), 2)
        actual_names = {item["name"] for item in result}
        assertEqual(actual_names, {"Alice", "Diana"})

    def test_get_all_with_args_empty(self, conn):
        """r.args() with empty list returns no results"""
        result = list(r.db("test_db").table("test").get_all(r.args([])).run(conn))
        assertEqual(len(result), 0)


class TestHasFieldsNested(MockTest):
    """Test has_fields() with nested dict specs"""

    def get_data(self):
        data = [
            {"id": 1, "a": {"b": {"c": 1}}, "name": "has_nested"},
            {"id": 2, "a": {"b": {}}, "name": "missing_c"},
            {"id": 3, "a": {}, "name": "missing_b"},
            {"id": 4, "name": "missing_a"},
        ]
        return as_db_and_table("test_db", "test", data)

    def test_has_fields_nested_true(self, conn):
        """has_fields with nested dict True spec"""
        result = list(
            r.db("test_db")
            .table("test")
            .has_fields({"a": {"b": {"c": True}}})
            .run(conn)
        )
        assertEqual(len(result), 1)
        assertEqual(result[0]["id"], 1)

    def test_has_fields_nested_partial(self, conn):
        """has_fields with partial nesting"""
        result = list(
            r.db("test_db").table("test").has_fields({"a": {"b": True}}).run(conn)
        )
        assertEqual(len(result), 2)
        actual_ids = {item["id"] for item in result}
        assertEqual(actual_ids, {1, 2})

    def test_has_fields_mixed(self, conn):
        """has_fields with both string and nested dict"""
        result = list(
            r.db("test_db").table("test").has_fields("name", {"a": True}).run(conn)
        )
        assertEqual(len(result), 3)


class TestWithoutNested(MockTest):
    """Test without() with nested dict specs"""

    def get_data(self):
        data = [
            {"id": 1, "a": {"b": 1, "c": 2}, "name": "test"},
        ]
        return as_db_and_table("test_db", "test", data)

    def test_without_nested_field(self, conn):
        """without with nested dict removes only specified nested field"""
        result = list(
            r.db("test_db").table("test").without({"a": {"b": True}}).run(conn)
        )
        assertEqual(len(result), 1)
        assertEqual(result[0]["a"], {"c": 2})
        assertEqual(result[0]["name"], "test")


if __name__ == "__main__":
    from tests.fixtures import unittest

    unittest.main()
