def make_category(client, name="Food"):
    return client.post("/categories", json={"name": name}).json()["id"]


def test_health(client):
    assert client.get("/").json() == {"status": "ok"}


def test_add_and_list_payment(client):
    category_id = make_category(client)
    response = client.post(
        "/transactions",
        json={
            "amount": 250.50,
            "date": "2026-11-22",
            "description": "Lunch",
            "payment_method": "UPI",
            "category_id": category_id,
        },
    )
    assert response.status_code == 201

    listed = client.get("/transactions", params={"month": "2026-11"}).json()
    assert len(listed) == 1
    assert listed[0]["amount"] == "250.50"


def test_negative_amount_is_rejected(client):
    category_id = make_category(client)
    response = client.post(
        "/transactions",
        json={"amount": -5, "date": "2026-11-22", "category_id": category_id},
    )
    assert response.status_code == 422


def test_unknown_category_is_rejected(client):
    response = client.post(
        "/transactions",
        json={"amount": 10, "date": "2026-11-22", "category_id": 999},
    )
    assert response.status_code == 400


def test_update_payment(client):
    category_id = make_category(client)
    created = client.post(
        "/transactions",
        json={"amount": 100, "date": "2026-11-22", "category_id": category_id},
    ).json()

    response = client.patch(f"/transactions/{created['id']}", json={"amount": 300})

    assert response.status_code == 200
    assert response.json()["amount"] == "300.00"


def test_delete_payment(client):
    category_id = make_category(client)
    created = client.post(
        "/transactions",
        json={"amount": 100, "date": "2026-11-22", "category_id": category_id},
    ).json()

    assert client.delete(f"/transactions/{created['id']}").status_code == 204
    assert client.get(f"/transactions/{created['id']}").status_code == 404