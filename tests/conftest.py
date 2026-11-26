import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models  # noqa: F401  (makes sure the tables are known)
from app.database import Base, get_db, settings
from app.main import app

# Same server and password as your real database, but the test database
TEST_URL = settings.database_url.rsplit("/", 1)[0] + "/expense_tracker_test"
engine = create_engine(TEST_URL)
TestingSession = sessionmaker(bind=engine, autoflush=False)


@pytest.fixture(autouse=True)
def clean_database():
    # Safety check: never wipe anything that isn't a test database
    assert engine.url.database.endswith("_test")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture(autouse=True)
def use_test_database(clean_database):
    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()


def register_and_login(test_client, email="user@example.com", password="testpass123"):
    response = test_client.post("/auth/register", json={"email": email, "password": password})
    assert response.status_code == 201
    response = test_client.post("/auth/login", data={"username": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def anonymous_client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        test_client.headers.update(register_and_login(test_client))
        yield test_client


@pytest.fixture
def other_client():
    with TestClient(app) as test_client:
        test_client.headers.update(register_and_login(test_client, email="other@example.com"))
        yield test_client