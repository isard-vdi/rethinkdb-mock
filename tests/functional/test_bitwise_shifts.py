"""
Tests for bitwise shift operations in rethinkdb-mock
"""

import pytest
import rethinkdb as r

from rethinkdb_mock import MockRethinkDB


def test_bit_sal():
    """Test bit_sal() for bitwise left shift"""
    db = MockRethinkDB()

    # Test basic left shift
    result = r.expr(5).bit_sal(1).run(db)  # 5 << 1 = 10
    assert result == 10

    result = r.expr(5).bit_sal(2).run(db)  # 5 << 2 = 20
    assert result == 20

    result = r.expr(1).bit_sal(3).run(db)  # 1 << 3 = 8
    assert result == 8

    # Test zero shift
    result = r.expr(42).bit_sal(0).run(db)
    assert result == 42

    # Test large shift
    result = r.expr(1).bit_sal(10).run(db)  # 1 << 10 = 1024
    assert result == 1024

    # Test with negative number
    result = r.expr(-4).bit_sal(1).run(db)  # -4 << 1 = -8
    assert result == -8

    # Test error cases
    with pytest.raises(TypeError):
        r.expr("not a number").bit_sal(1).run(db)

    with pytest.raises(TypeError):
        r.expr(5).bit_sal("not a number").run(db)

    with pytest.raises(ValueError):
        r.expr(5).bit_sal(-1).run(db)  # Negative shift amount


def test_bit_sar():
    """Test bit_sar() for bitwise right shift"""
    db = MockRethinkDB()

    # Test basic right shift
    result = r.expr(10).bit_sar(1).run(db)  # 10 >> 1 = 5
    assert result == 5

    result = r.expr(20).bit_sar(2).run(db)  # 20 >> 2 = 5
    assert result == 5

    result = r.expr(8).bit_sar(3).run(db)  # 8 >> 3 = 1
    assert result == 1

    # Test zero shift
    result = r.expr(42).bit_sar(0).run(db)
    assert result == 42

    # Test large shift (should approach zero/negative one)
    result = r.expr(1024).bit_sar(10).run(db)  # 1024 >> 10 = 1
    assert result == 1

    # Test with negative number (arithmetic right shift)
    result = r.expr(-8).bit_sar(1).run(db)  # -8 >> 1 = -4
    assert result == -4

    result = r.expr(-1).bit_sar(5).run(db)  # -1 >> 5 = -1 (all bits 1)
    assert result == -1

    # Test shift beyond number of bits
    result = r.expr(5).bit_sar(10).run(db)  # Should be 0
    assert result == 0

    # Test error cases
    with pytest.raises(TypeError):
        r.expr("not a number").bit_sar(1).run(db)

    with pytest.raises(TypeError):
        r.expr(5).bit_sar("not a number").run(db)

    with pytest.raises(ValueError):
        r.expr(5).bit_sar(-1).run(db)  # Negative shift amount


def test_bit_shift_combinations():
    """Test combinations of bit shift operations"""
    db = MockRethinkDB()

    # Test chaining shifts
    result = r.expr(16).bit_sar(2).bit_sal(1).run(db)  # 16 >> 2 << 1 = 4 << 1 = 8
    assert result == 8

    # Test with other bitwise operations
    result = r.expr(12).bit_and(15).bit_sal(2).run(db)  # (12 & 15) << 2 = 12 << 2 = 48
    assert result == 48

    # Test expression as shift amount
    result = (
        r.expr(100).bit_sar(r.expr(2).add(1)).run(db)
    )  # 100 >> (2+1) = 100 >> 3 = 12
    assert result == 12
