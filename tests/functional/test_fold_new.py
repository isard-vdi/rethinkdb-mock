from rethinkdb import r
from tests.common import assertEqual
from tests.functional.common import MockTest


class TestFold(MockTest):
    @staticmethod
    def get_data():
        return {
            "dbs": {
                "test": {
                    "tables": {
                        "numbers": [
                            {"id": 1, "value": 5},
                            {"id": 2, "value": 10},
                            {"id": 3, "value": 15},
                        ]
                    }
                }
            }
        }

    def test_fold_sum(self, conn):
        # Test basic fold functionality - sum of values
        result = r.expr([1, 2, 3, 4, 5]).fold(0, lambda acc, val: acc + val).run(conn)
        assertEqual(result, 15)

    def test_fold_product(self, conn):
        # Test fold for multiplication
        result = r.expr([1, 2, 3, 4]).fold(1, lambda acc, val: acc * val).run(conn)
        assertEqual(result, 24)

    def test_fold_string_concat(self, conn):
        # Test fold with string concatenation
        result = (
            r.expr(["hello", " ", "world"])
            .fold("", lambda acc, val: acc + val)
            .run(conn)
        )
        assertEqual(result, "hello world")

    def test_fold_with_table(self, conn):
        # Test fold on a table
        result = (
            r.db("test")
            .table("numbers")
            .fold(0, lambda acc, val: acc + val["value"])
            .run(conn)
        )
        assertEqual(result, 30)  # 5 + 10 + 15
