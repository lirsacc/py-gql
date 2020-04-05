# -*- coding: utf-8 -*-
"""
Utilities to work with Python datetime values and the ISO 8601
standard.

This module parses serialised values according to the following rules:

Dates:
    - YYYY-MM-DD
    - YYYYMMDD
    - YYYY-MM (defaults to 1 for the day)
    - YYYY (defaults to 1 for month and day)

Times:
    - hh:mm:ss.nn
    - hhmmss.nn
    - hh:mm (defaults to 0 for seconds)
    - hhmm (defaults to 0 for seconds)
    - hh (defaults to 0 for minutes and seconds)

Time Zones:
    - Nothing, will use the default UTC timezone
    - Z (UTC)
    - +/-hh:mm
    - +/-hhmm
    = +/-hh

Adapted from https://bitbucket.org/micktwomey/pyiso8601/. The main changes are:

    - Do not accept space separator in datetimes
    - Do not accept month and days without leading 0
    - Extracted pattersn to support times and dates independently
"""

import datetime
import decimal
import re
from typing import Any, Optional


TIME_PATTERN = re.compile(
    r"""
    ^
    (?P<hour>[0-9]{2})
    (:?(?P<minute>[0-9]{2}))?
    (
        :?(?P<second>[0-9]{2})
        ([.,](?P<microsecond>[0-9]+))?
    )?
    $
    """,
    re.VERBOSE,
)

DATE_PATTERN = re.compile(
    r"""
    ^
    (?P<year>[0-9]{4})
    (
        (
            (-(?P<monthdash>[0-9]{2}))
            |
            (?P<month>[0-9]{2})
            (?!$)  # Don't allow YYYYMM
        )
        (
            (
                (-(?P<daydash>[0-9]{2}))
                |
                (?P<day>[0-9]{2})
            )
        )?  # YYYY-MM
    )?  # YYYY only
    $
    """,
    re.VERBOSE,
)

DATETIME_PATTERN = re.compile(
    r"""
    ^
    (?P<year>[0-9]{4})
    (
        (
            (-(?P<monthdash>[0-9]{2}))
            |
            (?P<month>[0-9]{2})
            (?!$)  # Don't allow YYYYMM
        )
        (
            (
                (-(?P<daydash>[0-9]{2}))
                |
                (?P<day>[0-9]{2})
            )
            (
                (
                    T
                    (?P<hour>[0-9]{2})
                    (:?(?P<minute>[0-9]{2}))?
                    (
                        :?(?P<second>[0-9]{2})
                        ([.,](?P<microsecond>[0-9]+))?
                    )?
                    (?P<timezone>
                        Z
                        |
                        (
                            (?P<tz_sign>[-+])
                            (?P<tz_hour>[0-9]{2})
                            :?
                            (?P<tz_minute>[0-9]{2})?
                        )
                    )?
                )?
            )
        )?  # YYYY-MM
    )?  # YYYY only
    $
    """,
    re.VERBOSE,
)


def to_int(
    key: str, value: Optional[str], default: Optional[int] = None
) -> int:
    """
    >>> to_int("foo", "42")
    42
    >>> to_int("foo", None)
    Traceback (most recent call last):
        ...
    ValueError: Missing foo part.
    >>> to_int("foo", "", 0)
    0
    >>> to_int("foo", None, 1)
    1
    >>> to_int("foo", "foo")
    Traceback (most recent call last):
        ...
    ValueError: Invalid foo part.
    """
    if value is None or not value:
        if default is not None:
            return default
        raise ValueError("Missing %s part." % key)

    try:
        return int(value)
    except ValueError:
        raise ValueError("Invalid %s part." % key)


def offset(hours: int, minutes: int) -> datetime.timezone:
    return datetime.timezone(datetime.timedelta(hours=hours, minutes=minutes))


def _parse_microseconds(value: Optional[str]) -> int:
    if not value:
        return 0
    else:
        return int(
            decimal.Decimal("0.%s" % (value or 0))
            * decimal.Decimal("1000000.0")
        )


def parse_datetime(
    value: str,
    default_timezone: Optional[datetime.tzinfo] = datetime.timezone.utc,
) -> datetime.datetime:
    """
    Parse an ISO 8601 formatted datetime into a :py:class:`datetime.datetime` object.
    """
    match = DATETIME_PATTERN.match(value)
    if not match:
        raise ValueError("Invalid ISO 8601 datetime %r." % value)

    groups = match.groupdict()

    if groups["timezone"] == "Z":
        tzinfo = datetime.timezone.utc
    elif groups["timezone"] is None:
        tzinfo = default_timezone
    else:
        sign = groups["tz_sign"]
        hours = to_int("timezone", groups["tz_hour"])
        minutes = to_int("timezone", groups["tz_minute"], 0)
        if sign == "-":
            hours, minutes = -hours, -minutes
        tzinfo = offset(hours, minutes)

    try:
        return datetime.datetime(
            year=to_int("year", groups.get("year")),
            month=to_int("month", groups["month"] or groups["monthdash"], 1),
            day=to_int("day", groups["day"] or groups["daydash"], 1),
            hour=to_int("hour", groups["hour"], 0),
            minute=to_int("minute", groups["minute"], 0),
            second=to_int("second", groups["second"], 0),
            microsecond=_parse_microseconds(groups["microsecond"]),
            tzinfo=tzinfo,
        )
    except ValueError as err:
        raise ValueError("Cannot parse datetime from %s (%s)" % (value, err))


def parse_time(value: str) -> datetime.time:
    """
    Parse an ISO 8601 formatted time into a :py:class:`datetime.time` object.
    """
    match = TIME_PATTERN.match(value)
    if not match:
        raise ValueError("Invalid ISO 8601 time %r." % value)

    groups = match.groupdict()

    try:
        return datetime.time(
            hour=to_int("hour", groups["hour"], 0),
            minute=to_int("minute", groups["minute"], 0),
            second=to_int("second", groups["second"], 0),
            microsecond=_parse_microseconds(groups["microsecond"]),
        )
    except ValueError as err:
        raise ValueError("Cannot parse time from %s (%s)" % (value, err))


def parse_date(value: str) -> datetime.date:
    """
    Parse an ISO 8601 formatted date into a :py:class:`datetime.date` object.
    """
    match = DATE_PATTERN.match(value)
    if not match:
        raise ValueError("Invalid ISO 8601 date %r." % value)

    groups = match.groupdict()

    try:
        return datetime.date(
            year=to_int("year", groups.get("year")),
            month=to_int("month", groups["month"] or groups["monthdash"], 1),
            day=to_int("day", groups["day"] or groups["daydash"], 1),
        )
    except ValueError as err:
        raise ValueError("Cannot parse date from %s (%s)" % (value, err))


def serialize_datetime(value: Any) -> str:
    """
    >>> serialize_datetime("foo")
    Traceback (most recent call last):
        ...
    TypeError: Expected datetime instance but got 'foo'
    >>> serialize_datetime(
    ...     datetime.datetime(1997, 8, 29, 6, 14, 0, 123, datetime.timezone.utc)
    ... )
    '1997-08-29T06:14:00.000123+00:00'
    """
    if not isinstance(value, datetime.date):
        raise TypeError("Expected datetime instance but got %r" % value)
    return value.isoformat()


def serialize_date(value: Any) -> str:
    """
    >>> serialize_date("foo")
    Traceback (most recent call last):
        ...
    TypeError: Expected date instance but got 'foo'
    >>> serialize_date(
    ...     datetime.datetime(1997, 8, 29, 6, 14, 0, 123, datetime.timezone.utc)
    ... )
    '1997-08-29'
    >>> serialize_date(datetime.date(1997, 8, 29))
    '1997-08-29'
    """
    if not isinstance(value, datetime.date):
        raise TypeError("Expected date instance but got %r" % value)
    if isinstance(value, datetime.datetime):
        value = value.date()
    return value.isoformat()


def serialize_time(value: Any) -> str:
    """
    >>> serialize_time("foo")
    Traceback (most recent call last):
        ...
    TypeError: Expected time instance but got 'foo'
    >>> serialize_time(datetime.time(6, 14, 0, 123))
    '06:14:00.000123'
    """
    if not isinstance(value, datetime.time):
        raise TypeError("Expected time instance but got %r" % value)
    return value.isoformat()
