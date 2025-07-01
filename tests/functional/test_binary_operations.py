#!/usr/bin/env python3
"""
Tests for binary operations and array access: binop, bracket, getall

These tests ensure that binary operations, bracket notation for field access,
and get_all operations work correctly.
"""

from __future__ import print_function

from rethinkdb import r
from tests.common import as_db_and_table
from tests.common import assertEqual
from tests.common import assertEqUnordered
from tests.functional.common import MockTest


class TestBinaryOperations(MockTest):
    """Test binary operations (BinOp) and related functionality"""

    def get_data(self):
        data = [
            {"id": 1, "values": [10, 20, 30], "info": {"score": 85, "rank": 1}},
            {"id": 2, "values": [15, 25, 35], "info": {"score": 92, "rank": 2}},
            {"id": 3, "values": [5, 15, 25], "info": {"score": 78, "rank": 3}},
            {"id": 4, "values": [20, 30, 40], "info": {"score": 88, "rank": 1}},
        ]
        return as_db_and_table("test_db", "test", data)

    def test_binop_add_operation(self, conn):
        """Test BinOp class with addition operations"""
        # Test adding numbers from different fields
        result = list(
            r.db("test_db")
            .table("test")
            .map(lambda doc: doc["id"] + doc["info"]["rank"])
            .run(conn)
        )
        assertEqual(result, [2, 4, 6, 5])  # id + rank for each doc

    def test_binop_subtract_operation(self, conn):
        """Test BinOp class with subtraction operations"""
        result = list(
            r.db("test_db")
            .table("test")
            .map(lambda doc: doc["info"]["score"] - doc["id"])
            .run(conn)
        )
        assertEqual(result, [84, 90, 75, 84])  # score - id for each doc

    def test_binop_multiply_operation(self, conn):
        """Test BinOp class with multiplication operations"""
        result = list(
            r.db("test_db")
            .table("test")
            .map(lambda doc: doc["id"] * doc["info"]["rank"])
            .run(conn)
        )
        assertEqual(result, [1, 4, 9, 4])  # id * rank for each doc

    def test_binop_divide_operation(self, conn):
        """Test BinOp class with division operations"""
        result = list(
            r.db("test_db")
            .table("test")
            .filter(lambda doc: doc["id"] > 1)
            .map(lambda doc: doc["info"]["score"] / doc["id"])
            .run(conn)
        )
        expected = [92.0 / 2, 78.0 / 3, 88.0 / 4]  # score / id for docs where id > 1
        assertEqual(result, expected)


class TestBracketAccess(MockTest):
    """Test Bracket class for field and array access"""

    def get_data(self):
        data = [
            {
                "id": 1,
                "values": [10, 20, 30],
                "info": {"score": 85, "details": {"age": 25}},
            },
            {
                "id": 2,
                "values": [15, 25, 35],
                "info": {"score": 92, "details": {"age": 30}},
            },
            {
                "id": 3,
                "values": [5, 15, 25],
                "info": {"score": 78, "details": {"age": 35}},
            },
            {"id": 4, "values": [], "info": {"score": 88}},  # Missing details
        ]
        return as_db_and_table("test_db", "test", data)

    def test_bracket_field_access(self, conn):
        """Test Bracket class for object field access using [] notation"""
        # Test basic field access
        result = list(
            r.db("test_db").table("test").map(lambda doc: doc["id"]).run(conn)
        )
        assertEqual(result, [1, 2, 3, 4])

        # Test nested field access
        result = list(
            r.db("test_db")
            .table("test")
            .map(lambda doc: doc["info"]["score"])
            .run(conn)
        )
        assertEqual(result, [85, 92, 78, 88])

    def test_bracket_array_access(self, conn):
        """Test Bracket class for array element access"""
        # Test accessing array elements by index
        result = list(
            r.db("test_db")
            .table("test")
            .filter(lambda doc: doc["values"].count() > 0)
            .map(lambda doc: doc["values"][0])
            .run(conn)
        )
        assertEqual(result, [10, 15, 5])

        # Test accessing second element
        result = list(
            r.db("test_db")
            .table("test")
            .filter(lambda doc: doc["values"].count() > 1)
            .map(lambda doc: doc["values"][1])
            .run(conn)
        )
        assertEqual(result, [20, 25, 15])

    def test_bracket_missing_fields(self, conn):
        """Test Bracket class behavior with missing fields"""
        # Test accessing missing nested field (should return None)
        result = list(
            r.db("test_db")
            .table("test")
            .map(lambda doc: doc["info"].get_field("details").default(None))
            .run(conn)
        )
        # First 3 docs have details, last one doesn't
        assertEqual(len([x for x in result if x is not None]), 3)
        assertEqual(result[3], None)

    def test_bracket_deep_nesting(self, conn):
        """Test Bracket class with deeply nested field access"""
        result = list(
            r.db("test_db")
            .table("test")
            .filter(lambda doc: doc["info"].has_fields("details"))
            .map(lambda doc: doc["info"]["details"]["age"])
            .run(conn)
        )
        assertEqual(result, [25, 30, 35])


class TestGetAllOperation(MockTest):
    """Test GetAll class functionality"""

    def get_data(self):
        data = [
            {"id": 1, "category": "A", "value": 10},
            {"id": 2, "category": "B", "value": 20},
            {"id": 3, "category": "A", "value": 30},
            {"id": 4, "category": "C", "value": 40},
            {"id": 5, "category": "B", "value": 50},
        ]
        return as_db_and_table("test_db", "test", data)

    def test_getall_single_key(self, conn):
        """Test GetAll class with single key lookup"""
        # Test getting document by single primary key
        result = list(r.db("test_db").table("test").get_all(1).run(conn))
        assertEqual(len(result), 1)
        assertEqual(result[0]["id"], 1)
        assertEqual(result[0]["value"], 10)

    def test_getall_multiple_keys(self, conn):
        """Test GetAll class with multiple key lookup"""
        # Test getting documents by multiple primary keys
        result = list(r.db("test_db").table("test").get_all(1, 3, 5).run(conn))
        assertEqual(len(result), 3)
        expected_ids = {1, 3, 5}
        actual_ids = {item["id"] for item in result}
        assertEqual(actual_ids, expected_ids)

    def test_getall_nonexistent_keys(self, conn):
        """Test GetAll class with non-existent keys"""
        # Test getting documents with non-existent keys
        result = list(r.db("test_db").table("test").get_all(99, 100).run(conn))
        assertEqual(len(result), 0)

    def test_getall_mixed_keys(self, conn):
        """Test GetAll class with mix of existing and non-existent keys"""
        # Test getting documents with mix of existing and non-existent keys
        result = list(r.db("test_db").table("test").get_all(1, 99, 3).run(conn))
        assertEqual(len(result), 2)
        expected_ids = {1, 3}
        actual_ids = {item["id"] for item in result}
        assertEqual(actual_ids, expected_ids)

    def test_getall_with_index(self, conn):
        """Test GetAll class with secondary index"""
        # First create a secondary index
        r.db("test_db").table("test").index_create("category").run(conn)
        r.db("test_db").table("test").index_wait("category").run(conn)

        # Test getting documents by secondary index
        result = list(
            r.db("test_db").table("test").get_all("A", index="category").run(conn)
        )
        assertEqual(len(result), 2)
        expected_ids = {1, 3}
        actual_ids = {item["id"] for item in result}
        assertEqual(actual_ids, expected_ids)

        # Test multiple values on secondary index
        result = list(
            r.db("test_db").table("test").get_all("A", "B", index="category").run(conn)
        )
        assertEqual(len(result), 4)
        expected_ids = {1, 2, 3, 5}
        actual_ids = {item["id"] for item in result}
        assertEqual(actual_ids, expected_ids)
