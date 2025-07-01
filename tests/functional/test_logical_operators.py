#!/usr/bin/env python3
"""
Tests for logical operators: and, or, not
These test the logical operators using both Python syntax (&, |, ~) and ReQL syntax
"""

from __future__ import print_function

from rethinkdb import r
from tests.common import as_db_and_table
from tests.common import assertEqual
from tests.common import assertEqUnordered
from tests.functional.common import MockTest


class TestLogicalOperators(MockTest):
    """Test logical operators: and, or, not"""

    def get_data(self):
        data = [
            {"id": 1, "active": True, "score": 85, "premium": False},
            {"id": 2, "active": False, "score": 92, "premium": True},
            {"id": 3, "active": True, "score": 78, "premium": True},
            {"id": 4, "active": False, "score": 65, "premium": False},
        ]
        return as_db_and_table("test_db", "test", data)

    def test_and_operator_python_syntax(self, conn):
        """Test & logical operator (Python syntax)"""
        # Test active AND score > 80
        result = list(
            r.db("test_db")
            .table("test")
            .filter(lambda doc: doc["active"] & (doc["score"] > 80))
            .run(conn)
        )
        assertEqual(len(result), 1)
        assertEqual(result[0]["id"], 1)

    def test_and_operator_reql_method(self, conn):
        """Test .and_() method (ReQL syntax)"""
        # Test active AND premium
        result = list(
            r.db("test_db")
            .table("test")
            .filter(lambda doc: doc["active"].and_(doc["premium"]))
            .run(conn)
        )
        assertEqual(len(result), 1)
        assertEqual(result[0]["id"], 3)

    def test_or_operator_python_syntax(self, conn):
        """Test | logical operator (Python syntax)"""
        # Test not active OR score > 90
        result = list(
            r.db("test_db")
            .table("test")
            .filter(lambda doc: ~doc["active"] | (doc["score"] > 90))
            .run(conn)
        )
        assertEqual(len(result), 2)
        expected_ids = {2, 4}  # id 2 (score 92 > 90), id 4 (not active)
        actual_ids = {item["id"] for item in result}
        assertEqual(actual_ids, expected_ids)

    def test_or_operator_reql_method(self, conn):
        """Test .or_() method (ReQL syntax)"""
        # Test premium OR score > 85
        result = list(
            r.db("test_db")
            .table("test")
            .filter(lambda doc: doc["premium"].or_(doc["score"] > 85))
            .run(conn)
        )
        assertEqual(len(result), 3)
        expected_ids = {2, 3, 1}  # premium: 2,3; score>85: 1,2
        actual_ids = {item["id"] for item in result}
        assertEqual(actual_ids, expected_ids)

    def test_not_operator_python_syntax(self, conn):
        """Test ~ logical operator (Python syntax)"""
        # Test not active
        result = list(
            r.db("test_db").table("test").filter(lambda doc: ~doc["active"]).run(conn)
        )
        assertEqual(len(result), 2)
        expected_ids = {2, 4}
        actual_ids = {item["id"] for item in result}
        assertEqual(actual_ids, expected_ids)

    def test_not_operator_reql_method(self, conn):
        """Test .not_() method (ReQL syntax)"""
        # Test not premium
        result = list(
            r.db("test_db")
            .table("test")
            .filter(lambda doc: doc["premium"].not_())
            .run(conn)
        )
        assertEqual(len(result), 2)
        expected_ids = {1, 4}
        actual_ids = {item["id"] for item in result}
        assertEqual(actual_ids, expected_ids)

    def test_complex_logical_expressions(self, conn):
        """Test complex combinations of logical operators"""
        # Test (active AND premium) OR (not active AND score > 90)
        result = list(
            r.db("test_db")
            .table("test")
            .filter(
                lambda doc: (doc["active"] & doc["premium"])
                | (~doc["active"] & (doc["score"] > 90))
            )
            .run(conn)
        )
        assertEqual(len(result), 2)
        expected_ids = {3, 2}  # id 3 (active & premium), id 2 (not active & score 92)
        actual_ids = {item["id"] for item in result}
        assertEqual(actual_ids, expected_ids)


if __name__ == "__main__":
    from tests.fixtures import unittest

    unittest.main()
