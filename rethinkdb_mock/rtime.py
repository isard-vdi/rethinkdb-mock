import datetime

import rethinkdb


def to_date(dt, timezone=None):
    return datetime.datetime(dt.year, dt.month, dt.day, tzinfo=dt.tzinfo)


def time_of_day_seconds(dt):
    minutes = (dt.hour * 60) + dt.minute
    return (minutes * 60) + dt.second


def day_of_year(dt):
    """Get the day of year (1-366) for the given datetime"""
    return dt.timetuple().tm_yday


def in_timezone(dt, timezone_str):
    """Convert datetime to specified timezone"""
    if timezone_str == "Z" or timezone_str == "+00:00":
        new_tz = datetime.timezone.utc
    else:
        # Parse timezone string like "+05:30" or "-08:00"
        if timezone_str.startswith(("+", "-")):
            sign = 1 if timezone_str[0] == "+" else -1
            hours, minutes = map(int, timezone_str[1:].split(":"))
            offset = sign * (hours * 60 + minutes)
            new_tz = datetime.timezone(datetime.timedelta(minutes=offset))
        else:
            raise ValueError(f"Unsupported timezone format: {timezone_str}")

    return dt.astimezone(new_tz)


def get_timezone(dt):
    """Get the timezone offset string for the given datetime"""
    if dt.tzinfo is None:
        return "+00:00"

    offset = dt.utcoffset()
    if offset is None:
        return "+00:00"

    total_seconds = int(offset.total_seconds())
    hours, remainder = divmod(abs(total_seconds), 3600)
    minutes = remainder // 60
    sign = "+" if total_seconds >= 0 else "-"
    return f"{sign}{hours:02d}:{minutes:02d}"


def to_iso8601(dt):
    """Convert datetime to ISO8601 string format"""
    if dt.tzinfo is None:
        # Assume UTC if no timezone info
        dt = dt.replace(tzinfo=datetime.timezone.utc)

    # Format: YYYY-MM-DDTHH:MM:SS.sss+00:00
    return dt.isoformat()


def make_time(year, month, day, hour=0, minute=0, second=0, timezone=None):
    timezone = timezone or rethinkdb.r.make_timezone("00:00")
    return datetime.datetime(year, month, day, hour, minute, second, tzinfo=timezone)


def now():
    dtime = datetime.datetime.now()
    return dtime.replace(tzinfo=rethinkdb.r.make_timezone("00:00"))


def create_rql_timezone(timezone_string):
    if timezone_string == "Z":
        return rethinkdb.r.make_timezone("00:00")
    else:
        raise NotImplementedError


def epoch_time(dt):
    #   there's definitely a better way to do this.
    jan1_1970 = datetime.datetime(1970, 1, 1, tzinfo=dt.tzinfo)
    return int((dt - jan1_1970).total_seconds())


def from_epoch_time(timestamp):
    """Create a datetime object from Unix epoch time (seconds since 1970-01-01)"""
    return datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)


def rql_compatible_time(year, month, day, *args):
    hour, minute, second = (0, 0, 0)
    arg_count = len(args)
    if arg_count == 1:
        timezone = args[0]
    elif arg_count == 2:
        hour, timezone = args
    elif arg_count == 3:
        hour, minute, timezone = args
    elif arg_count == 4:
        hour, minute, second, timezone = args
    timezone = create_rql_timezone(timezone)
    return datetime.datetime(year, month, day, hour, minute, second, tzinfo=timezone)
