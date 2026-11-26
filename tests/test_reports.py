from decimal import Decimal


def make_category(client, name):
    return client.post("/categories", json={"name": name}).json()["id"]


def add_payment(client, category_id, amount, date):
    response = client.post(
        "/transactions",
        json={"amount": amount, "date": date, "category_id": category_id},
    )
    assert response.status_code == 201


def test_monthly_total_and_categories(client):
    rent = make_category(client, "Rent")
    food = make_category(client, "Food")
    add_payment(client, rent, 12000, "2026-10-01")
    add_payment(client, food, 420, "2026-10-09")
    add_payment(client, food, 300, "2026-10-27")

    report = client.get("/reports/monthly", params={"month": "2026-10"}).json()

    assert Decimal(report["total"]) == Decimal("12720")
    assert report["payment_count"] == 3

    first, second = report["by_category"]  # biggest category comes first
    assert first["category"] == "Rent"
    assert Decimal(first["total"]) == Decimal("12000")
    assert first["percent"] == 94.3
    assert second["category"] == "Food"
    assert Decimal(second["total"]) == Decimal("720")
    assert second["count"] == 2
    assert second["percent"] == 5.7


def test_empty_month_returns_zero(client):
    report = client.get("/reports/monthly", params={"month": "2026-09"}).json()

    assert Decimal(report["total"]) == 0
    assert report["payment_count"] == 0
    assert report["by_category"] == []


def test_payments_land_in_the_right_month(client):
    food = make_category(client, "Food")
    add_payment(client, food, 100, "2026-10-31")  # last day of October
    add_payment(client, food, 200, "2026-11-01")  # first day of November

    october = client.get("/reports/monthly", params={"month": "2026-10"}).json()
    november = client.get("/reports/monthly", params={"month": "2026-11"}).json()

    assert Decimal(october["total"]) == 100
    assert Decimal(november["total"]) == 200


def test_daily_totals_add_up_per_day(client):
    food = make_category(client, "Food")
    add_payment(client, food, 100, "2026-11-01")
    add_payment(client, food, 50, "2026-11-01")
    add_payment(client, food, 20, "2026-11-03")

    report = client.get("/reports/daily", params={"month": "2026-11"}).json()

    days = {day["date"]: Decimal(day["total"]) for day in report["days"]}
    assert days == {"2026-11-01": Decimal("150"), "2026-11-03": Decimal("20")}


def test_compare_with_previous_month(client):
    food = make_category(client, "Food")
    add_payment(client, food, 1000, "2026-10-10")
    add_payment(client, food, 1100, "2026-11-10")

    result = client.get("/reports/compare", params={"month": "2026-11"}).json()

    assert result["previous_month"] == "2026-10"
    assert Decimal(result["difference"]) == 100
    assert result["percent_change"] == 10.0


def test_compare_when_previous_month_is_empty(client):
    food = make_category(client, "Food")
    add_payment(client, food, 500, "2026-11-10")

    result = client.get("/reports/compare", params={"month": "2026-11"}).json()

    assert Decimal(result["previous_total"]) == 0
    assert result["percent_change"] is None  # can't divide by zero


def test_compare_across_a_year_boundary(client):
    food = make_category(client, "Food")
    add_payment(client, food, 500, "2025-12-15")
    add_payment(client, food, 250, "2026-01-15")

    result = client.get("/reports/compare", params={"month": "2026-01"}).json()

    assert result["previous_month"] == "2025-12"
    assert result["percent_change"] == -50.0