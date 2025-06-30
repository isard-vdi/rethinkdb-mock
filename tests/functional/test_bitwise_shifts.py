from rethinkdb import r
from tests.common import assertEqual
from tests.functional.common import MockTest


class TestBitwiseShifts(MockTest):
    @staticmethod
    def get_data():
        return {
            "dbs": {
                "test": {
                    "tables": {
                        "numbers": [{"id": 1, "value": 8}, {"id": 2, "value": 16}]
                    }
                }
            }
        }

    def test_bit_sal_basic(self, conn):
        # Test basic bit shift left (arithmetic left shift)
        result = r.expr(4).bit_sal(2).run(conn)  # 4 << 2 = 16
        assertEqual(result, 16)

    def test_bit_sar_basic(self, conn):
        # Test basic bit shift right (arithmetic right shift)
        result = r.expr(16).bit_sar(2).run(conn)  # 16 >> 2 = 4
        assertEqual(result, 4)

    def test_bit_operations_with_table(self, conn):
        # Test bit operations on table data
        result = list(
            r.db("test")
            .table("numbers")
            .map(lambda row: row["value"].bit_sal(1))
            .run(conn)
        )
        assertEqual(sorted(result), [16, 32])  # 8 << 1 = 16, 16 << 1 = 32
