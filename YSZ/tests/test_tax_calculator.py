"""TaxCalculator 테스트 (누진세율 구조)"""

import pytest
from datetime import date
from decimal import Decimal

from src.core import Fact, FactLedger, TaxCalculator, RuleEngine


class TestRuleEngine:
    """RuleEngine 테스트"""

    def test_load_rules(self):
        """규칙 파일 로드 테스트"""
        engine = RuleEngine()

        assert engine.version == "2024.11"
        assert 'short_term_rates' in engine.rules
        assert 'progressive_tax_brackets' in engine.rules
        assert 'multi_house_surcharge' in engine.rules
        assert 'deductions' in engine.rules

    def test_get_short_term_rate_residential(self):
        """주택 단기보유 세율 조회"""
        engine = RuleEngine()

        # 1년 미만
        rate_info = engine.get_short_term_rate('residential', 0)
        assert rate_info['rate'] == 0.70

        # 1년 이상 2년 미만
        rate_info = engine.get_short_term_rate('residential', 1)
        assert rate_info['rate'] == 0.60

        # 2년 이상은 None
        rate_info = engine.get_short_term_rate('residential', 2)
        assert rate_info is None

    def test_calculate_progressive_tax(self):
        """누진세율 계산 테스트"""
        engine = RuleEngine()

        # 1,400만원 이하: 6%
        rate, deduction, desc = engine.calculate_progressive_tax(Decimal('10000000'))
        assert rate == 0.06
        assert deduction == Decimal('0')

        # 5,000만원 이하: 15%, 누진공제 126만원
        rate, deduction, desc = engine.calculate_progressive_tax(Decimal('30000000'))
        assert rate == 0.15
        assert deduction == Decimal('1260000')

        # 3억원: 38%, 누진공제 1,994만원
        rate, deduction, desc = engine.calculate_progressive_tax(Decimal('300000000'))
        assert rate == 0.38
        assert deduction == Decimal('19940000')

    def test_get_multi_house_surcharge(self):
        """다주택자 중과세율 조회"""
        engine = RuleEngine()

        # 조정지역 + 2주택 + 2년 이상: 20%p 추가
        surcharge = engine.get_multi_house_surcharge(
            house_count=2,
            is_adjusted_area=True,
            holding_period_years=2
        )
        assert surcharge == 0.20

        # 조정지역 + 3주택 + 2년 이상: 30%p 추가
        surcharge = engine.get_multi_house_surcharge(
            house_count=3,
            is_adjusted_area=True,
            holding_period_years=2
        )
        assert surcharge == 0.30

        # 일반지역은 중과 없음
        surcharge = engine.get_multi_house_surcharge(
            house_count=2,
            is_adjusted_area=False,
            holding_period_years=2
        )
        assert surcharge == 0.0

    def test_calculate_long_term_deduction_rate(self):
        """장기보유특별공제율 계산"""
        engine = RuleEngine()

        # 일반 자산
        assert engine.calculate_long_term_deduction_rate(2) == 0.0  # 3년 미만
        assert engine.calculate_long_term_deduction_rate(3) == 0.06
        assert engine.calculate_long_term_deduction_rate(5) == 0.10
        assert engine.calculate_long_term_deduction_rate(10) == 0.20
        assert engine.calculate_long_term_deduction_rate(15) == 0.30

        # 1세대 1주택 (보유 + 거주)
        rate = engine.calculate_long_term_deduction_rate(
            holding_period_years=5,
            is_primary_residence=True,
            residence_period_years=3
        )
        # 보유 5년 16% + 거주 3년 12% = 28%
        assert rate == 0.28

    def test_get_basic_deduction(self):
        """기본공제 조회"""
        engine = RuleEngine()
        assert engine.get_basic_deduction() == Decimal('2500000')

    def test_get_local_tax_rate(self):
        """지방소득세율 조회"""
        engine = RuleEngine()
        assert engine.get_local_tax_rate() == 0.10


class TestTaxCalculatorBasic:
    """TaxCalculator 기본 케이스 테스트"""

    def test_basic_case_3_years(self):
        """기본 케이스: 일반지역, 3년 보유, 주택

        - 취득가: 5억원
        - 양도가: 8억원
        - 보유기간: 3년
        - 자산유형: 주택
        """
        # 1. FactLedger 생성
        ledger = FactLedger.create({
            "asset_type": Fact(
                value="residential",
                is_confirmed=True,
                confidence=1.0,
                entered_by="테스트"
            ),
            "acquisition_date": Fact(
                value=date(2020, 1, 1),
                is_confirmed=True,
                confidence=1.0,
                entered_by="테스트"
            ),
            "acquisition_price": Fact(
                value=Decimal("500000000"),
                is_confirmed=True,
                confidence=1.0,
                entered_by="테스트"
            ),
            "disposal_date": Fact(
                value=date(2023, 1, 1),
                is_confirmed=True,
                confidence=1.0,
                entered_by="테스트"
            ),
            "disposal_price": Fact(
                value=Decimal("800000000"),
                is_confirmed=True,
                confidence=1.0,
                entered_by="테스트"
            )
        })

        # 2. Freeze
        ledger.freeze()

        # 3. 계산
        calculator = TaxCalculator()
        result = calculator.calculate(ledger, is_adjusted_area=False)

        # 4. 검증
        # 양도소득 = 8억 - 5억 = 3억
        assert result.transfer_income == Decimal("300000000")

        # 장기보유특별공제 = 3억 × 6% = 1,800만원
        assert result.long_term_deduction == Decimal("18000000")

        # 양도소득금액 = 3억 - 1,800만 = 2억 8,200만
        assert result.transfer_income_amount == Decimal("282000000")

        # 기본공제 = 250만원
        assert result.basic_deduction == Decimal("2500000")

        # 과세표준 = 2억 8,200만 - 250만 = 2억 7,950만
        assert result.taxable_income == Decimal("279500000")

        # 세율 = 38%, 누진공제 = 1,994만원
        # (3억원 구간: 1.5억 초과 3억 이하)
        assert result.base_tax_rate == 0.38
        assert result.progressive_deduction == Decimal("19940000")

        # 계산세액 = (2억 7,950만 × 38%) - 1,994만 = 8,627만원
        expected_tax = (Decimal("279500000") * Decimal("0.38")) - Decimal("19940000")
        assert result.calculated_tax == expected_tax
        assert result.calculated_tax == Decimal("86270000")

        # 지방소득세 = 8,627만 × 10% = 862.7만원
        assert result.local_tax == Decimal("8627000")

        # 최종세액 = 8,627만 + 862.7만 = 9,489.7만원
        assert result.final_tax == Decimal("94897000")

        # 계산 추적 확인
        assert len(result.traces) > 0
        assert result.rule_version == "2024.11"

    def test_short_term_case(self):
        """단기보유 케이스: 일반지역, 1년 미만 보유, 주택

        - 취득가: 10억원
        - 양도가: 15억원
        - 보유기간: 6개월
        - 자산유형: 주택
        - 예상 세율: 70% (비례세율)
        """
        # 1. FactLedger 생성 (6개월 = 약 0년)
        ledger = FactLedger.create({
            "asset_type": Fact(
                value="residential",
                is_confirmed=True,
                confidence=1.0,
                entered_by="테스트"
            ),
            "acquisition_date": Fact(
                value=date(2023, 1, 1),
                is_confirmed=True,
                confidence=1.0,
                entered_by="테스트"
            ),
            "acquisition_price": Fact(
                value=Decimal("1000000000"),
                is_confirmed=True,
                confidence=1.0,
                entered_by="테스트"
            ),
            "disposal_date": Fact(
                value=date(2023, 7, 1),
                is_confirmed=True,
                confidence=1.0,
                entered_by="테스트"
            ),
            "disposal_price": Fact(
                value=Decimal("1500000000"),
                is_confirmed=True,
                confidence=1.0,
                entered_by="테스트"
            )
        })

        # 2. Freeze
        ledger.freeze()

        # 3. 계산
        calculator = TaxCalculator()
        result = calculator.calculate(ledger, is_adjusted_area=False)

        # 4. 검증
        # 양도소득 = 15억 - 10억 = 5억
        assert result.transfer_income == Decimal("500000000")

        # 장기보유특별공제 = 0 (3년 미만)
        assert result.long_term_deduction == Decimal("0")

        # 양도소득금액 = 5억
        assert result.transfer_income_amount == Decimal("500000000")

        # 기본공제 = 250만원
        assert result.basic_deduction == Decimal("2500000")

        # 과세표준 = 5억 - 250만 = 4억 9,750만
        assert result.taxable_income == Decimal("497500000")

        # 단기보유 비례세율 = 70%
        assert result.base_tax_rate == 0.70
        assert result.progressive_deduction == Decimal("0")  # 비례세율은 누진공제 없음

        # 계산세액 = 4억 9,750만 × 70% = 3억 4,825만원
        expected_tax = Decimal("497500000") * Decimal("0.70")
        assert result.calculated_tax == expected_tax
        assert result.calculated_tax == Decimal("348250000")

        # 지방소득세 = 3억 4,825만 × 10% = 3,482.5만원
        assert result.local_tax == Decimal("34825000")

        # 최종세액 = 3억 4,825만 + 3,482.5만 = 3억 8,307.5만원
        assert result.final_tax == Decimal("383075000")


class TestTaxCalculatorSurcharge:
    """다주택자 중과세 테스트"""

    def test_two_houses_surcharge(self):
        """2주택자 중과세 케이스: 조정지역, 3년 보유"""
        ledger = FactLedger.create({
            "asset_type": Fact(value="residential", is_confirmed=True, confidence=1.0, entered_by="테스트"),
            "acquisition_date": Fact(value=date(2020, 1, 1), is_confirmed=True, confidence=1.0, entered_by="테스트"),
            "acquisition_price": Fact(value=Decimal("500000000"), is_confirmed=True, confidence=1.0, entered_by="테스트"),
            "disposal_date": Fact(value=date(2023, 1, 1), is_confirmed=True, confidence=1.0, entered_by="테스트"),
            "disposal_price": Fact(value=Decimal("800000000"), is_confirmed=True, confidence=1.0, entered_by="테스트"),
            "house_count": Fact(value=2, is_confirmed=True, confidence=1.0, entered_by="테스트")
        })

        ledger.freeze()

        calculator = TaxCalculator()
        result = calculator.calculate(ledger, is_adjusted_area=True)

        # 중과세율 20%p 추가
        assert result.surcharge_rate == 0.20

        # 총 세율 = 38% + 20% = 58%
        total_rate = result.base_tax_rate + result.surcharge_rate
        assert abs(total_rate - 0.58) < 0.0001  # 부동소수점 오차 허용

        # 경고 메시지 확인
        assert len(result.warnings) > 0
        assert any('중과' in w for w in result.warnings)


class TestTaxCalculatorWithExpenses:
    """필요경비 포함 테스트"""

    def test_with_all_expenses(self):
        """모든 필요경비 포함"""
        ledger = FactLedger.create({
            "asset_type": Fact(value="residential", is_confirmed=True, confidence=1.0, entered_by="테스트"),
            "acquisition_date": Fact(value=date(2020, 1, 1), is_confirmed=True, confidence=1.0, entered_by="테스트"),
            "acquisition_price": Fact(value=Decimal("500000000"), is_confirmed=True, confidence=1.0, entered_by="테스트"),
            "disposal_date": Fact(value=date(2023, 1, 1), is_confirmed=True, confidence=1.0, entered_by="테스트"),
            "disposal_price": Fact(value=Decimal("800000000"), is_confirmed=True, confidence=1.0, entered_by="테스트"),
            "acquisition_cost": Fact(value=Decimal("5000000"), is_confirmed=True, confidence=1.0, entered_by="테스트"),
            "disposal_cost": Fact(value=Decimal("3000000"), is_confirmed=True, confidence=1.0, entered_by="테스트"),
            "improvement_cost": Fact(value=Decimal("10000000"), is_confirmed=True, confidence=1.0, entered_by="테스트")
        })

        ledger.freeze()

        calculator = TaxCalculator()
        result = calculator.calculate(ledger)

        # 양도소득 = 8억 - 5억 - 500만 - 300만 - 1,000만 = 2억 8,200만
        expected_income = (
            Decimal("800000000") - Decimal("500000000") -
            Decimal("5000000") - Decimal("3000000") - Decimal("10000000")
        )
        assert result.transfer_income == expected_income
        assert result.transfer_income == Decimal("282000000")


class TestTaxCalculatorExemption:
    """비과세 테스트"""

    def test_one_house_exemption(self):
        """1세대 1주택 비과세 (양도가 12억 이하)"""
        ledger = FactLedger.create({
            "asset_type": Fact(value="residential", is_confirmed=True, confidence=1.0, entered_by="테스트"),
            "acquisition_date": Fact(value=date(2020, 1, 1), is_confirmed=True, confidence=1.0, entered_by="테스트"),
            "acquisition_price": Fact(value=Decimal("500000000"), is_confirmed=True, confidence=1.0, entered_by="테스트"),
            "disposal_date": Fact(value=date(2023, 1, 1), is_confirmed=True, confidence=1.0, entered_by="테스트"),
            "disposal_price": Fact(value=Decimal("800000000"), is_confirmed=True, confidence=1.0, entered_by="테스트"),
            "is_primary_residence": Fact(value=True, is_confirmed=True, confidence=1.0, entered_by="테스트"),
            "residence_period_years": Fact(value=3, is_confirmed=True, confidence=1.0, entered_by="테스트")
        })

        ledger.freeze()

        calculator = TaxCalculator()
        result = calculator.calculate(ledger)

        # 1세대 1주택 요건 충족 (2년 이상 보유 및 거주, 12억원 이하)
        # → 전액 비과세
        assert result.exemption_amount == result.transfer_income
        assert result.calculated_tax == Decimal("0")
        assert result.final_tax == Decimal("0")

    def test_one_house_over_limit_warning(self):
        """1세대 1주택 비과세 한도 초과 (양도가 12억 초과)"""
        ledger = FactLedger.create({
            "asset_type": Fact(value="residential", is_confirmed=True, confidence=1.0, entered_by="테스트"),
            "acquisition_date": Fact(value=date(2020, 1, 1), is_confirmed=True, confidence=1.0, entered_by="테스트"),
            "acquisition_price": Fact(value=Decimal("800000000"), is_confirmed=True, confidence=1.0, entered_by="테스트"),
            "disposal_date": Fact(value=date(2023, 1, 1), is_confirmed=True, confidence=1.0, entered_by="테스트"),
            "disposal_price": Fact(value=Decimal("1500000000"), is_confirmed=True, confidence=1.0, entered_by="테스트"),
            "is_primary_residence": Fact(value=True, is_confirmed=True, confidence=1.0, entered_by="테스트"),
            "residence_period_years": Fact(value=3, is_confirmed=True, confidence=1.0, entered_by="테스트")
        })

        ledger.freeze()

        calculator = TaxCalculator()
        result = calculator.calculate(ledger)

        # 12억 초과 → 초과분 과세 경고
        assert len(result.warnings) > 0
        assert any('비과세 한도' in w for w in result.warnings)


class TestCalculationTrace:
    """계산 추적 테스트"""

    def test_trace_recording(self):
        """계산 과정 추적 기록"""
        ledger = FactLedger.create({
            "asset_type": Fact(value="residential", is_confirmed=True, confidence=1.0, entered_by="테스트"),
            "acquisition_date": Fact(value=date(2020, 1, 1), is_confirmed=True, confidence=1.0, entered_by="테스트"),
            "acquisition_price": Fact(value=Decimal("500000000"), is_confirmed=True, confidence=1.0, entered_by="테스트"),
            "disposal_date": Fact(value=date(2023, 1, 1), is_confirmed=True, confidence=1.0, entered_by="테스트"),
            "disposal_price": Fact(value=Decimal("800000000"), is_confirmed=True, confidence=1.0, entered_by="테스트")
        })

        ledger.freeze()

        calculator = TaxCalculator()
        result = calculator.calculate(ledger)

        # 추적 단계 확인
        step_names = [trace.step_name for trace in result.traces]
        assert 'calculate_transfer_income' in step_names
        assert 'calculate_long_term_deduction' in step_names
        assert 'apply_basic_deduction' in step_names
        assert 'calculate_progressive_tax' in step_names
        assert 'calculate_local_tax' in step_names

        # 각 추적에 법적 근거 포함 확인
        for trace in result.traces:
            if trace.step_name == 'calculate_transfer_income':
                assert trace.legal_basis is not None
                assert '소득세법' in trace.legal_basis

    def test_result_summary(self):
        """결과 요약 출력"""
        ledger = FactLedger.create({
            "asset_type": Fact(value="residential", is_confirmed=True, confidence=1.0, entered_by="테스트"),
            "acquisition_date": Fact(value=date(2020, 1, 1), is_confirmed=True, confidence=1.0, entered_by="테스트"),
            "acquisition_price": Fact(value=Decimal("500000000"), is_confirmed=True, confidence=1.0, entered_by="테스트"),
            "disposal_date": Fact(value=date(2023, 1, 1), is_confirmed=True, confidence=1.0, entered_by="테스트"),
            "disposal_price": Fact(value=Decimal("800000000"), is_confirmed=True, confidence=1.0, entered_by="테스트")
        })

        ledger.freeze()

        calculator = TaxCalculator()
        result = calculator.calculate(ledger)

        # 요약 문자열 생성 확인
        summary = result.get_summary()
        assert '양도소득' in summary
        assert '과세표준' in summary
        assert '최종납부세액' in summary

        # 추적 요약 확인
        trace_summary = result.get_trace_summary()
        assert '계산 과정 추적' in trace_summary


class TestQuickEstimate:
    """간편 추정 테스트"""

    def test_estimate_tax(self):
        """간편 세액 추정"""
        calculator = TaxCalculator()

        estimated_tax = calculator.estimate_tax(
            disposal_price=Decimal("800000000"),
            acquisition_price=Decimal("500000000"),
            holding_period_years=3,
            is_adjusted_area=False,
            asset_type='residential'
        )

        # 양도소득 = 3억
        # 장기보유공제 = 3억 × 6% = 1,800만
        # 양도소득금액 = 2억 8,200만
        # 기본공제 = 250만
        # 과세표준 = 2억 7,950만
        # 세액 = (2억 7,950만 × 38%) - 1,994만 = 8,627만
        # 지방세 = 8,627만 × 10% = 862.7만
        # 총 세액 = 9,489.7만
        expected = Decimal("94897000")
        assert estimated_tax == expected


class TestEdgeCases:
    """예외 케이스 테스트"""

    def test_cannot_calculate_unfrozen_ledger(self):
        """확정되지 않은 FactLedger로 계산 시 에러"""
        ledger = FactLedger.create({
            "disposal_price": Decimal("800000000")
        })

        calculator = TaxCalculator()

        with pytest.raises(ValueError, match="확정되지 않았습니다"):
            calculator.calculate(ledger)

    def test_zero_transfer_income(self):
        """양도소득이 0 이하인 경우"""
        ledger = FactLedger.create({
            "asset_type": Fact(value="residential", is_confirmed=True, confidence=1.0, entered_by="테스트"),
            "acquisition_date": Fact(value=date(2020, 1, 1), is_confirmed=True, confidence=1.0, entered_by="테스트"),
            "acquisition_price": Fact(value=Decimal("800000000"), is_confirmed=True, confidence=1.0, entered_by="테스트"),
            "disposal_date": Fact(value=date(2023, 1, 1), is_confirmed=True, confidence=1.0, entered_by="테스트"),
            "disposal_price": Fact(value=Decimal("800000000"), is_confirmed=True, confidence=1.0, entered_by="테스트")
        })

        ledger.freeze()

        calculator = TaxCalculator()
        result = calculator.calculate(ledger)

        # 양도차익 없음 → 세금 없음
        assert result.transfer_income == Decimal("0")
        assert result.final_tax == Decimal("0")
