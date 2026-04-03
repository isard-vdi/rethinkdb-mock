from rethinkdb import r
from tests.common import as_db_and_table
from tests.common import assertEqUnordered
from tests.functional.common import MockTest


class TestPlucking(MockTest):
    @staticmethod
    def get_data():
        data = [
            {"id": "joe-id", "name": "joe", "hobby": "guitar"},
            {"id": "bob-id", "name": "bob", "hobby": "pseudointellectualism"},
            {"id": "bill-id", "name": "bill"},
            {"id": "kimye-id", "name": "kimye", "hobby": "being kimye"},
        ]
        return as_db_and_table("x", "people", data)

    def test_pluck_missing_attr(self, conn):
        expected = [
            {"id": "joe-id", "hobby": "guitar"},
            {"id": "bob-id", "hobby": "pseudointellectualism"},
            {"id": "bill-id"},
            {"id": "kimye-id", "hobby": "being kimye"},
        ]
        result = r.db("x").table("people").pluck("id", "hobby").run(conn)
        assertEqUnordered(expected, list(result))

    def test_pluck_missing_attr_list(self, conn):
        expected = [
            {"id": "joe-id", "hobby": "guitar"},
            {"id": "bob-id", "hobby": "pseudointellectualism"},
            {"id": "bill-id"},
            {"id": "kimye-id", "hobby": "being kimye"},
        ]
        result = r.db("x").table("people").pluck(["id", "hobby"]).run(conn)
        assertEqUnordered(expected, list(result))

    def test_sub_pluck(self, conn):
        expected = [
            {"id": "joe-id", "hobby": "guitar"},
            {"id": "bob-id", "hobby": "pseudointellectualism"},
            {"id": "bill-id"},
            {"id": "kimye-id", "hobby": "being kimye"},
        ]
        result = (
            r.db("x").table("people").map(lambda p: p.pluck("id", "hobby")).run(conn)
        )
        assertEqUnordered(expected, list(result))


class TestPlucking2(MockTest):
    @staticmethod
    def get_data():
        data = [
            {
                "id": "thing-1",
                "values": {"a": "a-1", "b": "b-1", "c": "c-1", "d": "d-1"},
            },
            {
                "id": "thing-2",
                "values": {"a": "a-2", "b": "b-2", "c": "c-2", "d": "d-2"},
            },
        ]
        return as_db_and_table("some_db", "things", data)

    def test_sub_sub(self, conn):
        expected = [{"a": "a-1", "d": "d-1"}, {"a": "a-2", "d": "d-2"}]
        result = (
            r.db("some_db")
            .table("things")
            .map(lambda t: t["values"].pluck("a", "d"))
            .run(conn)
        )
        assertEqUnordered(expected, list(result))

    def test_sub_sub_list(self, conn):
        expected = [{"a": "a-1", "d": "d-1"}, {"a": "a-2", "d": "d-2"}]
        result = (
            r.db("some_db")
            .table("things")
            .map(lambda t: t["values"].pluck("a", "d"))
            .run(conn)
        )
        assertEqUnordered(expected, list(result))

    def test_sub_dict(self, conn):
        expected = [{"values": {"a": "a-1"}}, {"values": {"a": "a-2"}}]
        result = r.db("some_db").table("things").pluck({"values": "a"}).run(conn)
        assertEqUnordered(expected, result)

    def test_sub_dict2(self, conn):
        expected = [
            {"id": "thing-1", "values": {"a": "a-1"}},
            {"id": "thing-2", "values": {"a": "a-2"}},
        ]
        result = r.db("some_db").table("things").pluck("id", {"values": "a"}).run(conn)
        assertEqUnordered(expected, result)

    def test_sub_dict_list(self, conn):
        expected = [
            {"id": "thing-1", "values": {"a": "a-1", "b": "b-1"}},
            {"id": "thing-2", "values": {"a": "a-2", "b": "b-2"}},
        ]
        result = (
            r.db("some_db")
            .table("things")
            .pluck("id", {"values": ["a", "b"]})
            .run(conn)
        )
        assertEqUnordered(expected, result)


class TestPluckNestedTrue(MockTest):
    """Test pluck with True leaf values in nested dict specs"""

    @staticmethod
    def get_data():
        data = [
            {
                "id": "doc-1",
                "name": "Doc 1",
                "create_dict": {
                    "hardware": {
                        "disks": {"storage_id": "stor-1", "size": 50},
                        "memory": 4096,
                    }
                },
            },
            {
                "id": "doc-2",
                "name": "Doc 2",
                "create_dict": {
                    "hardware": {
                        "disks": {"storage_id": "stor-2", "size": 100},
                        "memory": 8192,
                    }
                },
            },
        ]
        return as_db_and_table("test_db", "docs", data)

    def test_pluck_nested_true(self, conn):
        """Pluck with True leaf extracts only the specified nested field"""
        expected = [
            {"create_dict": {"hardware": {"disks": {"storage_id": "stor-1"}}}},
            {"create_dict": {"hardware": {"disks": {"storage_id": "stor-2"}}}},
        ]
        result = (
            r.db("test_db")
            .table("docs")
            .pluck({"create_dict": {"hardware": {"disks": {"storage_id": True}}}})
            .run(conn)
        )
        assertEqUnordered(expected, list(result))

    def test_pluck_nested_true_with_string_fields(self, conn):
        """Pluck combining string fields and nested True spec"""
        expected = [
            {
                "id": "doc-1",
                "name": "Doc 1",
                "create_dict": {"hardware": {"disks": {"storage_id": "stor-1"}}},
            },
            {
                "id": "doc-2",
                "name": "Doc 2",
                "create_dict": {"hardware": {"disks": {"storage_id": "stor-2"}}},
            },
        ]
        result = (
            r.db("test_db")
            .table("docs")
            .pluck(
                "id",
                "name",
                {"create_dict": {"hardware": {"disks": {"storage_id": True}}}},
            )
            .run(conn)
        )
        assertEqUnordered(expected, list(result))

    def test_pluck_nested_true_missing_field(self, conn):
        """Pluck with True on a field that doesn't exist returns empty dict"""
        result = (
            r.db("test_db")
            .table("docs")
            .pluck({"create_dict": {"hardware": {"disks": {"nonexistent": True}}}})
            .run(conn)
        )
        for doc in result:
            # Missing fields produce empty dicts at the leaf level
            assert doc["create_dict"]["hardware"]["disks"]["nonexistent"] == {}
