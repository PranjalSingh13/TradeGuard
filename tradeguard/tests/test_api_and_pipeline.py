import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from tradeguard.api.app import app
from tradeguard.core.exceptions import PaymentLedgerError
from tradeguard.db.models import Base, Shipment
from tradeguard.db.session import get_db
from tradeguard.payments.ledger import LedgerService

# Setup isolated test database in memory with StaticPool to share connection across threads
TEST_DB_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_health_and_metrics():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

    metrics_res = client.get("/metrics")
    assert metrics_res.status_code == 200
    assert "t_low" in metrics_res.json()


def test_stateless_ml_endpoints():
    # 1. Classify
    bol_sample = "BILL OF LADING NON-NEGOTIABLE SHIPPED ON BOARD CSQU3054383 PORT OF DISCHARGE"
    c_res = client.post("/api/v1/ml/classify", json={"text": bol_sample})
    assert c_res.status_code == 200
    assert c_res.json()["predicted_type"] == "bill_of_lading"

    # 2. Extract
    extract_sample = """
    BILL OF LADING NO: MEDU1234567
    CONTAINER NUMBER: CSQU3054383
    GROSS WEIGHT: 18450.5 KG
    PACKAGES: 450 CARTONS
    PORT OF LOADING: INNSA - Nhava Sheva
    PORT OF DISCHARGE: NLRTM - Rotterdam
    """
    e_res = client.post("/api/v1/ml/extract", json={"text": extract_sample, "document_type": "bill_of_lading"})
    assert e_res.status_code == 200
    data = e_res.json()["fields"]
    assert data["container_number"] == "CSQU3054383"
    assert data["gross_weight_kg"] == 18450.5
    assert data["package_count"] == 450


def test_user_registration_and_login():
    email = "trader@example.com"
    reg_res = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepassword123", "role": "buyer"},
    )
    assert reg_res.status_code == 201
    token = reg_res.json()["access_token"]
    assert len(token) > 20

    # Login
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepassword123"},
    )
    assert login_res.status_code == 200
    assert login_res.json()["role"] == "buyer"


def test_ledger_anti_double_spend():
    db = TestingSessionLocal()
    # Create mock shipment
    shipment = Shipment(
        reference="TG-TEST-LEDGER-001",
        buyer_id="b1",
        seller_id="s1",
        declared_amount_minor=100000,
        currency="USD",
        status="funds_held",
    )
    db.add(shipment)
    db.commit()

    ledger = LedgerService(db)
    payment_id = "pay_test_001"

    # 1. First release succeeds
    ledger.record_release(shipment.id, payment_id, 100000)

    # 2. Attempting a second release or refund on same payment must raise PaymentLedgerError
    with pytest.raises(PaymentLedgerError):
        ledger.record_release(shipment.id, payment_id, 100000)

    with pytest.raises(PaymentLedgerError):
        ledger.record_refund(shipment.id, payment_id, 100000)

    db.close()
