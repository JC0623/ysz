"""통합 테스트: 전체 워크플로우 End-to-End 테스트"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import date
from decimal import Decimal

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


# 테스트용 앱
app = FastAPI()
app.include_router(facts.router, prefix="/api/v1/facts", tags=["사실관계"])
app.include_router(calculate.router, prefix="/api/v1/calculate", tags=["세금계산"])
app.dependency_overrides[get_db] = override_get_db

# 테이블 생성
Base.metadata.create_all(bind=engine)

# 테스트 클라이언트
client = TestClient(app)


@pytest.fixture(scope="function", autouse=True)
def cleanup_database():
    """각 테스트 후 데이터 정리"""
    yield
    db = TestingSessionLocal()
    try:
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


class TestCompleteCalculationFlow:
    """완전한 세금 계산 플로우 통합 테스트"""

    def test_complete_tax_calculation_flow(self):
        """사실관계 수집 → 확인 → 계산 → 결과 조회 전체 플로우"""

        # 1단계: 사실관계 수집
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
            "notes": "통합 테스트 - 완전한 플로우"
        }

        collect_response = client.post("/api/v1/facts/collect", json=collect_request)
        assert collect_response.status_code == 200

        collect_data = collect_response.json()
        transaction_id = collect_data["transaction_id"]

        # 수집된 사실 검증
        assert transaction_id > 0
        assert collect_data["status"] == "draft"
        assert len(collect_data["facts"]) >= 5
        assert len(collect_data["missing_fields"]) == 0  # 필수 필드 모두 제공

        # 2단계: 거래 정보 확인
        get_response = client.get(f"/api/v1/facts/{transaction_id}")
        assert get_response.status_code == 200
        assert get_response.json()["status"] == "draft"

        # 3단계: 사실관계 확인
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

        confirm_data = confirm_response.json()
        assert confirm_data["transaction_id"] == transaction_id
        assert len(confirm_data["confirmed_fields"]) == 5

        # 4단계: 세금 계산
        calc_response = client.post(f"/api/v1/calculate/{transaction_id}")
        assert calc_response.status_code == 200

        calc_data = calc_response.json()

        # 계산 결과 상세 검증
        assert calc_data["transaction_id"] == transaction_id
        assert calc_data["disposal_price"] == 800000000
        assert calc_data["acquisition_price"] == 500000000
        assert calc_data["capital_gain"] == 300000000
        assert calc_data["necessary_expenses"] == 10000000

        # 세액 검증 (0보다 커야 함)
        assert calc_data["total_tax"] > 0
        assert calc_data["calculated_tax"] > 0
        assert calc_data["local_tax"] > 0
        assert calc_data["local_tax"] == calc_data["calculated_tax"] * Decimal("0.1")

        # 세율 검증
        assert calc_data["applied_tax_rate"] is not None
        assert 0 < calc_data["applied_tax_rate"] <= 1

        # 상세 내역 검증
        assert len(calc_data["breakdown"]) > 0
        assert len(calc_data["applied_rules"]) > 0

        # 5단계: 거래 상태 확인
        get_response2 = client.get(f"/api/v1/facts/{transaction_id}")
        assert get_response2.json()["status"] == "calculated"

        # 6단계: 저장된 계산 결과 재조회
        result_response = client.get(f"/api/v1/calculate/{transaction_id}/result")
        assert result_response.status_code == 200

        result_data = result_response.json()
        assert result_data["total_tax"] == calc_data["total_tax"]
        assert result_data["calculated_tax"] == calc_data["calculated_tax"]

        # 7단계: 거래 목록에서 확인
        list_response = client.get("/api/v1/facts/")
        assert list_response.status_code == 200

        list_data = list_response.json()
        assert list_data["total"] >= 1

        # 생성한 거래가 목록에 있는지 확인
        transaction_found = any(
            t["id"] == transaction_id for t in list_data["transactions"]
        )
        assert transaction_found


class TestComplexScenarios:
    """복잡한 세금 계산 시나리오 테스트"""

    def test_adjusted_area_heavy_taxation(self):
        """조정대상지역 다주택 중과세 시나리오"""

        collect_request = {
            "user_data": {
                "acquisition_date": "2024-06-01",
                "acquisition_price": 1000000000,
                "disposal_date": "2025-10-20",
                "disposal_price": 1500000000,
                "asset_type": "residential",
                "necessary_expenses": 20000000,
                "holding_period_years": 1,
                "is_primary_residence": False,
                "number_of_houses": 3,  # 3주택
                "is_adjusted_area": True  # 조정지역
            },
            "created_by": "test_user"
        }

        # 수집
        collect_response = client.post("/api/v1/facts/collect", json=collect_request)
        transaction_id = collect_response.json()["transaction_id"]

        # 계산
        calc_response = client.post(f"/api/v1/calculate/{transaction_id}")
        calc_data = calc_response.json()

        # 중과세율 적용 검증 (조정지역 + 다주택)
        # 1년 미만 보유 + 조정지역 다주택은 최고 세율 적용
        assert calc_data["applied_tax_rate"] >= 0.5  # 최소 50% 이상

        # 양도차익 검증
        expected_gain = 1500000000 - 1000000000 - 20000000
        assert calc_data["capital_gain"] == expected_gain

    def test_primary_residence_exemption_partial(self):
        """1세대1주택 12억 초과 부분과세 시나리오"""

        collect_request = {
            "user_data": {
                "acquisition_date": "2020-01-01",
                "acquisition_price": 800000000,
                "disposal_date": "2025-10-20",
                "disposal_price": 1300000000,  # 12억 초과
                "asset_type": "residential",
                "necessary_expenses": 15000000,
                "holding_period_years": 5,
                "is_primary_residence": True,  # 1세대 1주택
                "number_of_houses": 1,
                "is_adjusted_area": False
            },
            "created_by": "test_user"
        }

        collect_response = client.post("/api/v1/facts/collect", json=collect_request)
        transaction_id = collect_response.json()["transaction_id"]

        calc_response = client.post(f"/api/v1/calculate/{transaction_id}")
        calc_data = calc_response.json()

        # 1세대1주택은 비과세지만, 12억 초과 시 초과분만 과세
        # 시스템이 이를 처리하는지 확인
        assert calc_data["total_tax"] >= 0

    def test_long_term_holding_deduction(self):
        """장기보유특별공제 시나리오"""

        collect_request = {
            "user_data": {
                "acquisition_date": "2010-01-01",
                "acquisition_price": 300000000,
                "disposal_date": "2025-10-20",
                "disposal_price": 600000000,
                "asset_type": "residential",
                "necessary_expenses": 5000000,
                "holding_period_years": 15,  # 15년 보유
                "is_primary_residence": False,
                "number_of_houses": 1,
                "is_adjusted_area": False
            },
            "created_by": "test_user"
        }

        collect_response = client.post("/api/v1/facts/collect", json=collect_request)
        transaction_id = collect_response.json()["transaction_id"]

        calc_response = client.post(f"/api/v1/calculate/{transaction_id}")
        calc_data = calc_response.json()

        # 장기보유특별공제 적용 확인
        # 15년 보유 시 상당한 공제가 있어야 함
        assert calc_data["long_term_deduction"] > 0

        # 공제 후 과세표준이 줄어들었는지 확인
        capital_gain = 600000000 - 300000000 - 5000000
        assert calc_data["taxable_income"] < capital_gain

    def test_minimal_gain_calculation(self):
        """최소 양도차익 시나리오"""

        collect_request = {
            "user_data": {
                "acquisition_date": "2024-01-01",
                "acquisition_price": 500000000,
                "disposal_date": "2025-10-20",
                "disposal_price": 510000000,  # 소폭 상승
                "asset_type": "residential",
                "necessary_expenses": 5000000,
                "holding_period_years": 1,
                "is_primary_residence": False,
                "number_of_houses": 1,
                "is_adjusted_area": False
            },
            "created_by": "test_user"
        }

        collect_response = client.post("/api/v1/facts/collect", json=collect_request)
        transaction_id = collect_response.json()["transaction_id"]

        calc_response = client.post(f"/api/v1/calculate/{transaction_id}")
        calc_data = calc_response.json()

        # 양도차익 = 510억 - 500억 - 5백만 = 5백만
        expected_gain = 510000000 - 500000000 - 5000000
        assert calc_data["capital_gain"] == expected_gain

        # 기본공제 2,500,000원 적용 시 과세표준 확인
        assert calc_data["basic_deduction"] == 2500000


class TestDataConsistency:
    """데이터 일관성 및 무결성 테스트"""

    def test_transaction_lifecycle_states(self):
        """거래 상태 전이 검증"""

        # 초기 상태: draft
        collect_response = client.post("/api/v1/facts/collect", json={
            "user_data": {
                "acquisition_date": "2020-05-01",
                "acquisition_price": 500000000,
                "disposal_date": "2025-10-20",
                "disposal_price": 800000000,
                "asset_type": "residential"
            },
            "created_by": "test"
        })

        transaction_id = collect_response.json()["transaction_id"]

        # draft 상태 확인
        response1 = client.get(f"/api/v1/facts/{transaction_id}")
        assert response1.json()["status"] == "draft"

        # 일부 확인 후에도 draft 유지
        client.post(f"/api/v1/facts/{transaction_id}/confirm", json={
            "field_names": ["acquisition_date"],
            "confirmed_by": "test"
        })

        response2 = client.get(f"/api/v1/facts/{transaction_id}")
        # 모든 필드가 확인되지 않았으므로 여전히 draft
        assert response2.json()["status"] in ["draft", "confirmed"]

        # 계산 후 calculated 상태로 전이
        client.post(f"/api/v1/calculate/{transaction_id}")

        response3 = client.get(f"/api/v1/facts/{transaction_id}")
        assert response3.json()["status"] == "calculated"

    def test_multiple_calculations_same_transaction(self):
        """동일 거래에 대한 여러 번 계산 (재계산)"""

        collect_response = client.post("/api/v1/facts/collect", json={
            "user_data": {
                "acquisition_date": "2020-05-01",
                "acquisition_price": 500000000,
                "disposal_date": "2025-10-20",
                "disposal_price": 800000000,
                "asset_type": "residential"
            },
            "created_by": "test"
        })

        transaction_id = collect_response.json()["transaction_id"]

        # 첫 번째 계산
        calc1_response = client.post(f"/api/v1/calculate/{transaction_id}")
        calc1_data = calc1_response.json()

        # 두 번째 계산 (재계산)
        calc2_response = client.post(f"/api/v1/calculate/{transaction_id}")
        calc2_data = calc2_response.json()

        # 동일한 입력에 대해 동일한 결과 (멱등성)
        assert calc1_data["total_tax"] == calc2_data["total_tax"]
        assert calc1_data["calculated_tax"] == calc2_data["calculated_tax"]

        # 최신 계산 결과 조회 시 마지막 계산 결과 반환
        result_response = client.get(f"/api/v1/calculate/{transaction_id}/result")
        result_data = result_response.json()
        assert result_data["total_tax"] == calc2_data["total_tax"]


class TestErrorHandling:
    """에러 처리 및 복원력 테스트"""

    def test_calculate_without_required_fields(self):
        """필수 필드 누락 시 적절한 에러 처리"""

        # asset_type 누락
        collect_response = client.post("/api/v1/facts/collect", json={
            "user_data": {
                "acquisition_date": "2020-05-01",
                "acquisition_price": 500000000
                # disposal_date, disposal_price, asset_type 누락
            },
            "created_by": "test"
        })

        # Pydantic 검증 실패로 422 에러 예상
        assert collect_response.status_code == 422

    def test_nonexistent_transaction_operations(self):
        """존재하지 않는 거래에 대한 작업"""

        fake_id = 99999

        # 확인 시도
        confirm_response = client.post(
            f"/api/v1/facts/{fake_id}/confirm",
            json={"field_names": ["test"], "confirmed_by": "test"}
        )
        assert confirm_response.status_code == 404

        # 계산 시도
        calc_response = client.post(f"/api/v1/calculate/{fake_id}")
        assert calc_response.status_code == 404

        # 조회 시도
        get_response = client.get(f"/api/v1/facts/{fake_id}")
        assert get_response.status_code == 404
