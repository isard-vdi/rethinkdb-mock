"""
Test for newly implemented bitwise and conversion functions.

This module tests recently added functionality including:
- Bitwise operations (bit_sal, bit_sar, bit_and, bit_or, bit_xor, bit_not)
- JSON conversion functions (to_json_string)
- Other new utility functions
"""

from rethinkdb import r
from tests.common import as_db_and_table
from tests.common import assertEqual
from tests.functional.common import MockTest


class TestBitwiseOperations(MockTest):
    @staticmethod
    def get_data():
        return as_db_and_table("test", "test", [])

    def test_bit_sal_shift_left(self, conn):
        """Test bitwise shift left operation"""
        result = r.expr(5).bit_sal(1).run(conn)
        assertEqual(result, 10)  # 5 << 1 = 10

        result = r.expr(5).bit_sal(2).run(conn)
        assertEqual(result, 20)  # 5 << 2 = 20

    def test_bit_sar_shift_right(self, conn):
        """Test bitwise shift right operation"""
        result = r.expr(10).bit_sar(1).run(conn)
        assertEqual(result, 5)  # 10 >> 1 = 5

        result = r.expr(20).bit_sar(2).run(conn)
        assertEqual(result, 5)  # 20 >> 2 = 5

    def test_bit_and(self, conn):
        """Test bitwise AND operation"""
        result = r.expr(12).bit_and(10).run(conn)
        assertEqual(result, 8)  # 12 & 10 = 8

    def test_bit_or(self, conn):
        """Test bitwise OR operation"""
        result = r.expr(12).bit_or(10).run(conn)
        assertEqual(result, 14)  # 12 | 10 = 14

    def test_bit_xor(self, conn):
        """Test bitwise XOR operation"""
        result = r.expr(12).bit_xor(10).run(conn)
        assertEqual(result, 6)  # 12 ^ 10 = 6

    def test_bit_not(self, conn):
        """Test bitwise NOT operation"""
        result = r.expr(5).bit_not().run(conn)
        assertEqual(result, -6)  # ~5 = -6 (two's complement)


class TestJsonConversion(MockTest):
    @staticmethod
    def get_data():
        return as_db_and_table("test", "test", [])

    def test_to_json_string_object(self, conn):
        """Test converting object to JSON string"""
        result = r.expr({"key": "value", "number": 42}).to_json_string().run(conn)
        # Result should be valid JSON string
        import json

        parsed = json.loads(result)
        assertEqual(parsed["key"], "value")
        assertEqual(parsed["number"], 42)

    def test_to_json_string_array(self, conn):
        """Test converting array to JSON string"""
        result = r.expr([1, 2, 3, "test"]).to_json_string().run(conn)
        import json

        parsed = json.loads(result)
        assertEqual(parsed, [1, 2, 3, "test"])

    def test_to_json_string_simple_values(self, conn):
        """Test converting simple values to JSON strings"""
        result = r.expr("hello").to_json_string().run(conn)
        assertEqual(result, '"hello"')

        result = r.expr(42).to_json_string().run(conn)
        assertEqual(result, "42")

        result = r.expr(True).to_json_string().run(conn)
        assertEqual(result, "true")
