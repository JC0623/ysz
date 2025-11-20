"""TaxCalculator: 양도소득세 계산기"""

from decimal import Decimal
from datetime import datetime
from typing import List, Optional

from .fact_ledger import FactLedger
from .calculation_trace import CalculationTrace, CalculationResult
from .rule_engine import RuleEngine


class TaxCalculator:
    """양도소득세 계산기

    FactLedger를 입력받아 세법 규칙을 적용하여 양도소득세를 계산합니다.
    모든 계산 과정을 추적하여 완전한 감사 추적을 제공합니다.

    Attributes:
        rule_engine: 세법 규칙 엔진
    """

    def __init__(self, rules_file: str = "rules/tax_rules_2024.yaml"):
        """TaxCalculator 초기화

        Args:
            rules_file: 규칙 파일 경로
        """
        self.rule_engine = RuleEngine(rules_file)

    def calculate(
        self,
        fact_ledger: FactLedger,
        is_adjusted_area: bool = False
    ) -> CalculationResult:
        """양도소득세 계산

        Args:
            fact_ledger: 확정된 사실관계 원장
            is_adjusted_area: 조정대상지역 여부

        Returns:
            계산 결과 객체

        Raises:
            ValueError: FactLedger가 확정되지 않았거나 필수 필드가 없는 경우
        """
        # 1. FactLedger 확정 여부 확인
        if not fact_ledger.is_frozen:
            raise ValueError("FactLedger가 확정되지 않았습니다. freeze() 메서드를 먼저 호출하세요.")

        # 2. 계산 추적 리스트 초기화
        traces: List[CalculationTrace] = []
        warnings: List[str] = []

        # 3. 양도소득 계산
        transfer_income = self._calculate_transfer_income(fact_ledger, traces)

        # 4. 장기보유특별공제 계산
        long_term_deduction = self._calculate_long_term_deduction(
            fact_ledger, transfer_income, traces
        )

        # 5. 과세표준 계산
        taxable_income = max(transfer_income - long_term_deduction, Decimal('0'))
        traces.append(CalculationTrace(
            step_name="calculate_taxable_income",
            input_facts={
                'transfer_income': transfer_income,
                'long_term_deduction': long_term_deduction
            },
            applied_rule="basic_calculation",
            output_value=taxable_income,
            formula="transfer_income - long_term_deduction",
            legal_basis="소득세법 제92조"
        ))

        # 6. 세율 결정 및 세액 계산
        tax_rate_info = self.rule_engine.find_applicable_tax_rate(
            holding_period_years=fact_ledger.holding_period_years,
            is_adjusted_area=is_adjusted_area
        )

        tax_rate = tax_rate_info['rate']
        calculated_tax = taxable_income * Decimal(str(tax_rate))

        traces.append(CalculationTrace(
            step_name="apply_tax_rate",
            input_facts={
                'taxable_income': taxable_income,
                'tax_rate': tax_rate,
                'holding_period_years': fact_ledger.holding_period_years,
                'is_adjusted_area': is_adjusted_area
            },
            applied_rule=tax_rate_info['name'],
            output_value=calculated_tax,
            formula=f"taxable_income × {tax_rate}",
            legal_basis=tax_rate_info.get('legal_basis', ''),
            notes=tax_rate_info.get('description', '')
        ))

        # 7. 비과세 및 감면 적용
        exemption_amount = self._calculate_exemption(
            fact_ledger, calculated_tax, traces, warnings
        )

        # 8. 최종 납부세액 계산
        final_tax = max(calculated_tax - exemption_amount, Decimal('0'))

        # 9. 결과 반환
        return CalculationResult(
            fact_ledger_id=fact_ledger.transaction_id,
            transfer_income=transfer_income,
            long_term_deduction=long_term_deduction,
            taxable_income=taxable_income,
            tax_rate=tax_rate,
            calculated_tax=calculated_tax,
            exemption_amount=exemption_amount,
            final_tax=final_tax,
            traces=traces,
            rule_version=self.rule_engine.version,
            warnings=warnings
        )

    def _calculate_transfer_income(
        self,
        fact_ledger: FactLedger,
        traces: List[CalculationTrace]
    ) -> Decimal:
        """양도소득 계산

        양도소득 = 양도가액 - 취득가액 - 필요경비

        Args:
            fact_ledger: 사실관계 원장
            traces: 계산 추적 리스트

        Returns:
            양도소득
        """
        disposal_price = fact_ledger.disposal_price.value
        acquisition_price = fact_ledger.acquisition_price.value

        # 필요경비 합계
        necessary_expenses = Decimal('0')
        if fact_ledger.acquisition_cost:
            necessary_expenses += fact_ledger.acquisition_cost.value
        if fact_ledger.disposal_cost:
            necessary_expenses += fact_ledger.disposal_cost.value
        if fact_ledger.improvement_cost:
            necessary_expenses += fact_ledger.improvement_cost.value

        transfer_income = disposal_price - acquisition_price - necessary_expenses

        traces.append(CalculationTrace(
            step_name="calculate_transfer_income",
            input_facts={
                'disposal_price': disposal_price,
                'acquisition_price': acquisition_price,
                'acquisition_cost': fact_ledger.acquisition_cost.value if fact_ledger.acquisition_cost else 0,
                'disposal_cost': fact_ledger.disposal_cost.value if fact_ledger.disposal_cost else 0,
                'improvement_cost': fact_ledger.improvement_cost.value if fact_ledger.improvement_cost else 0,
            },
            applied_rule="basic_formula",
            output_value=transfer_income,
            formula="disposal_price - acquisition_price - necessary_expenses",
            legal_basis="소득세법 제88조, 제97조",
            intermediate_values={
                'necessary_expenses': necessary_expenses
            }
        ))

        return transfer_income

    def _calculate_long_term_deduction(
        self,
        fact_ledger: FactLedger,
        transfer_income: Decimal,
        traces: List[CalculationTrace]
    ) -> Decimal:
        """장기보유특별공제 계산

        Args:
            fact_ledger: 사실관계 원장
            transfer_income: 양도소득
            traces: 계산 추적 리스트

        Returns:
            장기보유특별공제액
        """
        holding_period = fact_ledger.holding_period_years
        deduction_rate = self.rule_engine.calculate_long_term_deduction_rate(holding_period)

        deduction_amount = transfer_income * Decimal(str(deduction_rate))

        traces.append(CalculationTrace(
            step_name="calculate_long_term_deduction",
            input_facts={
                'transfer_income': transfer_income,
                'holding_period_years': holding_period,
                'deduction_rate': deduction_rate
            },
            applied_rule="long_term_holding_deduction",
            output_value=deduction_amount,
            formula=f"transfer_income × {deduction_rate}",
            legal_basis="소득세법 제95조 제2항",
            notes=f"{holding_period}년 보유 시 {deduction_rate*100}% 공제"
        ))

        return deduction_amount

    def _calculate_exemption(
        self,
        fact_ledger: FactLedger,
        calculated_tax: Decimal,
        traces: List[CalculationTrace],
        warnings: List[str]
    ) -> Decimal:
        """비과세 및 감면 계산

        Args:
            fact_ledger: 사실관계 원장
            calculated_tax: 계산된 세액
            traces: 계산 추적 리스트
            warnings: 경고 메시지 리스트

        Returns:
            비과세 금액
        """
        # 1세대 1주택 비과세 검토
        is_primary = fact_ledger.is_primary_residence.value if fact_ledger.is_primary_residence else False
        residence_years = fact_ledger.residence_period_years.value if fact_ledger.residence_period_years else 0
        holding_years = fact_ledger.holding_period_years

        exemption_info = self.rule_engine.check_exemption_eligibility(
            is_primary_residence=is_primary,
            residence_period_years=residence_years,
            holding_period_years=holding_years
        )

        if exemption_info:
            # 비과세 대상
            exemption_limit = Decimal(str(exemption_info['exemption_limit']))
            disposal_price = fact_ledger.disposal_price.value

            if disposal_price <= exemption_limit:
                # 전액 비과세
                exemption_amount = calculated_tax

                traces.append(CalculationTrace(
                    step_name="apply_exemption",
                    input_facts={
                        'is_primary_residence': is_primary,
                        'residence_period_years': residence_years,
                        'holding_period_years': holding_years,
                        'disposal_price': disposal_price,
                        'exemption_limit': exemption_limit
                    },
                    applied_rule=exemption_info['name'],
                    output_value=exemption_amount,
                    legal_basis=exemption_info.get('legal_basis', ''),
                    notes="1세대 1주택 비과세 요건 충족 - 전액 비과세"
                ))

                return exemption_amount
            else:
                # 부분 비과세
                warnings.append(
                    f"양도가액이 비과세 한도({exemption_limit:,}원)를 초과합니다. "
                    f"초과분에 대해 과세됩니다."
                )

        # 비과세 해당 없음
        traces.append(CalculationTrace(
            step_name="check_exemption",
            input_facts={
                'is_primary_residence': is_primary,
                'residence_period_years': residence_years,
                'holding_period_years': holding_years
            },
            applied_rule="no_exemption",
            output_value=Decimal('0'),
            notes="비과세 요건 미충족"
        ))

        return Decimal('0')

    def estimate_tax(
        self,
        disposal_price: Decimal,
        acquisition_price: Decimal,
        holding_period_years: int,
        is_adjusted_area: bool = False,
        **kwargs
    ) -> Decimal:
        """간편 세액 추정 (FactLedger 없이)

        빠른 세액 추정을 위한 간소화된 메서드입니다.
        정확한 계산은 calculate() 메서드를 사용하세요.

        Args:
            disposal_price: 양도가액
            acquisition_price: 취득가액
            holding_period_years: 보유 기간(년)
            is_adjusted_area: 조정대상지역 여부
            **kwargs: 추가 필요경비 (acquisition_cost, disposal_cost, improvement_cost)

        Returns:
            추정 세액
        """
        # 양도소득 계산
        transfer_income = disposal_price - acquisition_price
        for cost_key in ['acquisition_cost', 'disposal_cost', 'improvement_cost']:
            if cost_key in kwargs:
                transfer_income -= kwargs[cost_key]

        # 장기보유특별공제
        deduction_rate = self.rule_engine.calculate_long_term_deduction_rate(holding_period_years)
        deduction = transfer_income * Decimal(str(deduction_rate))

        # 과세표준
        taxable_income = max(transfer_income - deduction, Decimal('0'))

        # 세율 적용
        tax_rate_info = self.rule_engine.find_applicable_tax_rate(
            holding_period_years=holding_period_years,
            is_adjusted_area=is_adjusted_area
        )

        # 세액 계산
        estimated_tax = taxable_income * Decimal(str(tax_rate_info['rate']))

        return estimated_tax
