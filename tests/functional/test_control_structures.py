from rethinkdb import r
from tests.common import as_db_and_table
from tests.common import assertEqual
from tests.common import assertEqUnordered
from tests.functional.common import MockTest


class TestRange(MockTest):
    @staticmethod
    def get_data():
        return as_db_and_table("test_db", "data", [])

    def test_range_single_arg(self, conn):
        """Test range with single argument (0 to n)"""
        result = r.range(5).run(conn)
        expected = [0, 1, 2, 3, 4]
        assertEqual(expected, result)

    def test_range_zero(self, conn):
        """Test range with zero"""
        result = r.range(0).run(conn)
        expected = []
        assertEqual(expected, result)

    def test_range_two_args(self, conn):
        """Test range with start and end"""
        result = r.range(2, 7).run(conn)
        expected = [2, 3, 4, 5, 6]
        assertEqual(expected, result)

    def test_range_negative_start(self, conn):
        """Test range with negative start"""
        result = r.range(-3, 2).run(conn)
        expected = [-3, -2, -1, 0, 1]
        assertEqual(expected, result)

    def test_range_three_args(self, conn):
        """Test range with start, end, and step"""
        result = r.range(0, 10, 2).run(conn)
        expected = [0, 2, 4, 6, 8]
        assertEqual(expected, result)

    def test_range_negative_step(self, conn):
        """Test range with negative step"""
        result = r.range(10, 0, -2).run(conn)
        expected = [10, 8, 6, 4, 2]
        assertEqual(expected, result)

    def test_range_in_query(self, conn):
        """Test range used within a query"""
        result = r.range(3).map(lambda x: x.mul(2)).run(conn)
        expected = [0, 2, 4]
        assertEqual(expected, result)


class TestBitwiseOperations(MockTest):
    @staticmethod
    def get_data():
        return as_db_and_table("test_db", "data", [])

    def test_bit_and_basic(self, conn):
        """Test basic bitwise AND"""
        result = r.bit_and(12, 10).run(conn)  # 1100 & 1010 = 1000 = 8
        assertEqual(8, result)

    def test_bit_or_basic(self, conn):
        """Test basic bitwise OR"""
        result = r.bit_or(12, 10).run(conn)  # 1100 | 1010 = 1110 = 14
        assertEqual(14, result)

    def test_bit_xor_basic(self, conn):
        """Test basic bitwise XOR"""
        result = r.bit_xor(12, 10).run(conn)  # 1100 ^ 1010 = 0110 = 6
        assertEqual(6, result)

    def test_bit_not_basic(self, conn):
        """Test basic bitwise NOT"""
        result = r.bit_not(5).run(conn)  # ~5 = -6 (two's complement)
        assertEqual(-6, result)

    def test_bit_and_zero(self, conn):
        """Test bitwise AND with zero"""
        result = r.bit_and(15, 0).run(conn)
        assertEqual(0, result)

    def test_bit_or_zero(self, conn):
        """Test bitwise OR with zero"""
        result = r.bit_or(15, 0).run(conn)
        assertEqual(15, result)

    def test_bitwise_in_expression(self, conn):
        """Test bitwise operations in complex expression"""
        # ((5 & 3) | 4) ^ 2 = (1 | 4) ^ 2 = 5 ^ 2 = 7
        result = r.bit_xor(r.bit_or(r.bit_and(5, 3), 4), 2).run(conn)
        assertEqual(7, result)

    def test_bitwise_with_variables(self, conn):
        """Test bitwise operations with variable expressions"""
        result = r.expr(8).bit_and(r.expr(12)).run(conn)  # 8 & 12 = 8
        assertEqual(8, result)

    def test_bit_not_zero(self, conn):
        """Test bitwise NOT with zero"""
        result = r.bit_not(0).run(conn)
        assertEqual(-1, result)

    def test_bit_not_negative(self, conn):
        """Test bitwise NOT with negative number"""
        result = r.bit_not(-1).run(conn)
        assertEqual(0, result)
