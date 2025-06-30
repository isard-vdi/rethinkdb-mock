from rethinkdb import r
from tests.common import assertEqual
from tests.functional.common import MockTest


class TestJsonConversion(MockTest):
    @staticmethod
    def get_data():
        return {
            "dbs": {
                "test": {
                    "tables": {
                        "data": [
                            {"id": 1, "info": {"name": "John", "age": 30}},
                            {"id": 2, "info": {"name": "Jane", "age": 25}},
                        ]
                    }
                }
            }
        }

    def test_to_json_string_basic(self, conn):
        # Test basic JSON string conversion
        result = r.expr({"name": "John", "age": 30}).to_json_string().run(conn)
        # The exact formatting might vary, but it should be valid JSON
        assert "John" in result
        assert "30" in result

    def test_to_json_string_with_table(self, conn):
        # Test JSON conversion on table data
        result = list(
            r.db("test")
            .table("data")
            .map(lambda row: row["info"].to_json_string())
            .run(conn)
        )
        assert len(result) == 2
        assert all("name" in json_str for json_str in result)
