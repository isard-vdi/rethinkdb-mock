#!/usr/bin/env python3
"""
Tests for comparison operators: gte, lte, neq

These tests ensure that the comparison operator classes (Gte, Lte, Neq)
are properly tested and work as expected with various data types.
"""

from __future__ import print_function

from rethinkdb import r
from tests.common import as_db_and_table
from tests.common import assertEqual
from tests.functional.common import MockTest


class TestComparisonOperators(MockTest):
    """Test comparison operators gte (>=), lte (<=), neq (!=)"""

    def get_data(self):
        data = [
            {"id": 1, "value": 10, "name": "Alice", "score": 85.5},
            {"id": 2, "value": 20, "name": "Bob", "score": 92.0},
            {"id": 3, "value": 10, "name": "Charlie", "score": 78.3},
            {"id": 4, "value": 30, "name": "Alice", "score": 65.0},
            {"id": 5, "value": 15, "name": "David", "score": 88.7},
        ]
        return as_db_and_table("test_db", "test", data)

    def test_gte_operator(self, conn):
        """Test >= (greater than or equal) operator"""
        # Test with integers
        result = list(
            r.db("test_db")
            .table("test")
            .filter(lambda doc: doc["value"] >= 20)
            .run(conn)
        )
        assertEqual(len(result), 2)
        expected_ids = {2, 4}
        actual_ids = {item["id"] for item in result}
        assertEqual(actual_ids, expected_ids)

        # Test with floats
        result = list(
            r.db("test_db")
            .table("test")
            .filter(lambda doc: doc["score"] >= 85.0)
            .run(conn)
        )
        assertEqual(len(result), 3)
        expected_ids = {1, 2, 5}
        actual_ids = {item["id"] for item in result}
        assertEqual(actual_ids, expected_ids)

        # Test equality case
        result = list(
            r.db("test_db")
            .table("test")
            .filter(lambda doc: doc["value"] >= 10)
            .run(conn)
        )
        assertEqual(len(result), 5)  # All records have value >= 10

    def test_lte_operator(self, conn):
        """Test <= (less than or equal) operator"""
        # Test with integers
        result = list(
            r.db("test_db")
            .table("test")
            .filter(lambda doc: doc["value"] <= 15)
            .run(conn)
        )
        assertEqual(len(result), 3)
        expected_ids = {1, 3, 5}
        actual_ids = {item["id"] for item in result}
        assertEqual(actual_ids, expected_ids)

        # Test with floats
        result = list(
            r.db("test_db")
            .table("test")
            .filter(lambda doc: doc["score"] <= 80.0)
            .run(conn)
        )
        assertEqual(len(result), 2)
        expected_ids = {3, 4}
        actual_ids = {item["id"] for item in result}
        assertEqual(actual_ids, expected_ids)

        # Test equality case
        result = list(
            r.db("test_db")
            .table("test")
            .filter(lambda doc: doc["value"] <= 10)
            .run(conn)
        )
        assertEqual(len(result), 2)  # id=1,3 have value = 10
        expected_ids = {1, 3}
        actual_ids = {item["id"] for item in result}
        assertEqual(actual_ids, expected_ids)

    def test_neq_operator(self, conn):
        """Test != (not equal) operator"""
        # Test with integers
        result = list(
            r.db("test_db")
            .table("test")
            .filter(lambda doc: doc["value"] != 10)
            .run(conn)
        )
        assertEqual(len(result), 3)
        expected_ids = {2, 4, 5}
        actual_ids = {item["id"] for item in result}
        assertEqual(actual_ids, expected_ids)

        # Test with strings
        result = list(
            r.db("test_db")
            .table("test")
            .filter(lambda doc: doc["name"] != "Alice")
            .run(conn)
        )
        assertEqual(len(result), 3)
        expected_ids = {2, 3, 5}
        actual_ids = {item["id"] for item in result}
        assertEqual(actual_ids, expected_ids)

        # Test with floats
        result = list(
            r.db("test_db")
            .table("test")
            .filter(lambda doc: doc["score"] != 85.5)
            .run(conn)
        )
        assertEqual(len(result), 4)
        expected_ids = {2, 3, 4, 5}
        actual_ids = {item["id"] for item in result}
        assertEqual(actual_ids, expected_ids)

    def test_comparison_with_method_calls(self, conn):
        """Test comparison operators called as methods"""
        # Test .ge() method (gte)
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

        # Test .le() method (lte)
        result = list(
            r.db("test_db")
            .table("test")
            .filter(lambda doc: doc["value"].le(15))
            .run(conn)
        )
        assertEqual(len(result), 3)
        expected_ids = {1, 3, 5}
        actual_ids = {item["id"] for item in result}
        assertEqual(actual_ids, expected_ids)

        # Test .ne() method (neq)
        result = list(
            r.db("test_db")
            .table("test")
            .filter(lambda doc: doc["name"].ne("Alice"))
            .run(conn)
        )
        assertEqual(len(result), 3)
        expected_ids = {2, 3, 5}
        actual_ids = {item["id"] for item in result}
        assertEqual(actual_ids, expected_ids)

    def test_comparison_chaining(self, conn):
        """Test chaining comparison operators"""
        # Test combining >= and <=
        result = list(
            r.db("test_db")
            .table("test")
            .filter(lambda doc: (doc["value"] >= 10) & (doc["value"] <= 20))
            .run(conn)
        )
        assertEqual(len(result), 4)
        expected_ids = {1, 2, 3, 5}
        actual_ids = {item["id"] for item in result}
        assertEqual(actual_ids, expected_ids)

        # Test combining != with other operators
        result = list(
            r.db("test_db")
            .table("test")
            .filter(lambda doc: (doc["name"] != "Alice") & (doc["score"] >= 85))
            .run(conn)
        )
        assertEqual(len(result), 2)
        expected_ids = {2, 5}
        actual_ids = {item["id"] for item in result}
        assertEqual(actual_ids, expected_ids)
