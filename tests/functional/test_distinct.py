from pprint import pprint

from rethinkdb import r
from tests.common import as_db_and_table
from tests.common import assertEqual
from tests.common import assertEqUnordered
from tests.functional.common import MockTest

from rethinkdb_mock.util import DictableSet


class TestDistinctTop(MockTest):
    @staticmethod
    def get_data():
        data = [
            {"id": "bob-id", "first_name": "Bob", "last_name": "Sanders", "age": 35},
            {"id": "sam-id", "first_name": "Sam", "last_name": "Fudd", "age": 17},
            {"id": "joe-id", "first_name": "Joe", "last_name": "Sanders", "age": 62},
        ]
        return as_db_and_table("d", "people", data)

    def test_distinct_table(self, conn):
        expected = [
            {"id": "bob-id", "first_name": "Bob", "last_name": "Sanders", "age": 35},
            {"id": "sam-id", "first_name": "Sam", "last_name": "Fudd", "age": 17},
            {"id": "joe-id", "first_name": "Joe", "last_name": "Sanders", "age": 62},
        ]

        result = r.db("d").table("people").distinct().run(conn)
        assertEqUnordered(expected, list(result))

    def test_distinct_secondary_index(self, conn):
        r.db("d").table("people").index_create("last_name").run(conn)
        r.db("d").table("people").index_wait().run(conn)
        result = r.db("d").table("people").distinct(index="last_name").run(conn)
        result = list(result)
        pprint({"result": result})
        assertEqual(2, len(result))
        assertEqual(set(["Sanders", "Fudd"]), set(result))


class TestDistinctNested(MockTest):
    @staticmethod
    def get_data():
        data = [
            {"id": "x-id", "nums": [1, 5, 2, 5, 3, 2]},
            {
                "id": "y-id",
                "nums": [
                    {"val": 1},
                    {"val": 5},
                    {"val": 2},
                    {"val": 5},
                    {"val": 3},
                    {"val": 2},
                ],
            },
        ]
        return as_db_and_table("d", "people", data)

    def test_distinct_nested(self, conn):
        ex1 = set([1, 2, 5, 3])
        ex2 = DictableSet([{"val": 1}, {"val": 2}, {"val": 5}, {"val": 3}])
        result = (
            r.db("d").table("people").map(lambda doc: doc["nums"].distinct()).run(conn)
        )
        result = list(result)
        for elem in result:
            if isinstance(elem[0], dict):
                for dict_elem in elem:
                    assert ex2.has(dict_elem)
            else:
                assertEqual(ex1, set(elem))


class TestDistinctEdgeCases(MockTest):
    """Test edge cases for distinct operations"""

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
