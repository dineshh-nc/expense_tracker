from decimal import Decimal

CSV = (
    "date,description,amount,payment_method\n"
    "2026-11-20,Swiggy order,420.00,UPI\n"
    "2026-11-21,Uber ride,180.00,UPI\n"
).encode()


def make_category(client, name="Food"):
    return client.post("/categories", json={"name": name}).json()["id"]


def add_payment(client, category_id, amount=100, date="2026-11-10"):
    response = client.post(
        "/transactions",
        json={"amount": amount, "date": date, "category_id": category_id},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_users_only_see_their_own_payments(client, other_client):
    category_id = make_category(client)
    add_payment(client, category_id)

    mine = client.get("/transactions", params={"month": "2026-11"}).json()
    theirs = other_client.get("/transactions", params={"month": "2026-11"}).json()

    assert len(mine) == 1
    assert theirs == []


def test_cannot_read_edit_or_delete_someone_elses_payment(client, other_client):
    payment_id = add_payment(client, make_category(client))

    assert other_client.get(f"/transactions/{payment_id}").status_code == 404
    assert other_client.patch(f"/transactions/{payment_id}", json={"amount": 1}).status_code == 404
    assert other_client.delete(f"/transactions/{payment_id}").status_code == 404

    # The owner's payment is untouched
    still_there = client.get(f"/transactions/{payment_id}")
    assert still_there.status_code == 200
    assert still_there.json()["amount"] == "100.00"


def test_reports_only_count_own_payments(client, other_client):
    category_id = make_category(client)
    add_payment(client, category_id, amount=500)
    add_payment(other_client, category_id, amount=900)

    mine = client.get("/reports/monthly", params={"month": "2026-11"}).json()
    theirs = other_client.get("/reports/monthly", params={"month": "2026-11"}).json()

    assert Decimal(mine["total"]) == 500
    assert Decimal(theirs["total"]) == 900


def test_same_csv_can_be_imported_by_two_users(client, other_client):
    def upload(test_client):
        return test_client.post(
            "/import/csv", files={"file": ("statement.csv", CSV, "text/csv")}
        ).json()

    first = upload(client)
    second = upload(other_client)

    # Duplicate detection is per user, so the second user's rows are not "duplicates"
    assert first["imported"] == 2
    assert second["imported"] == 2
    assert second["skipped_duplicates"] == 0