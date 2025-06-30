"""
Tests for fold aggregation function in rethinkdb-mock
"""

import pytest
import rethinkdb as r

from rethinkdb_mock import MockRethinkDB


def test_fold_basic():
    """Test basic fold operation with simple function"""
    db = MockRethinkDB()

    # Test sum using fold
    data = [1, 2, 3, 4, 5]
    result = r.expr(data).fold(0, lambda acc, item: acc + item).run(db)
    assert result == 15

    # Test product using fold
    data = [1, 2, 3, 4]
    result = r.expr(data).fold(1, lambda acc, item: acc * item).run(db)
    assert result == 24

    # Test string concatenation
    words = ["hello", " ", "world"]
    result = r.expr(words).fold("", lambda acc, item: acc + item).run(db)
    assert result == "hello world"


def test_fold_with_objects():
    """Test fold with object sequences"""
    db = MockRethinkDB()

    # Test folding to build an object
    items = [
        {"name": "Alice", "score": 85},
        {"name": "Bob", "score": 92},
        {"name": "Charlie", "score": 78},
    ]

    # Find maximum score using fold
    result = r.expr(items).fold(0, lambda acc, item: r.max(acc, item["score"])).run(db)
    assert result == 92

    # Count items using fold
    result = r.expr(items).fold(0, lambda acc, item: acc + 1).run(db)
    assert result == 3


def test_fold_with_arrays():
    """Test fold with array accumulation"""
    db = MockRethinkDB()

    # Test building array of specific values
    numbers = [1, 2, 3, 4, 5]

    # Collect even numbers using fold
    result = (
        r.expr(numbers)
        .fold([], lambda acc, item: r.branch(item.mod(2).eq(0), acc.append(item), acc))
        .run(db)
    )
    assert result == [2, 4]


def test_fold_empty_sequence():
    """Test fold with empty sequence"""
    db = MockRethinkDB()

    # Empty array should return base value
    result = r.expr([]).fold(42, lambda acc, item: acc + item).run(db)
    assert result == 42

    # Empty with different base
    result = r.expr([]).fold("base", lambda acc, item: acc + str(item)).run(db)
    assert result == "base"


def test_fold_single_element():
    """Test fold with single element sequence"""
    db = MockRethinkDB()

    # Single element should apply function once
    result = r.expr([5]).fold(10, lambda acc, item: acc + item).run(db)
    assert result == 15

    # Single element with multiplication
    result = r.expr([3]).fold(7, lambda acc, item: acc * item).run(db)
    assert result == 21


def test_fold_complex_aggregation():
    """Test fold for complex aggregation operations"""
    db = MockRethinkDB()

    # Test computing running totals
    transactions = [
        {"type": "credit", "amount": 100},
        {"type": "debit", "amount": 30},
        {"type": "credit", "amount": 50},
        {"type": "debit", "amount": 20},
    ]

    # Calculate balance using fold
    result = (
        r.expr(transactions)
        .fold(
            0,
            lambda balance, transaction: r.branch(
                transaction["type"].eq("credit"),
                balance + transaction["amount"],
                balance - transaction["amount"],
            ),
        )
        .run(db)
    )
    assert result == 100  # 0 + 100 - 30 + 50 - 20 = 100


def test_fold_error_cases():
    """Test error handling in fold"""
    db = MockRethinkDB()

    # Test with non-sequence
    with pytest.raises(TypeError):
        r.expr(42).fold(0, lambda acc, item: acc + item).run(db)

    # Test with invalid function (this might be harder to test depending on implementation)
    # The fold function should handle most cases gracefully


def test_fold_with_nested_operations():
    """Test fold with nested ReQL operations"""
    db = MockRethinkDB()

    # Test fold with conditional logic
    data = [{"value": 10}, {"value": 5}, {"value": 15}, {"value": 3}]

    # Count items where value > 5 using fold
    result = (
        r.expr(data)
        .fold(0, lambda count, item: r.branch(item["value"].gt(5), count + 1, count))
        .run(db)
    )
    assert result == 2  # Two items have value > 5 (10 and 15)

    # Build array of values > 5 using fold
    result = (
        r.expr(data)
        .fold(
            [],
            lambda acc, item: r.branch(
                item["value"].gt(5), acc.append(item["value"]), acc
            ),
        )
        .run(db)
    )
    assert result == [10, 15]
