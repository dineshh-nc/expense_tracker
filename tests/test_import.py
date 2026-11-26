CSV = (
    "date,description,amount,payment_method\n"
    "2026-11-20,Swiggy order,420.00,UPI\n"
    "2026-11-21,Uber ride,180.00,UPI\n"
    "2026-11-23,Unknown shop,-5,UPI\n"
).encode()


def upload(client, content=CSV, name="statement.csv"):
    return client.post("/import/csv", files={"file": (name, content, "text/csv")})


def test_import_valid_and_bad_rows(client):
    result = upload(client).json()

    assert result["imported"] == 2
    assert result["skipped_duplicates"] == 0
    assert result["errors"] == [{"row": 4, "reason": "amount must be greater than 0"}]


def test_importing_twice_skips_duplicates(client):
    upload(client)
    second = upload(client).json()

    assert second["imported"] == 0
    assert second["skipped_duplicates"] == 2
    listed = client.get("/transactions", params={"month": "2026-11"}).json()
    assert len(listed) == 2


def test_import_creates_categories_from_keywords(client):
    upload(client)
    names = {c["name"] for c in client.get("/categories").json()}

    assert {"Food", "Travel"} <= names


def test_non_csv_file_is_rejected(client):
    response = upload(client, content=b"hello", name="notes.txt")

    assert response.status_code == 400


def test_missing_columns_return_400(client):
    response = upload(client, content=b"date,amount\n2026-11-20,100\n")

    assert response.status_code == 400
    assert "Missing columns" in response.json()["detail"]