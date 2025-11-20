"""FactLedger 테스트"""

import pytest
from datetime import date, datetime
from decimal import Decimal

from src.core.fact_ledger import FactLedger


class TestFactLedgerCreation:
    """FactLedger 생성 테스트"""

    def test_create_default_fact_ledger(self):
        """기본값으로 FactLedger 생성"""
        fact = FactLedger()

        assert fact.transaction_id is not None
        assert isinstance(fact.transaction_id, str)
        assert fact.version == 1
        assert fact.created_by == "system"

    def test_create_fact_ledger_with_values(self):
        """값을 지정하여 FactLedger 생성"""
        acquisition_date = date(2020, 1, 1)
        disposal_date = date(2023, 12, 31)

        fact = FactLedger(
            asset_type="부동산",
            asset_description="서울시 강남구 아파트",
            acquisition_date=acquisition_date,
            acquisition_price=Decimal("500000000"),
            disposal_date=disposal_date,
            disposal_price=Decimal("700000000"),
            acquisition_cost=Decimal("5000000"),
            disposal_cost=Decimal("3000000"),
            created_by="user123"
        )

        assert fact.asset_type == "부동산"
        assert fact.acquisition_price == Decimal("500000000")
        assert fact.disposal_price == Decimal("700000000")
        assert fact.created_by == "user123"


class TestFactLedgerImmutability:
    """FactLedger 불변성 테스트"""

    def test_cannot_modify_fields(self):
        """필드를 수정할 수 없음을 확인"""
        fact = FactLedger(asset_type="부동산")

        with pytest.raises(Exception):  # FrozenInstanceError
            fact.asset_type = "주식"

    def test_create_new_version(self):
        """새 버전 생성 테스트"""
        fact = FactLedger(
            asset_type="부동산",
            acquisition_price=Decimal("500000000")
        )

        new_fact = fact.create_new_version(
            acquisition_price=Decimal("550000000")
        )

        # 원본은 변경되지 않음
        assert fact.acquisition_price == Decimal("500000000")
        assert fact.version == 1

        # 새 객체는 변경됨
        assert new_fact.acquisition_price == Decimal("550000000")
        assert new_fact.version == 2
        assert new_fact.asset_type == "부동산"  # 다른 필드는 유지


class TestFactLedgerValidation:
    """FactLedger 유효성 검증 테스트"""

    def test_disposal_date_before_acquisition_date(self):
        """처분일이 취득일보다 이전인 경우 에러"""
        with pytest.raises(ValueError, match="처분일은 취득일보다 이전일 수 없습니다"):
            FactLedger(
                acquisition_date=date(2023, 1, 1),
                disposal_date=date(2022, 1, 1)
            )

    def test_negative_acquisition_price(self):
        """취득가액이 음수인 경우 에러"""
        with pytest.raises(ValueError, match="취득가액은 음수일 수 없습니다"):
            FactLedger(acquisition_price=Decimal("-100"))

    def test_negative_disposal_price(self):
        """처분가액이 음수인 경우 에러"""
        with pytest.raises(ValueError, match="처분가액은 음수일 수 없습니다"):
            FactLedger(disposal_price=Decimal("-100"))

    def test_negative_costs(self):
        """비용이 음수인 경우 에러"""
        with pytest.raises(ValueError, match="취득비용은 음수일 수 없습니다"):
            FactLedger(acquisition_cost=Decimal("-100"))

        with pytest.raises(ValueError, match="처분비용은 음수일 수 없습니다"):
            FactLedger(disposal_cost=Decimal("-100"))

        with pytest.raises(ValueError, match="자본적지출은 음수일 수 없습니다"):
            FactLedger(improvement_cost=Decimal("-100"))

    def test_negative_residence_period(self):
        """거주기간이 음수인 경우 에러"""
        with pytest.raises(ValueError, match="거주기간은 음수일 수 없습니다"):
            FactLedger(residence_period_years=-1)


class TestFactLedgerCalculations:
    """FactLedger 계산 테스트"""

    def test_capital_gain_calculation(self):
        """양도차익 계산 테스트"""
        fact = FactLedger(
            acquisition_price=Decimal("500000000"),
            disposal_price=Decimal("700000000"),
            acquisition_cost=Decimal("5000000"),
            disposal_cost=Decimal("3000000"),
            improvement_cost=Decimal("10000000")
        )

        expected_gain = Decimal("700000000") - (
            Decimal("500000000") +
            Decimal("5000000") +
            Decimal("3000000") +
            Decimal("10000000")
        )

        assert fact.capital_gain == expected_gain
        assert fact.capital_gain == Decimal("182000000")

    def test_capital_loss(self):
        """양도차손 테스트"""
        fact = FactLedger(
            acquisition_price=Decimal("700000000"),
            disposal_price=Decimal("500000000")
        )

        assert fact.capital_gain < 0
        assert fact.capital_gain == Decimal("-200000000")

    def test_holding_period_calculation(self):
        """보유기간 계산 테스트"""
        fact = FactLedger(
            acquisition_date=date(2020, 1, 1),
            disposal_date=date(2023, 12, 31)
        )

        # 약 4년 (1460일 / 365 = 4년)
        assert fact.holding_period_years == 4  # 정수 나눗셈

    def test_zero_holding_period(self):
        """보유기간 0년 테스트"""
        today = date.today()
        fact = FactLedger(
            acquisition_date=today,
            disposal_date=today
        )

        assert fact.holding_period_years == 0


class TestFactLedgerSerialization:
    """FactLedger 직렬화 테스트"""

    def test_to_dict(self):
        """딕셔너리 변환 테스트"""
        fact = FactLedger(
            asset_type="부동산",
            acquisition_price=Decimal("500000000"),
            disposal_price=Decimal("700000000")
        )

        data = fact.to_dict()

        assert isinstance(data, dict)
        assert data['asset_type'] == "부동산"
        assert data['acquisition_price'] == "500000000"
        assert data['disposal_price'] == "700000000"
        assert 'transaction_id' in data
        assert 'version' in data

    def test_str_representation(self):
        """문자열 표현 테스트"""
        fact = FactLedger(
            asset_type="부동산",
            acquisition_date=date(2020, 1, 1),
            disposal_date=date(2023, 12, 31),
            acquisition_price=Decimal("500000000"),
            disposal_price=Decimal("700000000")
        )

        str_repr = str(fact)

        assert "FactLedger" in str_repr
        assert "부동산" in str_repr
        assert "2020-01-01" in str_repr
        assert "2023-12-31" in str_repr


class TestFactLedgerRealWorldScenarios:
    """실제 시나리오 테스트"""

    def test_apartment_transaction(self):
        """아파트 거래 시나리오"""
        # 2020년 5억에 아파트 취득
        # 2023년 7억에 처분
        # 1세대 1주택, 2년 거주
        fact = FactLedger(
            asset_type="부동산",
            asset_description="서울 강남구 아파트 85㎡",
            acquisition_date=date(2020, 1, 1),
            acquisition_price=Decimal("500000000"),
            disposal_date=date(2023, 12, 31),
            disposal_price=Decimal("700000000"),
            acquisition_cost=Decimal("3000000"),  # 취득세, 중개수수료
            disposal_cost=Decimal("2000000"),      # 중개수수료
            improvement_cost=Decimal("5000000"),   # 리모델링
            is_primary_residence=True,
            residence_period_years=2,
            created_by="tax_accountant_kim"
        )

        assert fact.capital_gain == Decimal("190000000")
        assert fact.holding_period_years == 4
        assert fact.is_primary_residence is True

    def test_stock_transaction(self):
        """주식 거래 시나리오"""
        fact = FactLedger(
            asset_type="주식",
            asset_description="삼성전자 보통주 100주",
            acquisition_date=date(2023, 1, 1),
            acquisition_price=Decimal("6000000"),
            disposal_date=date(2023, 6, 30),
            disposal_price=Decimal("8000000"),
            acquisition_cost=Decimal("5000"),  # 수수료
            disposal_cost=Decimal("8000"),     # 수수료
            created_by="investor_lee"
        )

        assert fact.capital_gain == Decimal("1987000")
        assert fact.holding_period_years == 0  # 1년 미만
