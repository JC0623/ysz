"""TaxCalculator 테스트"""

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
        assert 'tax_rates' in engine.rules
        assert 'deductions' in engine.rules

    def test_find_basic_long_term_rate(self):
        """기본 장기보유 세율 찾기"""
        engine = RuleEngine()

        rule = engine.find_applicable_tax_rate(
            holding_period_years=3,
            is_adjusted_area=False
        )

        assert rule['rate'] == 0.06
        assert '일반지역' in rule['description']

    def test_find_basic_short_term_rate(self):
        """기본 단기보유 세율 찾기"""
        engine = RuleEngine()

        rule = engine.find_applicable_tax_rate(
            holding_period_years=0,
            is_adjusted_area=False
        )

        assert rule['rate'] == 0.42
        assert '일반지역' in rule['description']

    def test_find_adjusted_area_very_short_rate(self):
        """조정지역 초단기 세율 찾기"""
        engine = RuleEngine()

        rule = engine.find_applicable_tax_rate(
            holding_period_years=0,
            is_adjusted_area=True
        )

        assert rule['rate'] == 0.70
        assert '조정대상지역' in rule['description']

    def test_find_adjusted_area_short_rate(self):
        """조정지역 단기 세율 찾기"""
        engine = RuleEngine()

        rule = engine.find_applicable_tax_rate(
            holding_period_years=1,
            is_adjusted_area=True
        )

        assert rule['rate'] == 0.60
        assert '조정대상지역' in rule['description']

    def test_calculate_long_term_deduction_rate(self):
        """장기보유특별공제율 계산"""
        engine = RuleEngine()

        assert engine.calculate_long_term_deduction_rate(2) == 0.0  # 3년 미만
        assert engine.calculate_long_term_deduction_rate(3) == 0.06
        assert engine.calculate_long_term_deduction_rate(5) == 0.10
        assert engine.calculate_long_term_deduction_rate(10) == 0.20
        assert engine.calculate_long_term_deduction_rate(15) == 0.30


class TestTaxCalculatorBasic:
    """TaxCalculator 기본 케이스 테스트"""

    def test_basic_case_3_years(self):
        """기본 케이스: 일반지역, 3년 보유, 주택

        - 취득가: 5억원
        - 양도가: 8억원
        - 보유기간: 3년
        - 예상 세율: 6%
        """
        # 1. FactLedger 생성
        ledger = FactLedger.create({
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

        # 장기보유특별공제 = 3억 × 6% = 1800만원
        assert result.long_term_deduction == Decimal("18000000")

        # 과세표준 = 3억 - 1800만 = 2억8200만
        assert result.taxable_income == Decimal("282000000")

        # 세율 = 6%
        assert result.tax_rate == 0.06

        # 계산세액 = 2억8200만 × 6% = 1692만원
        assert result.calculated_tax == Decimal("16920000")

        # 최종세액 (비과세 없음)
        assert result.final_tax == Decimal("16920000")

        # 계산 추적 확인
        assert len(result.traces) > 0
        assert result.rule_version == "2024.11"

    def test_heavy_tax_case(self):
        """중과세 케이스: 조정지역, 1년 미만 보유

        - 취득가: 10억원
        - 양도가: 15억원
        - 보유기간: 6개월
        - 예상 세율: 70%
        """
        # 1. FactLedger 생성 (6개월 = 약 0년)
        ledger = FactLedger.create({
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
        result = calculator.calculate(ledger, is_adjusted_area=True)

        # 4. 검증
        # 양도소득 = 15억 - 10억 = 5억
        assert result.transfer_income == Decimal("500000000")

        # 장기보유특별공제 = 0 (보유기간 3년 미만)
        assert result.long_term_deduction == Decimal("0")

        # 과세표준 = 5억
        assert result.taxable_income == Decimal("500000000")

        # 세율 = 70%
        assert result.tax_rate == 0.70

        # 계산세액 = 5억 × 70% = 3억5천만원
        assert result.calculated_tax == Decimal("350000000")

        # 최종세액
        assert result.final_tax == Decimal("350000000")


class TestTaxCalculatorWithExpenses:
    """필요경비 포함 테스트"""

    def test_with_all_expenses(self):
        """모든 필요경비 포함"""
        ledger = FactLedger.create({
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

        # 양도소득 = 8억 - 5억 - 500만 - 300만 - 1000만 = 2억8200만
        expected_income = Decimal("800000000") - Decimal("500000000") - Decimal("5000000") - Decimal("3000000") - Decimal("10000000")
        assert result.transfer_income == expected_income
        assert result.transfer_income == Decimal("282000000")


class TestTaxCalculatorExemption:
    """비과세 테스트"""

    def test_one_house_exemption(self):
        """1세대 1주택 비과세"""
        ledger = FactLedger.create({
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
        assert result.exemption_amount == result.calculated_tax
        assert result.final_tax == Decimal("0")


class TestCalculationTrace:
    """계산 추적 테스트"""

    def test_trace_recording(self):
        """계산 과정 추적 기록"""
        ledger = FactLedger.create({
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
        assert 'calculate_taxable_income' in step_names
        assert 'apply_tax_rate' in step_names

        # 각 추적에 법적 근거 포함 확인
        for trace in result.traces:
            if trace.step_name == 'calculate_transfer_income':
                assert trace.legal_basis is not None
                assert '소득세법' in trace.legal_basis

    def test_result_summary(self):
        """결과 요약 출력"""
        ledger = FactLedger.create({
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
            is_adjusted_area=False
        )

        # 양도소득 = 3억
        # 장기보유공제 = 3억 × 6% = 1800만
        # 과세표준 = 2억8200만
        # 세액 = 2억8200만 × 6% = 1692만
        expected = Decimal("16920000")
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
