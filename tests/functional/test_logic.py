from rethinkdb import r
from tests.common import as_db_and_table
from tests.common import assertEqual
from tests.common import assertEqUnordered
from tests.functional.common import MockTest


class TestLogic1(MockTest):
    @staticmethod
    def get_data():
        data = [
            {"id": "joe", "has_eyes": True, "age": 22, "hair_color": "brown"},
            {"id": "sam", "has_eyes": True, "age": 17, "hair_color": "bald"},
            {"id": "angela", "has_eyes": False, "age": 26, "hair_color": "black"},
            {"id": "johnson", "has_eyes": False, "age": 16, "hair_color": "blonde"},
        ]
        return as_db_and_table("pdb", "p", data)

    def test_not(self, conn):
        expected = [{"id": "johnson"}, {"id": "angela"}]
        result = (
            r.db("pdb")
            .table("p")
            .filter(lambda doc: ~doc["has_eyes"])
            .pluck("id")
            .run(conn)
        )
        assertEqUnordered(expected, list(result))

    def test_and(self, conn):
        expected = [{"id": "sam"}]
        result = (
            r.db("pdb")
            .table("p")
            .filter(lambda doc: doc["has_eyes"].and_(doc["age"].lt(20)))
            .pluck("id")
            .run(conn)
        )
        assertEqual(expected, list(result))

    def test_or(self, conn):
        expected = [{"id": "sam"}, {"id": "angela"}, {"id": "joe"}]
        result = (
            r.db("pdb")
            .table("p")
            .filter(lambda doc: doc["has_eyes"].or_(doc["age"].gt(20)))
            .pluck("id")
            .run(conn)
        )
        assertEqUnordered(expected, list(result))

    def test_gt(self, conn):
        expected = [{"id": "joe"}, {"id": "angela"}]
        result = (
            r.db("pdb")
            .table("p")
            .filter(lambda doc: doc["age"] > 20)
            .pluck("id")
            .run(conn)
        )
        assertEqUnordered(expected, list(result))

    def test_lt(self, conn):
        expected = [{"id": "sam"}, {"id": "johnson"}]
        result = (
            r.db("pdb")
            .table("p")
            .filter(lambda doc: doc["age"].lt(20))
            .pluck("id")
            .run(conn)
        )
        assertEqUnordered(expected, list(result))

    def test_eq(self, conn):
        expected = [{"id": "sam"}]
        result = (
            r.db("pdb")
            .table("p")
            .filter(lambda doc: doc["hair_color"] == "bald")
            .pluck("id")
            .run(conn)
        )
        assertEqual(expected, list(result))

    def test_neq(self, conn):
        expected = [{"id": "sam"}, {"id": "angela"}, {"id": "joe"}]
        result = (
            r.db("pdb")
            .table("p")
            .filter(lambda doc: doc["hair_color"] != "blonde")
            .pluck("id")
            .run(conn)
        )
        assertEqUnordered(expected, list(result))


class TestLogicEdgeCases(MockTest):
    """Test edge cases for logic operations"""

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
