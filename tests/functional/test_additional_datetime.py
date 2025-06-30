"""
Tests for additional date/time functions in rethinkdb-mock
"""

import datetime

import pytest
import rethinkdb as r

from rethinkdb_mock import MockRethinkDB


def test_in_timezone():
    """Test in_timezone() for converting datetime timezones"""
    db = MockRethinkDB()

    # Create a UTC datetime
    utc_time = datetime.datetime(2023, 6, 15, 12, 0, 0, tzinfo=datetime.timezone.utc)

    # Test converting to different timezones
    # Test UTC (Z format)
    result = r.expr(utc_time).in_timezone("Z").run(db)
    assert result.tzinfo == datetime.timezone.utc

    # Test positive offset
    result = r.expr(utc_time).in_timezone("+05:30").run(db)
    expected_tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    assert result.tzinfo == expected_tz

    # Test negative offset
    result = r.expr(utc_time).in_timezone("-08:00").run(db)
    expected_tz = datetime.timezone(datetime.timedelta(hours=-8))
    assert result.tzinfo == expected_tz

    # Test with non-datetime should raise error
    with pytest.raises(TypeError):
        r.expr("not a datetime").in_timezone("+00:00").run(db)


def test_timezone():
    """Test timezone() for getting timezone offset string"""
    db = MockRethinkDB()

    # Test UTC timezone
    utc_time = datetime.datetime(2023, 6, 15, 12, 0, 0, tzinfo=datetime.timezone.utc)
    result = r.expr(utc_time).timezone().run(db)
    assert result == "+00:00"

    # Test positive offset timezone
    tz_plus = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    time_plus = datetime.datetime(2023, 6, 15, 12, 0, 0, tzinfo=tz_plus)
    result = r.expr(time_plus).timezone().run(db)
    assert result == "+05:30"

    # Test negative offset timezone
    tz_minus = datetime.timezone(datetime.timedelta(hours=-8))
    time_minus = datetime.datetime(2023, 6, 15, 12, 0, 0, tzinfo=tz_minus)
    result = r.expr(time_minus).timezone().run(db)
    assert result == "-08:00"

    # Test naive datetime (should return +00:00)
    naive_time = datetime.datetime(2023, 6, 15, 12, 0, 0)
    result = r.expr(naive_time).timezone().run(db)
    assert result == "+00:00"

    # Test with non-datetime should raise error
    with pytest.raises(TypeError):
        r.expr("not a datetime").timezone().run(db)


def test_day_of_year():
    """Test day_of_year() for getting day number in year"""
    db = MockRethinkDB()

    # Test January 1st (day 1)
    jan_1 = datetime.datetime(2023, 1, 1, 12, 0, 0)
    result = r.expr(jan_1).day_of_year().run(db)
    assert result == 1

    # Test February 1st (day 32)
    feb_1 = datetime.datetime(2023, 2, 1, 12, 0, 0)
    result = r.expr(feb_1).day_of_year().run(db)
    assert result == 32

    # Test December 31st (day 365 in non-leap year)
    dec_31 = datetime.datetime(2023, 12, 31, 12, 0, 0)
    result = r.expr(dec_31).day_of_year().run(db)
    assert result == 365

    # Test leap year (2024)
    leap_dec_31 = datetime.datetime(2024, 12, 31, 12, 0, 0)
    result = r.expr(leap_dec_31).day_of_year().run(db)
    assert result == 366

    # Test with non-datetime should raise error
    with pytest.raises(TypeError):
        r.expr("not a datetime").day_of_year().run(db)


def test_to_iso8601():
    """Test to_iso8601() for converting datetime to ISO8601 string"""
    db = MockRethinkDB()

    # Test UTC datetime
    utc_time = datetime.datetime(2023, 6, 15, 12, 30, 45, tzinfo=datetime.timezone.utc)
    result = r.expr(utc_time).to_iso8601().run(db)
    assert result == "2023-06-15T12:30:45+00:00"

    # Test with timezone offset
    tz_plus = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    time_plus = datetime.datetime(2023, 6, 15, 12, 30, 45, tzinfo=tz_plus)
    result = r.expr(time_plus).to_iso8601().run(db)
    assert result == "2023-06-15T12:30:45+05:30"

    # Test naive datetime (should assume UTC)
    naive_time = datetime.datetime(2023, 6, 15, 12, 30, 45)
    result = r.expr(naive_time).to_iso8601().run(db)
    assert result == "2023-06-15T12:30:45+00:00"

    # Test with microseconds
    micro_time = datetime.datetime(
        2023, 6, 15, 12, 30, 45, 123456, tzinfo=datetime.timezone.utc
    )
    result = r.expr(micro_time).to_iso8601().run(db)
    assert result == "2023-06-15T12:30:45.123456+00:00"

    # Test with non-datetime should raise error
    with pytest.raises(TypeError):
        r.expr("not a datetime").to_iso8601().run(db)
