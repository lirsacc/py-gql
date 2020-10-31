# -*- coding: utf-8 -*-

import datetime as dt

import pytest

from py_gql._date_utils import offset, parse_date, parse_datetime, parse_time


@pytest.mark.parametrize(
    "value,expected",
    [
        (
            "1997-07-16T19:20+01:00",
            dt.datetime(1997, 7, 16, 19, 20, 0, 0, offset(1, 0)),
        ),
        (
            "2007-01-01T08:00:00",
            dt.datetime(2007, 1, 1, 8, 0, 0, 0, dt.timezone.utc),
        ),
        (
            "2006-10-20T15:34:56.123+02:30",
            dt.datetime(2006, 10, 20, 15, 34, 56, 123000, offset(2, 30)),
        ),
        (
            "2006-10-20T15:34:56Z",
            dt.datetime(2006, 10, 20, 15, 34, 56, 0, dt.timezone.utc),
        ),
        (
            "2006-10-20T15:34:56.123Z",
            dt.datetime(2006, 10, 20, 15, 34, 56, 123000, dt.timezone.utc),
        ),
        (
            "2013-10-15T18:30Z",
            dt.datetime(2013, 10, 15, 18, 30, 0, 0, dt.timezone.utc),
        ),
        (
            "2013-10-15T22:30+04",
            dt.datetime(2013, 10, 15, 22, 30, 0, 0, offset(4, 0)),
        ),
        (
            "2013-10-15T1130-0700",
            dt.datetime(2013, 10, 15, 11, 30, 0, 0, offset(-7, 0)),
        ),
        (
            "2013-10-15T1130+0700",
            dt.datetime(2013, 10, 15, 11, 30, 0, 0, offset(+7, 0)),
        ),
        (
            "2013-10-15T1130+07",
            dt.datetime(2013, 10, 15, 11, 30, 0, 0, offset(+7, 0)),
        ),
        (
            "2013-10-15T1130-07",
            dt.datetime(2013, 10, 15, 11, 30, 0, 0, offset(-7, 0)),
        ),
        (
            "2013-10-15T15:00-03:30",
            dt.datetime(2013, 10, 15, 15, 0, 0, 0, offset(-3, -30)),
        ),
        (
            "2013-10-15T183123Z",
            dt.datetime(2013, 10, 15, 18, 31, 23, 0, dt.timezone.utc),
        ),
        (
            "2013-10-15T1831Z",
            dt.datetime(2013, 10, 15, 18, 31, 0, 0, dt.timezone.utc),
        ),
        (
            "2013-10-15T18Z",
            dt.datetime(2013, 10, 15, 18, 0, 0, 0, dt.timezone.utc),
        ),
        ("2013-10-15", dt.datetime(2013, 10, 15, 0, 0, 0, 0, dt.timezone.utc)),
        (
            "20131015T18:30Z",
            dt.datetime(2013, 10, 15, 18, 30, 0, 0, dt.timezone.utc),
        ),
        (
            "2012-12-19T23:21:28.512400+00:00",
            dt.datetime(2012, 12, 19, 23, 21, 28, 512400, offset(0, 0)),
        ),
        (
            "2006-10-20T15:34:56.123+0230",
            dt.datetime(2006, 10, 20, 15, 34, 56, 123000, offset(2, 30)),
        ),
        ("19950204", dt.datetime(1995, 2, 4, tzinfo=dt.timezone.utc)),
        ("2010-06-12", dt.datetime(2010, 6, 12, tzinfo=dt.timezone.utc)),
        (
            "1985-04-12T23:20:50.52-05:30",
            dt.datetime(1985, 4, 12, 23, 20, 50, 520000, offset(-5, -30)),
        ),
        (
            "1997-08-29T06:14:00.000123Z",
            dt.datetime(1997, 8, 29, 6, 14, 0, 123, dt.timezone.utc),
        ),
        ("2014-02", dt.datetime(2014, 2, 1, 0, 0, 0, 0, dt.timezone.utc)),
        ("2014", dt.datetime(2014, 1, 1, 0, 0, 0, 0, dt.timezone.utc)),
        (
            "1997-08-29T06:14:00,000123Z",
            dt.datetime(1997, 8, 29, 6, 14, 0, 123, dt.timezone.utc),
        ),
    ],
)
def test_parse_datetime(value, expected):
    parsed = parse_datetime(value)
    assert expected == parsed
    assert expected == parse_datetime(parsed.isoformat())


@pytest.mark.parametrize(
    "value,expected_msg",
    [
        ("2013-10-", "Invalid ISO 8601 datetime '2013-10-'."),
        ("2013-", "Invalid ISO 8601 datetime '2013-'."),
        ("", "Invalid ISO 8601 datetime ''."),
        ("wibble", "Invalid ISO 8601 datetime 'wibble'."),
        ("23", "Invalid ISO 8601 datetime '23'."),
        ("131015T142533Z", "Invalid ISO 8601 datetime '131015T142533Z'."),
        ("131015", "Invalid ISO 8601 datetime '131015'."),
        ("20141", "Invalid ISO 8601 datetime '20141'."),
        ("201402", "Invalid ISO 8601 datetime '201402'."),
        (
            "2007-06-23X06:40:34.00Z",
            "Invalid ISO 8601 datetime '2007-06-23X06:40:34.00Z'.",
        ),
        (
            "2007-06-23T06:40:72.00Z",
            "Cannot parse datetime from 2007-06-23T06:40:72.00Z",
        ),
        (
            "2007-06-23 06:40:34.00Zrubbish",
            "Invalid ISO 8601 datetime '2007-06-23 06:40:34.00Zrubbish'.",
        ),
        (
            "20114-01-03T01:45:49",
            "Invalid ISO 8601 datetime '20114-01-03T01:45:49'.",
        ),
    ],
)
def test_parse_datetime_invalid(value, expected_msg):
    with pytest.raises(ValueError) as exc_info:
        parse_datetime(value)
    assert expected_msg in str(exc_info.value)


@pytest.mark.parametrize(
    "value,tz,expected",
    [
        (
            "2007-01-01T08:00:00",
            offset(2, 0),
            dt.datetime(2007, 1, 1, 8, 0, 0, 0, offset(2, 0)),
        ),
        (
            "2007-01-01T08:00:00Z",
            offset(2, 0),
            dt.datetime(2007, 1, 1, 8, 0, 0, 0, dt.timezone.utc),
        ),
        ("2007-01-01T08:00:00", None, dt.datetime(2007, 1, 1, 8, 0, 0, 0)),
        (
            "2007-01-01T08:00:00Z",
            None,
            dt.datetime(2007, 1, 1, 8, 0, 0, 0, dt.timezone.utc),
        ),
    ],
)
def test_parse_datetime_different_default_timezone(value, tz, expected):
    parsed = parse_datetime(value, default_timezone=tz)
    assert expected == parsed
    assert expected == parse_datetime(parsed.isoformat(), default_timezone=tz)


@pytest.mark.parametrize(
    "value,expected",
    [
        ("15:34:56.123", dt.time(15, 34, 56, 123000)),
        ("153456.123", dt.time(15, 34, 56, 123000)),
        ("15:34", dt.time(15, 34, 0, 0)),
        ("1534", dt.time(15, 34, 0, 0)),
        ("15", dt.time(15, 0, 0, 0)),
    ],
)
def test_parse_time(value, expected):
    assert expected == parse_time(value)


@pytest.mark.parametrize(
    "value,expected_msg",
    [
        ("X06:40:34.00", "Invalid ISO 8601 time 'X06:40:34.00'."),
        ("06:40:34.00foo", "Invalid ISO 8601 time '06:40:34.00foo'."),
        ("foo", "Invalid ISO 8601 time 'foo'."),
        ("06:40:72.00", "Cannot parse time from 06:40:72.00"),
    ],
)
def test_parse_time_invalid(value, expected_msg):
    with pytest.raises(ValueError) as exc_info:
        parse_time(value)
    assert expected_msg in str(exc_info.value)


@pytest.mark.parametrize(
    "value,expected",
    [
        ("2007-02-03", dt.date(2007, 2, 3)),
        ("20070203", dt.date(2007, 2, 3)),
        ("2007-02", dt.date(2007, 2, 1)),
        ("2007", dt.date(2007, 1, 1)),
    ],
)
def test_parse_date(value, expected):
    assert expected == parse_date(value)


@pytest.mark.parametrize(
    "value,expected_msg",
    [
        ("X2007-02-03", "Invalid ISO 8601 date 'X2007-02-03'."),
        ("20070203foo", "Invalid ISO 8601 date '20070203foo'."),
        ("foo", "Invalid ISO 8601 date 'foo'."),
        ("200702", "Invalid ISO 8601 date '200702'."),
    ],
)
def test_parse_date_invalid(value, expected_msg):
    with pytest.raises(ValueError) as exc_info:
        parse_date(value)
    assert str(exc_info.value) == expected_msg
