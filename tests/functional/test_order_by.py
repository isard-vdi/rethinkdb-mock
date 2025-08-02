from rethinkdb import r
from tests.common import as_db_and_table
from tests.common import assertEqual
from tests.functional.common import MockTest


class TestOrderByOne(MockTest):
    @staticmethod
    def get_data():
        data = [
            {"id": "bill", "age": 35, "score": 78},
            {"id": "joe", "age": 26, "score": 60},
            {"id": "todd", "age": 52, "score": 15},
        ]
        return as_db_and_table("y", "scores", data)

    def test_sort_1_attr(self, conn):
        expected = [
            {"id": "joe", "age": 26, "score": 60},
            {"id": "bill", "age": 35, "score": 78},
            {"id": "todd", "age": 52, "score": 15},
        ]
        result = r.db("y").table("scores").order_by("age").run(conn)
        assertEqual(expected, list(result))

    def test_sort_1_attr_asc(self, conn):
        expected = [
            {"id": "joe", "age": 26, "score": 60},
            {"id": "bill", "age": 35, "score": 78},
            {"id": "todd", "age": 52, "score": 15},
        ]
        result = r.db("y").table("scores").order_by(r.asc("age")).run(conn)
        assertEqual(expected, list(result))

    def test_sort_1_attr_desc(self, conn):
        expected = [
            {"id": "todd", "age": 52, "score": 15},
            {"id": "bill", "age": 35, "score": 78},
            {"id": "joe", "age": 26, "score": 60},
        ]
        result = r.db("y").table("scores").order_by(r.desc("age")).run(conn)
        assertEqual(expected, list(result))

    def test_sort_1_attr_2(self, conn):
        expected = [
            {"id": "todd", "age": 52, "score": 15},
            {"id": "joe", "age": 26, "score": 60},
            {"id": "bill", "age": 35, "score": 78},
        ]
        result = r.db("y").table("scores").order_by("score").run(conn)
        assertEqual(expected, list(result))

    def test_sort_1_attr_2_asc(self, conn):
        expected = [
            {"id": "todd", "age": 52, "score": 15},
            {"id": "joe", "age": 26, "score": 60},
            {"id": "bill", "age": 35, "score": 78},
        ]
        result = r.db("y").table("scores").order_by(r.asc("score")).run(conn)
        assertEqual(expected, list(result))

    def test_sort_1_attr_2_desc(self, conn):
        expected = [
            {"id": "bill", "age": 35, "score": 78},
            {"id": "joe", "age": 26, "score": 60},
            {"id": "todd", "age": 52, "score": 15},
        ]
        result = r.db("y").table("scores").order_by(r.desc("score")).run(conn)
        assertEqual(expected, list(result))

    def test_sort_1_attr_2_asc_index(self, conn):
        r.db("y").table("scores").index_create("score").run(conn)
        r.db("y").table("scores").index_wait().run(conn)
        expected = [
            {"id": "todd", "age": 52, "score": 15},
            {"id": "joe", "age": 26, "score": 60},
            {"id": "bill", "age": 35, "score": 78},
        ]
        result = r.db("y").table("scores").order_by(index="score").run(conn)
        assertEqual(expected, list(result))


class TestOrderByMulti(MockTest):
    @staticmethod
    def get_data():
        data = [
            {"id": "bill", "age": 35, "score": 78},
            {"id": "glen", "age": 26, "score": 15},
            {"id": "todd", "age": 52, "score": 15},
            {"id": "joe", "age": 26, "score": 60},
            {"id": "pale", "age": 52, "score": 30},
        ]
        return as_db_and_table("y", "scores", data)

    def test_sort_multi_1(self, conn):
        expected = [
            {"id": "glen", "age": 26, "score": 15},
            {"id": "joe", "age": 26, "score": 60},
            {"id": "bill", "age": 35, "score": 78},
            {"id": "todd", "age": 52, "score": 15},
            {"id": "pale", "age": 52, "score": 30},
        ]
        result = r.db("y").table("scores").order_by("age", "score").run(conn)
        assertEqual(expected, list(result))

    def test_sort_multi_1_asc(self, conn):
        expected = [
            {"id": "glen", "age": 26, "score": 15},
            {"id": "joe", "age": 26, "score": 60},
            {"id": "bill", "age": 35, "score": 78},
            {"id": "todd", "age": 52, "score": 15},
            {"id": "pale", "age": 52, "score": 30},
        ]
        result = (
            r.db("y").table("scores").order_by(r.asc("age"), r.asc("score")).run(conn)
        )
        assertEqual(expected, list(result))

    def test_sort_multi_1_desc_1(self, conn):
        expected = [
            {"id": "joe", "age": 26, "score": 60},
            {"id": "glen", "age": 26, "score": 15},
            {"id": "bill", "age": 35, "score": 78},
            {"id": "pale", "age": 52, "score": 30},
            {"id": "todd", "age": 52, "score": 15},
        ]
        result = (
            r.db("y").table("scores").order_by(r.asc("age"), r.desc("score")).run(conn)
        )
        assertEqual(expected, list(result))

    def test_sort_multi_1_desc_2(self, conn):
        expected = [
            {"id": "todd", "age": 52, "score": 15},
            {"id": "pale", "age": 52, "score": 30},
            {"id": "bill", "age": 35, "score": 78},
            {"id": "glen", "age": 26, "score": 15},
            {"id": "joe", "age": 26, "score": 60},
        ]
        result = r.db("y").table("scores").order_by(r.desc("age"), "score").run(conn)
        assertEqual(expected, list(result))

    def test_sort_multi_2(self, conn):
        expected = [
            {"id": "glen", "age": 26, "score": 15},
            {"id": "todd", "age": 52, "score": 15},
            {"id": "pale", "age": 52, "score": 30},
            {"id": "joe", "age": 26, "score": 60},
            {"id": "bill", "age": 35, "score": 78},
        ]
        result = r.db("y").table("scores").order_by("score", "age").run(conn)
        assertEqual(expected, list(result))


class TestOrderByEdgeCases(MockTest):
    """Test edge cases for order by operations"""

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
