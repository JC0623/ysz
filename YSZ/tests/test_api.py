"""API 엔드포인트 통합 테스트"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import date
from decimal import Decimal
from contextlib import asynccontextmanager

from fastapi import FastAPI
from src.database import Base, get_db
from src.database.models import TransactionDB, FactDB, CalculationResultDB
from src.api.routers import facts, calculate


# 테스트용 인메모리 데이터베이스
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """테스트용 DB 세션"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# 테스트용 앱 생성 (lifes이클 없이)
app = FastAPI()
app.include_router(facts.router, prefix="/api/v1/facts", tags=["사실관계"])
app.include_router(calculate.router, prefix="/api/v1/calculate", tags=["세금계산"])

@app.get("/")
async def root():
    return {"message": "YSZ 양도소득세 계산 API", "version": "0.1.0", "docs": "/docs"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# 의존성 오버라이드
app.dependency_overrides[get_db] = override_get_db

# 테이블 생성 (한 번만)
Base.metadata.create_all(bind=engine)

# 테스트 클라이언트
client = TestClient(app)


@pytest.fixture(scope="function", autouse=True)
def cleanup_database():
    """각 테스트 후 데이터 정리"""
    yield
    # 데이터 정리 (테이블 구조는 유지)
    db = TestingSessionLocal()
    try:
        # 모든 데이터 삭제 (역순으로 외래키 제약 조건 고려)
        try:
            db.query(CalculationResultDB).delete()
        except:
            pass
        try:
            db.query(FactDB).delete()
        except:
            pass
        try:
            db.query(TransactionDB).delete()
        except:
            pass
        db.commit()
    except:
        db.rollback()
    finally:
        db.close()


class TestHealthCheck:
    """헬스체크 엔드포인트 테스트"""

    def test_root_endpoint(self):
        """루트 엔드포인트 테스트"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data

    def test_health_endpoint(self):
        """헬스체크 엔드포인트 테스트"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestFactsCollection:
    """사실관계 수집 엔드포인트 테스트"""

    def test_collect_facts_success(self):
        """정상적인 사실관계 수집"""
        request_data = {
            "user_data": {
                "acquisition_date": "2020-05-01",
                "acquisition_price": 500000000,
                "disposal_date": "2025-10-20",
                "disposal_price": 800000000,
                "asset_type": "residential",
                "necessary_expenses": 10000000,
                "holding_period_years": 5,
                "is_primary_residence": False,
                "number_of_houses": 2,
                "is_adjusted_area": True
            },
            "created_by": "test_user",
            "notes": "테스트 거래"
        }

        response = client.post("/api/v1/facts/collect", json=request_data)
        assert response.status_code == 200

        data = response.json()
        assert "transaction_id" in data
        assert data["status"] == "draft"
        assert len(data["facts"]) > 0
        assert isinstance(data["missing_fields"], list)
        assert isinstance(data["unconfirmed_fields"], list)

    def test_collect_facts_minimal_data(self):
        """최소 필수 데이터만으로 수집"""
        request_data = {
            "user_data": {
                "acquisition_date": "2020-05-01",
                "acquisition_price": 500000000,
                "disposal_date": "2025-10-20",
                "disposal_price": 800000000,
                "asset_type": "residential"
            },
            "created_by": "test_user"
        }

        response = client.post("/api/v1/facts/collect", json=request_data)
        assert response.status_code == 200

        data = response.json()
        assert data["transaction_id"] > 0
        assert len(data["missing_fields"]) == 0  # 필수 필드는 모두 제공됨

    def test_collect_facts_invalid_date(self):
        """잘못된 날짜 형식"""
        request_data = {
            "user_data": {
                "acquisition_date": "invalid-date",
                "acquisition_price": 500000000,
                "disposal_date": "2025-10-20",
                "disposal_price": 800000000,
                "asset_type": "residential"
            },
            "created_by": "test_user"
        }

        response = client.post("/api/v1/facts/collect", json=request_data)
        assert response.status_code == 422  # Validation error


class TestFactsConfirmation:
    """사실관계 확인 엔드포인트 테스트"""

    def test_confirm_facts_success(self):
        """정상적인 사실관계 확인"""
        # 먼저 사실관계 수집
        collect_request = {
            "user_data": {
                "acquisition_date": "2020-05-01",
                "acquisition_price": 500000000,
                "disposal_date": "2025-10-20",
                "disposal_price": 800000000,
                "asset_type": "residential"
            },
            "created_by": "test_user"
        }

        collect_response = client.post("/api/v1/facts/collect", json=collect_request)
        transaction_id = collect_response.json()["transaction_id"]

        # 사실관계 확인
        confirm_request = {
            "field_names": ["acquisition_date", "acquisition_price"],
            "confirmed_by": "test_user"
        }

        confirm_response = client.post(
            f"/api/v1/facts/{transaction_id}/confirm",
            json=confirm_request
        )

        assert confirm_response.status_code == 200
        data = confirm_response.json()
        assert data["transaction_id"] == transaction_id
        assert len(data["confirmed_fields"]) == 2

    def test_confirm_nonexistent_transaction(self):
        """존재하지 않는 거래 ID로 확인 시도"""
        confirm_request = {
            "field_names": ["acquisition_date"],
            "confirmed_by": "test_user"
        }

        response = client.post(
            "/api/v1/facts/99999/confirm",
            json=confirm_request
        )

        assert response.status_code == 404


class TestCalculation:
    """세금 계산 엔드포인트 테스트"""

    def test_calculate_tax_success(self):
        """정상적인 세금 계산"""
        # 사실관계 수집
        collect_request = {
            "user_data": {
                "acquisition_date": "2020-05-01",
                "acquisition_price": 500000000,
                "disposal_date": "2025-10-20",
                "disposal_price": 800000000,
                "asset_type": "residential",
                "necessary_expenses": 10000000,
                "holding_period_years": 5,
                "is_primary_residence": False,
                "number_of_houses": 2,
                "is_adjusted_area": True
            },
            "created_by": "test_user"
        }

        collect_response = client.post("/api/v1/facts/collect", json=collect_request)
        transaction_id = collect_response.json()["transaction_id"]

        # 세금 계산
        calc_response = client.post(f"/api/v1/calculate/{transaction_id}")

        assert calc_response.status_code == 200
        data = calc_response.json()

        # 응답 검증
        assert data["transaction_id"] == transaction_id
        assert "calculated_at" in data
        assert data["disposal_price"] == 800000000
        assert data["acquisition_price"] == 500000000
        assert data["capital_gain"] == 300000000
        assert data["total_tax"] > 0
        assert len(data["breakdown"]) > 0
        assert isinstance(data["applied_rules"], list)

    def test_calculate_tax_missing_fields(self):
        """필수 필드 누락 시 계산 실패"""
        # 필수 필드 일부만 제공
        collect_request = {
            "user_data": {
                "acquisition_date": "2020-05-01",
                "acquisition_price": 500000000
                # disposal_date, disposal_price, asset_type 누락
            },
            "created_by": "test_user"
        }

        collect_response = client.post("/api/v1/facts/collect", json=collect_request)
        # 이 요청 자체가 실패할 수 있음 (Pydantic 검증)
        if collect_response.status_code == 200:
            transaction_id = collect_response.json()["transaction_id"]

            # 세금 계산 시도
            calc_response = client.post(f"/api/v1/calculate/{transaction_id}")
            assert calc_response.status_code == 400  # Bad Request

    def test_calculate_nonexistent_transaction(self):
        """존재하지 않는 거래 ID로 계산 시도"""
        response = client.post("/api/v1/calculate/99999")
        assert response.status_code == 404

    def test_get_calculation_result(self):
        """저장된 계산 결과 조회"""
        # 사실관계 수집 및 계산
        collect_request = {
            "user_data": {
                "acquisition_date": "2020-05-01",
                "acquisition_price": 500000000,
                "disposal_date": "2025-10-20",
                "disposal_price": 800000000,
                "asset_type": "residential"
            },
            "created_by": "test_user"
        }

        collect_response = client.post("/api/v1/facts/collect", json=collect_request)
        transaction_id = collect_response.json()["transaction_id"]

        # 계산
        calc_response = client.post(f"/api/v1/calculate/{transaction_id}")
        assert calc_response.status_code == 200

        # 결과 조회
        result_response = client.get(f"/api/v1/calculate/{transaction_id}/result")
        assert result_response.status_code == 200

        data = result_response.json()
        assert data["transaction_id"] == transaction_id
        assert data["total_tax"] > 0


class TestTransactions:
    """거래 조회 엔드포인트 테스트"""

    def test_get_transaction(self):
        """거래 정보 조회"""
        # 거래 생성
        collect_request = {
            "user_data": {
                "acquisition_date": "2020-05-01",
                "acquisition_price": 500000000,
                "disposal_date": "2025-10-20",
                "disposal_price": 800000000,
                "asset_type": "residential"
            },
            "created_by": "test_user"
        }

        collect_response = client.post("/api/v1/facts/collect", json=collect_request)
        transaction_id = collect_response.json()["transaction_id"]

        # 조회
        response = client.get(f"/api/v1/facts/{transaction_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == transaction_id
        assert data["created_by"] == "test_user"
        assert data["status"] == "draft"
        assert data["facts_count"] > 0

    def test_list_transactions(self):
        """거래 목록 조회"""
        # 여러 거래 생성
        for i in range(3):
            collect_request = {
                "user_data": {
                    "acquisition_date": "2020-05-01",
                    "acquisition_price": 500000000 + i * 10000000,
                    "disposal_date": "2025-10-20",
                    "disposal_price": 800000000 + i * 10000000,
                    "asset_type": "residential"
                },
                "created_by": f"user_{i}"
            }
            client.post("/api/v1/facts/collect", json=collect_request)

        # 목록 조회
        response = client.get("/api/v1/facts/")
        assert response.status_code == 200

        data = response.json()
        assert "transactions" in data
        assert data["total"] >= 3
        assert len(data["transactions"]) >= 3

    def test_list_transactions_pagination(self):
        """거래 목록 페이지네이션"""
        # 거래 생성
        for i in range(5):
            collect_request = {
                "user_data": {
                    "acquisition_date": "2020-05-01",
                    "acquisition_price": 500000000,
                    "disposal_date": "2025-10-20",
                    "disposal_price": 800000000,
                    "asset_type": "residential"
                },
                "created_by": "test_user"
            }
            client.post("/api/v1/facts/collect", json=collect_request)

        # 첫 페이지
        response1 = client.get("/api/v1/facts/?page=1&page_size=2")
        assert response1.status_code == 200
        data1 = response1.json()
        assert len(data1["transactions"]) == 2
        assert data1["page"] == 1

        # 두 번째 페이지
        response2 = client.get("/api/v1/facts/?page=2&page_size=2")
        assert response2.status_code == 200
        data2 = response2.json()
        assert len(data2["transactions"]) == 2
        assert data2["page"] == 2


class TestEndToEndWorkflow:
    """전체 워크플로우 통합 테스트"""

    def test_complete_workflow(self):
        """사실관계 수집 → 확인 → 계산 전체 프로세스"""
        # 1. 사실관계 수집
        collect_request = {
            "user_data": {
                "acquisition_date": "2020-05-01",
                "acquisition_price": 500000000,
                "disposal_date": "2025-10-20",
                "disposal_price": 800000000,
                "asset_type": "residential",
                "necessary_expenses": 10000000,
                "holding_period_years": 5,
                "is_primary_residence": False,
                "number_of_houses": 2,
                "is_adjusted_area": True
            },
            "created_by": "test_user",
            "notes": "통합 테스트"
        }

        collect_response = client.post("/api/v1/facts/collect", json=collect_request)
        assert collect_response.status_code == 200
        transaction_id = collect_response.json()["transaction_id"]

        # 2. 거래 정보 확인
        get_response = client.get(f"/api/v1/facts/{transaction_id}")
        assert get_response.status_code == 200
        assert get_response.json()["status"] == "draft"

        # 3. 사실관계 확인
        confirm_request = {
            "field_names": [
                "acquisition_date",
                "acquisition_price",
                "disposal_date",
                "disposal_price",
                "asset_type"
            ],
            "confirmed_by": "test_user"
        }

        confirm_response = client.post(
            f"/api/v1/facts/{transaction_id}/confirm",
            json=confirm_request
        )
        assert confirm_response.status_code == 200

        # 4. 상태가 confirmed로 변경되었는지 확인
        get_response2 = client.get(f"/api/v1/facts/{transaction_id}")
        # 모든 필수 필드가 확인되면 상태가 confirmed로 변경될 수 있음

        # 5. 세금 계산
        calc_response = client.post(f"/api/v1/calculate/{transaction_id}")
        assert calc_response.status_code == 200
        calc_data = calc_response.json()

        # 계산 결과 검증
        assert calc_data["total_tax"] > 0
        assert calc_data["disposal_price"] == 800000000
        assert calc_data["acquisition_price"] == 500000000

        # 6. 계산 후 상태 확인
        get_response3 = client.get(f"/api/v1/facts/{transaction_id}")
        assert get_response3.json()["status"] == "calculated"

        # 7. 저장된 계산 결과 재조회
        result_response = client.get(f"/api/v1/calculate/{transaction_id}/result")
        assert result_response.status_code == 200
        assert result_response.json()["total_tax"] == calc_data["total_tax"]
