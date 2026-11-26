import datetime as dt
from decimal import Decimal

import pytest

from app.importer import guess_category, parse_amount, parse_csv, parse_date


def test_parse_date_accepts_common_formats():
    assert parse_date("2026-11-22") == dt.date(2026, 11, 22)
    assert parse_date("22-11-2026") == dt.date(2026, 11, 22)
    assert parse_date("22/11/2026") == dt.date(2026, 11, 22)


def test_parse_date_rejects_nonsense():
    with pytest.raises(ValueError):
        parse_date("not a date")


def test_parse_amount_cleans_symbols():
    assert parse_amount("1,299.00") == Decimal("1299.00")
    assert parse_amount("₹250") == Decimal("250.00")


@pytest.mark.parametrize("value", ["-5", "0", "abc", ""])
def test_parse_amount_rejects_bad_values(value):
    with pytest.raises(ValueError):
        parse_amount(value)


def test_guess_category_from_keywords():
    assert guess_category("Swiggy order") == "Food"
    assert guess_category("UBER RIDE") == "Travel"
    assert guess_category("Amazon purchase") == "Shopping"
    assert guess_category("Chai stall") == "Uncategorized"


def test_parse_csv_returns_rows_and_errors():
    content = b"date,description,amount\n2026-11-20,Swiggy,420\n2026-11-21,Bad,-5\n"
    rows, errors = parse_csv(content)

    assert len(rows) == 1
    assert rows[0]["amount"] == Decimal("420.00")
    assert errors == [(3, "amount must be greater than 0")]


def test_parse_csv_missing_columns():
    with pytest.raises(ValueError, match="Missing columns"):
        parse_csv(b"date,amount\n2026-11-20,420\n")