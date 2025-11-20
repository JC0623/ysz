"""FactLedger 테스트"""

import pytest
from datetime import date
from decimal import Decimal

from src.core import Fact, FactLedger


class TestFactLedgerCreation:
    """FactLedger 생성 테스트"""

    def test_create_with_dict(self):
        """딕셔너리로 FactLedger 생성"""
        ledger = FactLedger.create({
            "acquisition_date": Fact(
                value=date(2020, 1, 1),
                is_confirmed=True,
                entered_by="김세무사"
            ),
            "disposal_price": Decimal("700000000")  # 자동 래핑
        }, created_by="김세무사")

        assert ledger.acquisition_date.value == date(2020, 1, 1)
        assert ledger.acquisition_date.is_confirmed is True

        # 자동 래핑된 필드
        assert ledger.disposal_price.value == Decimal("700000000")
        assert isinstance(ledger.disposal_price, Fact)
        assert ledger.disposal_price.entered_by == "김세무사"

    def test_create_empty_ledger(self):
        """빈 FactLedger 생성"""
        ledger = FactLedger.create({}, created_by="system")

        assert ledger.acquisition_date is None
        assert ledger.disposal_price is None
        assert ledger.is_frozen is False


class TestFactLedgerFreeze:
    """FactLedger freeze 테스트"""

    def test_freeze_with_all_required_fields(self):
        """필수 필드가 모두 확정된 경우 freeze 성공"""
        ledger = FactLedger.create({
            "acquisition_date": Fact(
                value=date(2020, 1, 1),
                is_confirmed=True,
                confidence=1.0,
                entered_by="user"
            ),
            "acquisition_price": Fact(
                value=Decimal("500000000"),
                is_confirmed=True,
                confidence=1.0,
                entered_by="user"
            ),
            "disposal_date": Fact(
                value=date(2023, 12, 31),
                is_confirmed=True,
                confidence=1.0,
                entered_by="user"
            ),
            "disposal_price": Fact(
                value=Decimal("700000000"),
                is_confirmed=True,
                confidence=1.0,
                entered_by="user"
            )
        })

        ledger.freeze()

        assert ledger.is_frozen is True

    def test_freeze_without_required_field(self):
        """필수 필드가 없는 경우 freeze 실패"""
        ledger = FactLedger.create({
            "acquisition_date": Fact(
                value=date(2020, 1, 1),
                is_confirmed=True,
                confidence=1.0,
                entered_by="user"
            )
            # disposal_price 없음
        })

        with pytest.raises(ValueError, match="필수 필드.*설정되지 않았습니다"):
            ledger.freeze()

    def test_freeze_with_unconfirmed_field(self):
        """확정되지 않은 필드가 있는 경우 freeze 실패"""
        ledger = FactLedger.create({
            "acquisition_date": Fact(
                value=date(2020, 1, 1),
                is_confirmed=True,
                confidence=1.0,
                entered_by="user"
            ),
            "acquisition_price": Fact(
                value=Decimal("500000000"),
                is_confirmed=False,  # 확정 안 됨
                confidence=0.9,
                entered_by="user"
            ),
            "disposal_date": Fact(
                value=date(2023, 12, 31),
                is_confirmed=True,
                confidence=1.0,
                entered_by="user"
            ),
            "disposal_price": Fact(
                value=Decimal("700000000"),
                is_confirmed=True,
                confidence=1.0,
                entered_by="user"
            )
        })

        with pytest.raises(ValueError, match="확정되지 않았습니다"):
            ledger.freeze()

    def test_cannot_freeze_twice(self):
        """이미 확정된 ledger는 다시 freeze 불가"""
        ledger = FactLedger.create({
            "acquisition_date": Fact(value=date(2020, 1, 1), is_confirmed=True, confidence=1.0, entered_by="user"),
            "acquisition_price": Fact(value=Decimal("500000000"), is_confirmed=True, confidence=1.0, entered_by="user"),
            "disposal_date": Fact(value=date(2023, 12, 31), is_confirmed=True, confidence=1.0, entered_by="user"),
            "disposal_price": Fact(value=Decimal("700000000"), is_confirmed=True, confidence=1.0, entered_by="user")
        })

        ledger.freeze()

        with pytest.raises(ValueError, match="이미 확정된"):
            ledger.freeze()


class TestFactLedgerUpdate:
    """FactLedger 업데이트 테스트"""

    def test_update_field_before_freeze(self):
        """freeze 전에는 필드 업데이트 가능"""
        ledger = FactLedger.create({
            "disposal_price": Decimal("700000000")
        })

        new_fact = Fact(value=Decimal("750000000"), entered_by="김세무사")
        ledger.update_field("disposal_price", new_fact)

        assert ledger.disposal_price.value == Decimal("750000000")

    def test_cannot_update_after_freeze(self):
        """freeze 후에는 필드 업데이트 불가"""
        ledger = FactLedger.create({
            "acquisition_date": Fact(value=date(2020, 1, 1), is_confirmed=True, confidence=1.0, entered_by="user"),
            "acquisition_price": Fact(value=Decimal("500000000"), is_confirmed=True, confidence=1.0, entered_by="user"),
            "disposal_date": Fact(value=date(2023, 12, 31), is_confirmed=True, confidence=1.0, entered_by="user"),
            "disposal_price": Fact(value=Decimal("700000000"), is_confirmed=True, confidence=1.0, entered_by="user")
        })

        ledger.freeze()

        with pytest.raises(ValueError, match="확정된 FactLedger는 수정할 수 없습니다"):
            ledger.update_field("disposal_price", Fact(value=Decimal("750000000"), entered_by="user"))


class TestFactLedgerValidation:
    """FactLedger 유효성 검증 테스트"""

    def test_disposal_date_before_acquisition_date(self):
        """처분일이 취득일보다 이전인 경우 에러"""
        ledger = FactLedger.create({
            "acquisition_date": Fact(value=date(2023, 1, 1), is_confirmed=True, confidence=1.0, entered_by="user"),
            "acquisition_price": Fact(value=Decimal("500000000"), is_confirmed=True, confidence=1.0, entered_by="user"),
            "disposal_date": Fact(value=date(2022, 1, 1), is_confirmed=True, confidence=1.0, entered_by="user"),  # 취득일보다 이전
            "disposal_price": Fact(value=Decimal("700000000"), is_confirmed=True, confidence=1.0, entered_by="user")
        })

        with pytest.raises(ValueError, match="처분일은 취득일보다 이전일 수 없습니다"):
            ledger.freeze()

    def test_negative_prices(self):
        """음수 금액 검증"""
        ledger = FactLedger.create({
            "acquisition_date": Fact(value=date(2020, 1, 1), is_confirmed=True, confidence=1.0, entered_by="user"),
            "acquisition_price": Fact(value=Decimal("-500000000"), is_confirmed=True, confidence=1.0, entered_by="user"),  # 음수
            "disposal_date": Fact(value=date(2023, 12, 31), is_confirmed=True, confidence=1.0, entered_by="user"),
            "disposal_price": Fact(value=Decimal("700000000"), is_confirmed=True, confidence=1.0, entered_by="user")
        })

        with pytest.raises(ValueError, match="취득가액은 음수일 수 없습니다"):
            ledger.freeze()


class TestFactLedgerCalculations:
    """FactLedger 계산 테스트"""

    def test_capital_gain_calculation(self):
        """양도차익 계산"""
        ledger = FactLedger.create({
            "acquisition_price": Fact(value=Decimal("500000000"), entered_by="user"),
            "disposal_price": Fact(value=Decimal("700000000"), entered_by="user"),
            "acquisition_cost": Fact(value=Decimal("5000000"), entered_by="user"),
            "disposal_cost": Fact(value=Decimal("3000000"), entered_by="user"),
            "improvement_cost": Fact(value=Decimal("10000000"), entered_by="user")
        })

        expected_gain = Decimal("700000000") - (
            Decimal("500000000") + Decimal("5000000") +
            Decimal("3000000") + Decimal("10000000")
        )

        assert ledger.capital_gain == expected_gain
        assert ledger.capital_gain == Decimal("182000000")

    def test_holding_period_calculation(self):
        """보유기간 계산"""
        ledger = FactLedger.create({
            "acquisition_date": Fact(value=date(2020, 1, 1), entered_by="user"),
            "disposal_date": Fact(value=date(2023, 12, 31), entered_by="user")
        })

        assert ledger.holding_period_years == 4


class TestFactLedgerConfidenceTracking:
    """FactLedger 신뢰도 추적 테스트"""

    def test_get_confidence_summary(self):
        """신뢰도 요약 조회"""
        ledger = FactLedger.create({
            "acquisition_price": Fact(value=Decimal("500000000"), confidence=1.0, entered_by="user"),
            "disposal_price": Fact(value=Decimal("700000000"), confidence=0.8, entered_by="user")
        })

        summary = ledger.get_confidence_summary()

        assert summary['acquisition_price'] == 1.0
        assert summary['disposal_price'] == 0.8

    def test_get_unconfirmed_fields(self):
        """확정되지 않은 필드 조회"""
        ledger = FactLedger.create({
            "acquisition_price": Fact(value=Decimal("500000000"), is_confirmed=True, confidence=1.0, entered_by="user"),
            "disposal_price": Fact(value=Decimal("700000000"), is_confirmed=False, confidence=0.9, entered_by="user")
        })

        unconfirmed = ledger.get_unconfirmed_fields()

        assert 'disposal_price' in unconfirmed
        assert 'acquisition_price' not in unconfirmed


class TestFactLedgerRealWorldScenarios:
    """실제 시나리오 테스트"""

    def test_apartment_transaction_workflow(self):
        """아파트 거래 워크플로우"""
        # 1. 초기 데이터 입력 (일부는 추정값)
        ledger = FactLedger.create({
            "asset_type": Fact.create_user_input(
                value="부동산",
                entered_by="김세무사",
                is_confirmed=True
            ),
            "acquisition_date": Fact.create_user_input(
                value=date(2020, 1, 1),
                entered_by="김세무사",
                is_confirmed=True
            ),
            "acquisition_price": Fact.create_estimated(
                value=Decimal("500000000"),
                confidence=0.8,
                notes="과거 시세 기반 추정"
            ),
            "disposal_date": Fact.create_user_input(
                value=date(2023, 12, 31),
                entered_by="김세무사",
                is_confirmed=True
            ),
            "disposal_price": Fact.create_user_input(
                value=Decimal("700000000"),
                entered_by="김세무사",
                is_confirmed=True
            )
        }, created_by="김세무사")

        # 확정되지 않은 필드 확인
        unconfirmed = ledger.get_unconfirmed_fields()
        assert 'acquisition_price' in unconfirmed

        # 2. 추정값을 확정값으로 변경
        confirmed_price = ledger.acquisition_price.confirm(
            confirmed_by="김세무사",
            notes="등기부등본 확인 완료"
        )
        ledger.update_field('acquisition_price', confirmed_price)

        # 3. 모든 필드 확정 후 freeze
        ledger.freeze()

        assert ledger.is_frozen is True
        assert ledger.capital_gain == Decimal("200000000")

    def test_version_management(self):
        """버전 관리 테스트"""
        ledger_v1 = FactLedger.create({
            "disposal_price": Fact(value=Decimal("700000000"), entered_by="user")
        })

        assert ledger_v1.version == 1

        # 새 버전 생성
        ledger_v2 = ledger_v1.create_new_version(
            disposal_price=Fact(value=Decimal("750000000"), entered_by="user")
        )

        assert ledger_v1.disposal_price.value == Decimal("700000000")
        assert ledger_v2.disposal_price.value == Decimal("750000000")
        assert ledger_v2.version == 2
