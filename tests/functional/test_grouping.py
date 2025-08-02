from rethinkdb import r
from tests.common import as_db_and_table
from tests.common import assertEqual
from tests.common import assertEqUnordered
from tests.functional.common import MockTest


class TestGroup(MockTest):
    @staticmethod
    def get_data():
        data = [
            {"id": "joe", "type": "bro"},
            {"id": "bill", "type": "hipster"},
            {"id": "todd", "type": "hipster"},
        ]
        return as_db_and_table("x", "people", data)

    def test_group_by_field(self, conn):
        expected = {
            "bro": [
                {"id": "joe", "type": "bro"},
            ],
            "hipster": [
                {"id": "bill", "type": "hipster"},
                {"id": "todd", "type": "hipster"},
            ],
        }
        result = r.db("x").table("people").group("type").run(conn)
        assertEqual(expected["bro"], result["bro"])
        assertEqUnordered(expected["hipster"], result["hipster"])
        assertEqual(set(["bro", "hipster"]), set(result.keys()))

    def test_group_by_func(self, conn):
        expected = {
            "bro": [
                {"id": "joe", "type": "bro"},
            ],
            "hipster": [
                {"id": "bill", "type": "hipster"},
                {"id": "todd", "type": "hipster"},
            ],
        }
        result = r.db("x").table("people").group(lambda d: d["type"]).run(conn)
        assertEqual(expected["bro"], result["bro"])
        assertEqUnordered(expected["hipster"], result["hipster"])
        assertEqual(set(["bro", "hipster"]), set(result.keys()))

    def test_group_count(self, conn):
        expected = {"bro": 1, "hipster": 2}
        result = r.db("x").table("people").group("type").count().run(conn)
        assertEqual(expected, result)


class TestUngroup(MockTest):
    @staticmethod
    def get_data():
        data = [
            {"id": "joe", "type": "bro"},
            {"id": "bill", "type": "hipster"},
            {"id": "todd", "type": "hipster"},
            {"id": "sam", "type": "bro"},
            {"id": "glenn", "type": "unknown"},
        ]
        return as_db_and_table("x", "people", data)

    def test_ungroup_grouped_by_field(self, conn):
        expected = [
            {
                "group": "bro",
                "reduction": [
                    {"id": "joe", "type": "bro"},
                    {"id": "sam", "type": "bro"},
                ],
            },
            {
                "group": "hipster",
                "reduction": [
                    {"id": "bill", "type": "hipster"},
                    {"id": "todd", "type": "hipster"},
                ],
            },
            {
                "group": "unknown",
                "reduction": [
                    {"id": "glenn", "type": "unknown"},
                ],
            },
        ]
        result = r.db("x").table("people").group("type").ungroup().run(conn)
        result = list(result)
        assertEqual(3, len(result))
        assertEqual(
            set(["bro", "hipster", "unknown"]), set([doc["group"] for doc in result])
        )

        def is_group(group):
            return lambda doc: doc["group"] == group

        for group in ("bro", "hipster", "unknown"):
            result_group = list(filter(is_group(group), result))[0]
            expected_group = list(filter(is_group(group), expected))[0]
            assertEqUnordered(expected_group["reduction"], result_group["reduction"])

    def test_ungroup_grouped_by_func(self, conn):
        expected = [
            {
                "group": "bro",
                "reduction": [
                    {"id": "joe", "type": "bro"},
                    {"id": "sam", "type": "bro"},
                ],
            },
            {
                "group": "hipster",
                "reduction": [
                    {"id": "bill", "type": "hipster"},
                    {"id": "todd", "type": "hipster"},
                ],
            },
            {
                "group": "unknown",
                "reduction": [
                    {"id": "glenn", "type": "unknown"},
                ],
            },
        ]
        result = (
            r.db("x").table("people").group(lambda d: d["type"]).ungroup().run(conn)
        )
        result = list(result)
        assertEqual(3, len(result))
        assertEqual(
            set(["bro", "hipster", "unknown"]), set([doc["group"] for doc in result])
        )

        def is_group(group):
            return lambda doc: doc["group"] == group

        for group in ("bro", "hipster", "unknown"):
            result_group = list(filter(is_group(group), result))[0]
            expected_group = list(filter(is_group(group), expected))[0]
            assertEqUnordered(expected_group["reduction"], result_group["reduction"])


class TestGroupingEdgeCases(MockTest):
    """Test edge cases for grouping operations"""

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
