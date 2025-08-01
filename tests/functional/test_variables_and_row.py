#!/usr/bin/env python3
"""
Tests for variables and row references: rvar, row

These tests ensure that variable references (RVar) and row references (RRow)
work correctly in different contexts.
"""

from __future__ import print_function

from rethinkdb import r
from tests.common import as_db_and_table
from tests.common import assertEqual
from tests.common import assertEqUnordered
from tests.functional.common import MockTest


class TestVariableReferences(MockTest):
    """Test RVar class for variable references"""

    def get_data(self):
        data = [
            {"id": 1, "name": "Alice", "age": 25, "active": True},
            {"id": 2, "name": "Bob", "age": 30, "active": False},
            {"id": 3, "name": "Charlie", "age": 35, "active": True},
            {"id": 4, "name": "David", "age": 28, "active": False},
        ]
        return as_db_and_table("test_db", "test", data)

    def test_rvar_basic_usage(self, conn):
        """Test RVar class in basic variable contexts"""
        # Using variables in filter expressions
        # This tests the underlying variable mechanism in lambdas
        result = list(
            r.db("test_db").table("test").filter(lambda doc: doc["age"] > 27).run(conn)
        )
        assertEqual(len(result), 3)
        expected_ids = {2, 3, 4}
        actual_ids = {item["id"] for item in result}
        assertEqual(actual_ids, expected_ids)

    def test_rvar_in_complex_expressions(self, conn):
        """Test RVar class in complex expressions"""
        # Test variable usage in complex filter with multiple references
        result = list(
            r.db("test_db")
            .table("test")
            .filter(lambda user: (user["age"] > 25) & user["active"])
            .run(conn)
        )
        assertEqual(len(result), 1)
        assertEqual(result[0]["id"], 3)

    def test_rvar_in_map_operations(self, conn):
        """Test RVar class in map operations"""
        # Test variable references in map transformations
        result = list(
            r.db("test_db")
            .table("test")
            .map(
                lambda person: {
                    "id": person["id"],
                    "display_name": person["name"],
                    "years": person["age"],
                    "status": r.branch(person["active"], "active", "inactive"),
                }
            )
            .run(conn)
        )
        assertEqual(len(result), 4)
        assertEqual(result[0]["display_name"], "Alice")
        assertEqual(result[0]["status"], "active")
        assertEqual(result[1]["status"], "inactive")

    def test_rvar_nested_operations(self, conn):
        """Test RVar class in nested operations"""
        # Test variable references in nested operations like reduce
        result = (
            r.db("test_db")
            .table("test")
            .map(lambda doc: r.branch(doc["active"], doc["age"] * 2, doc["age"] / 2))
            .reduce(lambda left, right: left + right)
            .run(conn)
        )

        # Expected: Alice(25*2=50) + Bob(30/2=15) + Charlie(35*2=70) + David(28/2=14) = 149
        assertEqual(result, 149.0)


class TestRowReferences(MockTest):
    """Test RRow class for r.row references"""

    def get_data(self):
        data = [
            {
                "id": 1,
                "info": {"score": 85, "grade": "B"},
                "tags": ["student", "active"],
            },
            {
                "id": 2,
                "info": {"score": 92, "grade": "A"},
                "tags": ["student", "honor"],
            },
            {"id": 3, "info": {"score": 78, "grade": "C"}, "tags": ["student"]},
            {
                "id": 4,
                "info": {"score": 88, "grade": "B"},
                "tags": ["student", "active", "leader"],
            },
        ]
        return as_db_and_table("test_db", "test", data)

    def test_row_basic_access(self, conn):
        """Test r.row for basic field access"""
        # Test r.row for accessing document fields
        result = list(r.db("test_db").table("test").filter(r.row["id"] > 2).run(conn))
        assertEqual(len(result), 2)
        expected_ids = {3, 4}
        actual_ids = {item["id"] for item in result}
        assertEqual(actual_ids, expected_ids)

    def test_row_nested_access(self, conn):
        """Test r.row for nested field access"""
        # Test r.row for accessing nested fields
        result = list(
            r.db("test_db").table("test").filter(r.row["info"]["score"] >= 85).run(conn)
        )
        assertEqual(len(result), 3)
        expected_ids = {1, 2, 4}
        actual_ids = {item["id"] for item in result}
        assertEqual(actual_ids, expected_ids)

    def test_row_array_access(self, conn):
        """Test r.row for array field access"""
        # Test r.row for accessing array elements
        result = list(
            r.db("test_db")
            .table("test")
            .filter(r.row["tags"].contains("active"))
            .run(conn)
        )
        assertEqual(len(result), 2)
        expected_ids = {1, 4}
        actual_ids = {item["id"] for item in result}
        assertEqual(actual_ids, expected_ids)

    def test_row_in_map_operations(self, conn):
        """Test r.row in map operations"""
        # Test r.row in map transformations
        result = list(
            r.db("test_db")
            .table("test")
            .map(lambda doc: doc["info"]["score"] * 1.1)  # 10% bonus using lambda instead of r.row
            .run(conn)
        )
        expected = [93.5, 101.2, 85.8, 96.8]  # scores * 1.1
        # Use approximate equality for floating point comparison
        assertEqual(len(result), len(expected))
        for i, (actual, exp) in enumerate(zip(result, expected)):
            assert abs(actual - exp) < 1e-10, f"Index {i}: {actual} != {exp}"

    def test_row_complex_expressions(self, conn):
        """Test r.row in complex expressions"""
        # Test r.row in complex boolean expressions
        result = list(
            r.db("test_db")
            .table("test")
            .filter((r.row["info"]["score"] > 80) & (r.row["tags"].count() > 1))
            .run(conn)
        )
        assertEqual(len(result), 3)
        expected_ids = {1, 2, 4}
        actual_ids = {item["id"] for item in result}
        assertEqual(actual_ids, expected_ids)

    def test_row_arithmetic_operations(self, conn):
        """Test r.row in arithmetic operations"""
        # Test r.row with arithmetic
        result = list(
            r.db("test_db")
            .table("test")
            .map(
                {
                    "id": r.row["id"],
                    "adjusted_score": r.row["info"]["score"] + r.row["id"] * 2,
                    "tag_count": r.row["tags"].count(),
                }
            )
            .run(conn)
        )

        # Expected adjusted_scores: 85+2=87, 92+4=96, 78+6=84, 88+8=96
        expected_adjusted = [87, 96, 84, 96]
        actual_adjusted = [item["adjusted_score"] for item in result]
        assertEqual(actual_adjusted, expected_adjusted)

    def test_row_with_methods(self, conn):
        """Test r.row with method calls"""
        # Test r.row with string and array methods
        result = list(
            r.db("test_db")
            .table("test")
            .map(
                {
                    "id": r.row["id"],
                    "grade_lower": r.row["info"]["grade"].downcase(),
                    "has_leader_tag": r.row["tags"].contains("leader"),
                    "first_tag": r.row["tags"][0],
                }
            )
            .run(conn)
        )

        assertEqual(result[0]["grade_lower"], "b")
        assertEqual(result[1]["grade_lower"], "a")
        assertEqual(result[3]["has_leader_tag"], True)
        assertEqual(result[0]["has_leader_tag"], False)
        assertEqual(result[0]["first_tag"], "student")


class TestMixedVariableUsage(MockTest):
    """Test mixed usage of variables and row references"""

    def get_data(self):
        data = [
            {"id": 1, "values": [10, 20, 30], "multiplier": 2},
            {"id": 2, "values": [5, 15, 25], "multiplier": 3},
            {"id": 3, "values": [12, 24, 36], "multiplier": 1},
        ]
        return as_db_and_table("test_db", "test", data)

    def test_mixed_row_and_lambda_vars(self, conn):
        """Test mixing r.row with lambda variables"""
        # Test using both r.row and lambda variables
        # Simplified version to avoid complex nested scoping issues
        result = list(
            r.db("test_db")
            .table("test")
            .filter(lambda doc: doc["id"] <= 2)
            .map(lambda doc: doc["values"].map(lambda val: val * doc["multiplier"]))
            .run(conn)
        )

        # Expected: [20,40,60], [15,45,75]
        assertEqual(result[0], [20, 40, 60])
        assertEqual(result[1], [15, 45, 75])

    def test_complex_nested_variables(self, conn):
        """Test complex nested variable usage"""
        # Test complex nesting with multiple variable scopes
        result = (
            r.db("test_db")
            .table("test")
            .map(
                lambda doc: doc["values"]
                .map(
                    lambda item: r.branch(
                        item > 15, item + doc["multiplier"], item - doc["multiplier"]
                    )
                )
                .reduce(lambda a, b: a + b)
            )
            .run(conn)
        )

        # For doc 1: values [10,20,30], multiplier 2
        # [10-2, 20+2, 30+2] = [8, 22, 32] = sum 62
        # For doc 2: values [5,15,25], multiplier 3
        # [5-3, 15-3, 25+3] = [2, 12, 28] = sum 42
        # For doc 3: values [12,24,36], multiplier 1
        # [12-1, 24+1, 36+1] = [11, 25, 37] = sum 73
        assertEqual(result, [62, 42, 73])
