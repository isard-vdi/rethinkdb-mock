from rethinkdb import r
from tests.common import as_db_and_table
from tests.common import assertEqual
from tests.common import assertEqUnordered
from tests.functional.common import MockTest


class TestMath(MockTest):
    @staticmethod
    def get_data():
        data = [{"id": "pt-1", "x": 10, "y": 25}, {"id": "pt-2", "x": 100, "y": 3}]
        return as_db_and_table("math_db", "points", data)

    def test_add_method(self, conn):
        expected = [35, 103]
        result = (
            r.db("math_db").table("points").map(lambda t: t["x"].add(t["y"])).run(conn)
        )
        assertEqUnordered(expected, list(result))

    def test_add_oper(self, conn):
        expected = [35, 103]
        result = (
            r.db("math_db").table("points").map(lambda t: t["x"] + t["y"]).run(conn)
        )
        assertEqUnordered(expected, list(result))

    def test_sub_method(self, conn):
        expected = [-15, 97]
        result = (
            r.db("math_db").table("points").map(lambda t: t["x"].sub(t["y"])).run(conn)
        )
        assertEqUnordered(expected, list(result))

    def test_sub_oper(self, conn):
        expected = [-15, 97]
        result = (
            r.db("math_db").table("points").map(lambda t: t["x"] - t["y"]).run(conn)
        )
        assertEqUnordered(expected, list(result))

    def test_mul_method(self, conn):
        expected = [250, 300]
        result = (
            r.db("math_db").table("points").map(lambda t: t["x"].mul(t["y"])).run(conn)
        )
        assertEqUnordered(expected, list(result))

    def test_mul_oper(self, conn):
        expected = [250, 300]
        result = (
            r.db("math_db").table("points").map(lambda t: t["x"] * t["y"]).run(conn)
        )
        assertEqUnordered(expected, list(result))


class TestMath2(MockTest):
    @staticmethod
    def get_data():
        data = [
            {"id": "pt-1", "x": 30, "y": 3, "z": 18},
            {"id": "pt-2", "x": 24, "y": 6, "z": 10},
        ]
        return as_db_and_table("math_db", "points", data)

    def test_div_method(self, conn):
        expected = set([10, 4])
        result = (
            r.db("math_db").table("points").map(lambda t: t["x"].div(t["y"])).run(conn)
        )
        assertEqual(expected, set(list(result)))

    def test_div_oper(self, conn):
        expected = set([10, 4])
        result = (
            r.db("math_db").table("points").map(lambda t: t["x"] / t["y"]).run(conn)
        )
        assertEqual(expected, set(list(result)))

    def test_mod_method(self, conn):
        expected = set([12, 4])
        result = (
            r.db("math_db").table("points").map(lambda t: t["x"].mod(t["z"])).run(conn)
        )
        assertEqual(expected, set(list(result)))

    def test_mod_oper(self, conn):
        expected = set([12, 4])
        result = (
            r.db("math_db").table("points").map(lambda t: t["x"] % t["z"]).run(conn)
        )
        assertEqual(expected, set(list(result)))


class TestRandom(MockTest):
    @staticmethod
    def get_data():
        # Provide data for both "things" db (for random tests) and "math_db" (for math_in_query test)
        return {
            "dbs": {
                "things": {
                    "tables": {
                        "pointless": [{"id": "x", "val": 12}, {"id": "y", "val": 30}]
                    }
                },
                "math_db": {
                    "tables": {
                        "points": [{"id": "pt-1", "x": 9.6}, {"id": "pt-2", "x": 99.6}]
                    }
                },
            }
        }

    def test_random_0(self, conn):
        result = r.random().run(conn)
        assert result <= 1
        assert result >= 0
        assert type(result) is float

    def test_random_1(self, conn):
        result = r.random(10).run(conn)
        assert result <= 10
        assert result >= 0
        assert type(result) is int

    def test_random_1_float(self, conn):
        result = r.random(10).run(conn)
        assert result <= 10
        assert result >= 0
        assert type(result) is int

    def test_random_2(self, conn):
        result = r.random(10, 20).run(conn)
        assert result <= 20
        assert result >= 10
        assert type(result) is int

    def test_random_2_float(self, conn):
        result = r.random(10, 20, float=True).run(conn)
        assert result <= 20
        assert result >= 10
        assert type(result) is float

    def test_round_basic(self, conn):
        """Test basic round functionality"""
        result = r.expr(3.14159).round().run(conn)
        assertEqual(3, result)

    def test_round_negative(self, conn):
        """Test round with negative numbers"""
        result = r.expr(-3.7).round().run(conn)
        assertEqual(-4, result)

    def test_round_with_precision(self, conn):
        """Test round with specified precision"""
        result = r.expr(3.14159).round(2).run(conn)
        assertEqual(3.14, result)

    def test_round_zero_precision(self, conn):
        """Test round with zero precision"""
        result = r.expr(3.14159).round(0).run(conn)
        assertEqual(3.0, result)

    def test_ceil_basic(self, conn):
        """Test basic ceil functionality"""
        result = r.expr(3.14159).ceil().run(conn)
        assertEqual(4, result)

    def test_ceil_negative(self, conn):
        """Test ceil with negative numbers"""
        result = r.expr(-3.7).ceil().run(conn)
        assertEqual(-3, result)

    def test_ceil_integer(self, conn):
        """Test ceil with integer input"""
        result = r.expr(5).ceil().run(conn)
        assertEqual(5, result)

    def test_floor_basic(self, conn):
        """Test basic floor functionality"""
        result = r.expr(3.14159).floor().run(conn)
        assertEqual(3, result)

    def test_floor_negative(self, conn):
        """Test floor with negative numbers"""
        result = r.expr(-3.2).floor().run(conn)
        assertEqual(-4, result)

    def test_floor_integer(self, conn):
        """Test floor with integer input"""
        result = r.expr(5).floor().run(conn)
        assertEqual(5, result)

    def test_math_in_query(self, conn):
        """Test math functions within a query"""
        expected = [{"id": "pt-1", "x_rounded": 10}, {"id": "pt-2", "x_rounded": 100}]
        result = list(
            r.db("math_db")
            .table("points")
            .map(
                lambda pt: {
                    "id": pt["id"],
                    "x_rounded": pt["x"].add(0.4).round(),
                }
            )
            .run(conn)
        )
        assertEqUnordered(expected, result)
