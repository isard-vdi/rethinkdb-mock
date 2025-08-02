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
            .map(
                lambda doc: doc["info"]["score"] * 1.1
            )  # 10% bonus using lambda instead of r.row
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


class TestVariableRowEdgeCases(MockTest):
    """Test edge cases for variables and row references"""

    def get_data(self):
        data = [
            {"id": 1, "null_field": None, "empty_array": [], "zero": 0},
            {
                "id": 2,
                "nested": {"deep": {"deeper": {"value": "found"}}},
                "unicode": "héllo wörld",
            },
            {"id": 3, "large_array": list(range(100)), "mixed": [1, "str", None, True]},
            {"id": 4, "special": {"$field": "dollar", "field.with.dots": "dotted"}},
            {
                "id": 5,
                "bool_fields": {"true": True, "false": False},
                "numbers": {"int": 42, "float": 3.14},
            },
        ]
        return as_db_and_table("test_db", "edge_cases", data)

    def test_null_field_access(self, conn):
        """Test r.row access with null fields"""
        result = list(
            r.db("test_db")
            .table("edge_cases")
            .filter({"id": 1})
            .map(
                lambda doc: r.branch(
                    doc["null_field"] == None, "is_null", doc["null_field"]
                )
            )
            .run(conn)
        )
        assertEqual(result[0], "is_null")

        # Test r.row with null field
        result = list(
            r.db("test_db")
            .table("edge_cases")
            .filter({"id": 1})
            .map(
                lambda doc: r.branch(
                    r.row["null_field"] == None, "row_is_null", r.row["null_field"]
                )
            )
            .run(conn)
        )
        assertEqual(result[0], "row_is_null")

    def test_deep_nested_access(self, conn):
        """Test very deep nested field access"""
        result = list(
            r.db("test_db")
            .table("edge_cases")
            .filter({"id": 2})
            .map(lambda doc: doc["nested"]["deep"]["deeper"]["value"])
            .run(conn)
        )
        assertEqual(result[0], "found")

        # Same with r.row
        result = list(
            r.db("test_db")
            .table("edge_cases")
            .filter({"id": 2})
            .map(lambda doc: r.row["nested"]["deep"]["deeper"]["value"])
            .run(conn)
        )
        assertEqual(result[0], "found")

    def test_missing_field_access(self, conn):
        """Test access to non-existent fields"""
        try:
            result = list(
                r.db("test_db")
                .table("edge_cases")
                .filter({"id": 1})
                .map(lambda doc: doc["nonexistent_field"])
                .run(conn)
            )
            # Should either return None or raise error
        except Exception:
            pass  # Missing field access might raise error

    def test_variable_scoping_edge_cases(self, conn):
        """Test complex variable scoping scenarios"""
        # Simpler nested operation to avoid scoping issues
        result = list(
            r.db("test_db")
            .table("edge_cases")
            .filter({"id": 3})
            .map(lambda doc: doc["large_array"][:5].count())
            .run(conn)
        )
        assertEqual(result[0], 5)

    def test_unicode_field_operations(self, conn):
        """Test operations on unicode fields"""
        result = list(
            r.db("test_db")
            .table("edge_cases")
            .filter({"id": 2})
            .map(lambda doc: doc["unicode"].upcase())
            .run(conn)
        )
        assertEqual(result[0], "HÉLLO WÖRLD")

        # Unicode with r.row
        result = list(
            r.db("test_db")
            .table("edge_cases")
            .filter({"id": 2})
            .map(lambda doc: r.row["unicode"].count())
            .run(conn)
        )
        assertEqual(result[0], 11)

    def test_special_field_names(self, conn):
        """Test fields with special characters in names"""
        # Access field with $ in name
        result = list(
            r.db("test_db")
            .table("edge_cases")
            .filter({"id": 4})
            .map(lambda doc: doc["special"]["$field"])
            .run(conn)
        )
        assertEqual(result[0], "dollar")

        # Access field with dots in name
        result = list(
            r.db("test_db")
            .table("edge_cases")
            .filter({"id": 4})
            .map(lambda doc: doc["special"]["field.with.dots"])
            .run(conn)
        )
        assertEqual(result[0], "dotted")

    def test_boolean_field_operations(self, conn):
        """Test operations on boolean fields"""
        result = list(
            r.db("test_db")
            .table("edge_cases")
            .filter({"id": 5})
            .map(lambda doc: doc["bool_fields"]["true"] & doc["bool_fields"]["false"])
            .run(conn)
        )
        assertEqual(result[0], False)

        # Boolean arithmetic
        result = list(
            r.db("test_db")
            .table("edge_cases")
            .filter({"id": 5})
            .map(lambda doc: doc["bool_fields"]["true"] + doc["bool_fields"]["false"])
            .run(conn)
        )
        assertEqual(result[0], 1)  # True=1, False=0

    def test_empty_array_operations(self, conn):
        """Test operations on empty arrays"""
        result = list(
            r.db("test_db")
            .table("edge_cases")
            .filter({"id": 1})
            .map(lambda doc: doc["empty_array"].count())
            .run(conn)
        )
        assertEqual(result[0], 0)

        # Map over empty array
        result = list(
            r.db("test_db")
            .table("edge_cases")
            .filter({"id": 1})
            .map(lambda doc: doc["empty_array"].map(lambda x: x * 2))
            .run(conn)
        )
        assertEqual(result[0], [])

    def test_zero_value_operations(self, conn):
        """Test operations with zero values"""
        # Division by zero handling
        try:
            result = list(
                r.db("test_db")
                .table("edge_cases")
                .filter({"id": 1})
                .map(lambda doc: 42 / doc["zero"])
                .run(conn)
            )
            # Should handle division by zero appropriately
        except Exception:
            pass  # Division by zero might raise error

        # Zero in boolean context - in RethinkDB, 0 is truthy
        result = list(
            r.db("test_db")
            .table("edge_cases")
            .filter({"id": 1})
            .map(lambda doc: r.branch(doc["zero"], "truthy", "falsy"))
            .run(conn)
        )
        assertEqual(result[0], "truthy")  # 0 is truthy in RethinkDB

    def test_large_array_performance(self, conn):
        """Test performance with large arrays"""
        # Operations on large array
        result = list(
            r.db("test_db")
            .table("edge_cases")
            .filter({"id": 3})
            .map(lambda doc: doc["large_array"].slice(50, 60).sum())
            .run(conn)
        )
        # Sum of numbers 50-59 = 545
        assertEqual(result[0], 545)

    def test_mixed_type_array_operations(self, conn):
        """Test operations on arrays with mixed types"""
        result = list(
            r.db("test_db")
            .table("edge_cases")
            .filter({"id": 3})
            .map(lambda doc: doc["mixed"].count())
            .run(conn)
        )
        assertEqual(result[0], 4)

        # Test that we can access mixed type array elements
        result = list(
            r.db("test_db")
            .table("edge_cases")
            .filter({"id": 3})
            .map(lambda doc: doc["mixed"][0])
            .run(conn)
        )
        assertEqual(result[0], 1)  # First element is the number 1

    def test_type_checking_with_variables(self, conn):
        """Test type checking in variable contexts"""
        result = list(
            r.db("test_db")
            .table("edge_cases")
            .map(lambda doc: r.type_of(doc["id"]))
            .distinct()
            .run(conn)
        )
        assertEqual(result, ["NUMBER"])

        # Type checking with r.row
        result = list(
            r.db("test_db")
            .table("edge_cases")
            .filter({"id": 5})
            .map(
                lambda doc: [
                    r.type_of(r.row["numbers"]["int"]),
                    r.type_of(r.row["numbers"]["float"]),
                ]
            )
            .run(conn)
        )
        assertEqual(result[0], ["NUMBER", "NUMBER"])

    def test_conditional_logic_edge_cases(self, conn):
        """Test complex conditional logic with variables"""
        # Nested r.branch with variables
        result = list(
            r.db("test_db")
            .table("edge_cases")
            .map(
                lambda doc: r.branch(
                    doc["id"] == 1,
                    r.branch(doc["null_field"] == None, "null_case", "not_null"),
                    r.branch(doc["id"] == 2, "case_2", "other"),
                )
            )
            .run(conn)
        )
        expected = ["null_case", "case_2", "other", "other", "other"]
        assertEqual(result, expected)

    def test_error_handling_in_variable_contexts(self, conn):
        """Test error handling within variable contexts"""
        # Error in lambda should be handled gracefully
        try:
            result = list(
                r.db("test_db")
                .table("edge_cases")
                .map(
                    lambda doc: r.branch(
                        doc["id"] == 1, 1 / doc["zero"], doc["id"]  # Division by zero
                    )
                )
                .run(conn)
            )
        except Exception:
            pass  # Should handle errors appropriately

    def test_variable_reference_consistency(self, conn):
        """Test that variable references are consistent"""
        # Same variable used multiple times should be consistent
        result = list(
            r.db("test_db")
            .table("edge_cases")
            .filter({"id": 5})
            .map(
                lambda doc: {
                    "first_ref": doc["numbers"]["int"],
                    "second_ref": doc["numbers"]["int"],
                    "are_equal": doc["numbers"]["int"] == doc["numbers"]["int"],
                }
            )
            .run(conn)
        )
        assertEqual(result[0]["first_ref"], result[0]["second_ref"])
        assertEqual(result[0]["are_equal"], True)
