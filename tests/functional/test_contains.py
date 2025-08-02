from rethinkdb import r
from tests.common import as_db_and_table
from tests.common import assertEqual
from tests.functional.common import MockTest


class TestContains(MockTest):
    @staticmethod
    def get_data():
        data = [
            {"id": "bob-id", "age": 32, "nums": [5, 7]},
            {"id": "sam-id", "age": 45},
            {"id": "joe-id", "age": 36},
        ]
        return as_db_and_table("d", "people", data)

    def test_contains_table_dict_true(self, conn):
        result = (
            r.db("d").table("people").contains({"id": "sam-id", "age": 45}).run(conn)
        )
        assertEqual(True, result)

    def test_contains_table_dict_multi_true(self, conn):
        result = (
            r.db("d")
            .table("people")
            .contains({"id": "sam-id", "age": 45}, {"id": "joe-id", "age": 36})
            .run(conn)
        )
        assertEqual(True, result)

    def test_contains_table_dict_false(self, conn):
        result = (
            r.db("d")
            .table("people")
            .contains({"id": "tara-muse-id", "age": "timeless"})
            .run(conn)
        )
        assertEqual(False, result)

    def test_contains_table_dict_multi_false(self, conn):
        result = (
            r.db("d")
            .table("people")
            .contains(
                {"id": "sam-id", "age": 45}, {"id": "tara-muse-id", "age": "timeless"}
            )
            .run(conn)
        )
        assertEqual(False, result)

    def test_contains_table_pred_true(self, conn):
        result = (
            r.db("d")
            .table("people")
            .contains(lambda doc: doc["id"] == "sam-id")
            .run(conn)
        )
        assertEqual(True, result)

    def test_contains_table_pred_multi_true(self, conn):
        result = (
            r.db("d")
            .table("people")
            .contains(
                lambda doc: doc["id"] == "sam-id", lambda doc: doc["id"] == "joe-id"
            )
            .run(conn)
        )
        assertEqual(True, result)

    def test_contains_table_pred_false(self, conn):
        result = (
            r.db("d")
            .table("people")
            .contains(lambda doc: doc["id"] == "tara-muse-id")
            .run(conn)
        )
        assertEqual(False, result)

    def test_contains_table_pred_multi_false(self, conn):
        result = (
            r.db("d")
            .table("people")
            .contains(
                lambda doc: doc["id"] == "sam-id",
                lambda doc: doc["id"] == "tara-muse-id",
            )
            .run(conn)
        )
        assertEqual(False, result)

    def test_contains_lambda(self, conn):
        expected = [
            {"id": "bob-id", "age": 32, "nums": [5, 7]},
            {"id": "sam-id", "age": 45},
        ]
        result = (
            r.db("d")
            .table("people")
            .filter(
                lambda doc: r.expr(["non_existent", "sam-id", "bob-id"]).contains(
                    doc["id"]
                )
            )
            .run(conn)
        )
        assertEqual(
            sorted(expected, key=lambda d: d["id"]),
            sorted(list(result), key=lambda d: d["id"]),
        )


class TestContainsEdgeCases(MockTest):
    """Test edge cases for contains operations"""

    @staticmethod
    def get_data():
        data = [
            {"id": 1, "value": None, "empty_str": "", "zero": 0},
            {"id": 2, "array": [], "nested": {"deep": {"value": 42}}},
            {"id": 3, "large_array": list(range(1000)), "unicode": "héllo wörld"},
            {"id": 4, "mixed_types": [1, "str", None, True, 3.14]},
            {"id": 5, "special_chars": "\n\t\r\\", "whitespace": "  \t\n  "},
        ]
        return as_db_and_table("test_db", "edge_cases", data)

    def test_null_value_handling(self, conn):
        """Test operations with null values"""
        result = list(r.db("test_db").table("edge_cases").filter({"id": 1}).run(conn))
        assertEqual(len(result), 1)
        assertEqual(result[0]["value"], None)

    def test_empty_data_handling(self, conn):
        """Test operations with empty data"""
        result = list(r.db("test_db").table("edge_cases").filter({"id": 2}).run(conn))
        assertEqual(len(result), 1)
        assertEqual(result[0]["array"], [])

    def test_large_data_handling(self, conn):
        """Test operations with large datasets"""
        result = list(r.db("test_db").table("edge_cases").filter({"id": 3}).run(conn))
        assertEqual(len(result), 1)
        assertEqual(len(result[0]["large_array"]), 1000)

    def test_mixed_type_handling(self, conn):
        """Test operations with mixed data types"""
        result = list(r.db("test_db").table("edge_cases").filter({"id": 4}).run(conn))
        assertEqual(len(result), 1)
        assertEqual(len(result[0]["mixed_types"]), 5)

    def test_special_character_handling(self, conn):
        """Test operations with special characters"""
        result = list(r.db("test_db").table("edge_cases").filter({"id": 5}).run(conn))
        assertEqual(len(result), 1)
        assert "\n" in result[0]["special_chars"]
