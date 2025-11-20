"""TaxCalculator: 양도소득세 계산기 (누진세율 구조)"""

from decimal import Decimal
from datetime import datetime
from typing import List, Optional

from .fact_ledger import FactLedger
from .calculation_trace import CalculationTrace, CalculationResult
from .rule_engine import RuleEngine


class TaxCalculator:
    """양도소득세 계산기

    FactLedger를 입력받아 세법 규칙을 적용하여 양도소득세를 계산합니다.
    2024년 기준 누진세율 구조를 지원합니다.

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

        # 4. 비과세 검토 (1세대 1주택)
        exemption_result = self._check_exemption(fact_ledger, traces, warnings)
        if exemption_result['is_exempt']:
            # 전액 비과세
            return self._create_exempt_result(
                fact_ledger, transfer_income, traces, warnings
            )

        # 5. 장기보유특별공제 계산
        long_term_deduction = self._calculate_long_term_deduction(
            fact_ledger, transfer_income, traces
        )

        # 6. 양도소득금액 계산
        transfer_income_amount = max(transfer_income - long_term_deduction, Decimal('0'))
        traces.append(CalculationTrace(
            step_name="calculate_transfer_income_amount",
            input_facts={
                'transfer_income': transfer_income,
                'long_term_deduction': long_term_deduction
            },
            applied_rule="basic_calculation",
            output_value=transfer_income_amount,
            formula="transfer_income - long_term_deduction",
            legal_basis="소득세법 제92조"
        ))

        # 7. 기본공제 적용
        basic_deduction = self.rule_engine.get_basic_deduction()
        taxable_income = max(transfer_income_amount - basic_deduction, Decimal('0'))

        traces.append(CalculationTrace(
            step_name="apply_basic_deduction",
            input_facts={
                'transfer_income_amount': transfer_income_amount,
                'basic_deduction': basic_deduction
            },
            applied_rule="basic_deduction",
            output_value=taxable_income,
            formula="transfer_income_amount - basic_deduction (250만원)",
            legal_basis="소득세법 제100조"
        ))

        # 8. 세율 결정 및 세액 계산
        tax_result = self._calculate_tax(
            fact_ledger, taxable_income, is_adjusted_area, traces, warnings
        )

        # 9. 지방소득세 계산
        local_tax_rate = self.rule_engine.get_local_tax_rate()
        local_tax = tax_result['calculated_tax'] * Decimal(str(local_tax_rate))

        traces.append(CalculationTrace(
            step_name="calculate_local_tax",
            input_facts={
                'calculated_tax': tax_result['calculated_tax'],
                'local_tax_rate': local_tax_rate
            },
            applied_rule="local_income_tax",
            output_value=local_tax,
            formula=f"calculated_tax × {local_tax_rate}",
            legal_basis="지방세법 제92조",
            notes="산출세액의 10%"
        ))

        # 10. 최종 납부세액
        final_tax = tax_result['calculated_tax'] + local_tax

        # 11. 결과 반환
        return CalculationResult(
            fact_ledger_id=fact_ledger.transaction_id,
            transfer_income=transfer_income,
            long_term_deduction=long_term_deduction,
            transfer_income_amount=transfer_income_amount,
            basic_deduction=basic_deduction,
            taxable_income=taxable_income,
            base_tax_rate=tax_result['base_tax_rate'],
            progressive_deduction=tax_result['progressive_deduction'],
            surcharge_rate=tax_result['surcharge_rate'],
            calculated_tax=tax_result['calculated_tax'],
            local_tax=local_tax,
            exemption_amount=Decimal('0'),
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

    def _check_exemption(
        self,
        fact_ledger: FactLedger,
        traces: List[CalculationTrace],
        warnings: List[str]
    ) -> dict:
        """비과세 검토 (1세대 1주택)

        Args:
            fact_ledger: 사실관계 원장
            traces: 계산 추적 리스트
            warnings: 경고 메시지 리스트

        Returns:
            {'is_exempt': bool, 'exemption_info': dict or None}
        """
        is_primary = fact_ledger.is_primary_residence.value if fact_ledger.is_primary_residence else False
        residence_years = fact_ledger.residence_period_years.value if fact_ledger.residence_period_years else 0
        holding_years = fact_ledger.holding_period_years

        exemption_info = self.rule_engine.check_exemption_eligibility(
            is_primary_residence=is_primary,
            residence_period_years=residence_years,
            holding_period_years=holding_years
        )

        if exemption_info:
            exemption_limit = Decimal(str(exemption_info['exemption_limit']))
            disposal_price = fact_ledger.disposal_price.value

            if disposal_price <= exemption_limit:
                # 전액 비과세
                traces.append(CalculationTrace(
                    step_name="check_exemption",
                    input_facts={
                        'is_primary_residence': is_primary,
                        'residence_period_years': residence_years,
                        'holding_period_years': holding_years,
                        'disposal_price': disposal_price,
                        'exemption_limit': exemption_limit
                    },
                    applied_rule=exemption_info['name'],
                    output_value=True,
                    legal_basis=exemption_info.get('legal_basis', ''),
                    notes="1세대 1주택 비과세 요건 충족 - 전액 비과세"
                ))

                return {'is_exempt': True, 'exemption_info': exemption_info}
            else:
                # 부분 과세 (12억 초과분)
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
            output_value=False,
            notes="비과세 요건 미충족"
        ))

        return {'is_exempt': False, 'exemption_info': None}

    def _create_exempt_result(
        self,
        fact_ledger: FactLedger,
        transfer_income: Decimal,
        traces: List[CalculationTrace],
        warnings: List[str]
    ) -> CalculationResult:
        """비과세 결과 생성

        Args:
            fact_ledger: 사실관계 원장
            transfer_income: 양도소득
            traces: 계산 추적 리스트
            warnings: 경고 메시지 리스트

        Returns:
            비과세 계산 결과
        """
        return CalculationResult(
            fact_ledger_id=fact_ledger.transaction_id,
            transfer_income=transfer_income,
            long_term_deduction=Decimal('0'),
            transfer_income_amount=transfer_income,
            basic_deduction=Decimal('0'),
            taxable_income=Decimal('0'),
            base_tax_rate=0.0,
            progressive_deduction=Decimal('0'),
            surcharge_rate=0.0,
            calculated_tax=Decimal('0'),
            local_tax=Decimal('0'),
            exemption_amount=transfer_income,  # 전액 비과세
            final_tax=Decimal('0'),
            traces=traces,
            rule_version=self.rule_engine.version,
            warnings=warnings
        )

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
        is_primary = fact_ledger.is_primary_residence.value if fact_ledger.is_primary_residence else False
        residence_years = fact_ledger.residence_period_years.value if fact_ledger.residence_period_years else 0

        deduction_rate = self.rule_engine.calculate_long_term_deduction_rate(
            holding_period_years=holding_period,
            is_primary_residence=is_primary,
            residence_period_years=residence_years
        )

        deduction_amount = transfer_income * Decimal(str(deduction_rate))

        notes = f"{holding_period}년 보유 시 {deduction_rate*100:.0f}% 공제"
        if is_primary and residence_years >= 2:
            notes += f" (1세대1주택: 보유+거주 공제, 거주 {residence_years}년)"

        traces.append(CalculationTrace(
            step_name="calculate_long_term_deduction",
            input_facts={
                'transfer_income': transfer_income,
                'holding_period_years': holding_period,
                'is_primary_residence': is_primary,
                'residence_period_years': residence_years,
                'deduction_rate': deduction_rate
            },
            applied_rule="long_term_holding_deduction",
            output_value=deduction_amount,
            formula=f"transfer_income × {deduction_rate}",
            legal_basis="소득세법 제95조 제2항",
            notes=notes
        ))

        return deduction_amount

    def _calculate_tax(
        self,
        fact_ledger: FactLedger,
        taxable_income: Decimal,
        is_adjusted_area: bool,
        traces: List[CalculationTrace],
        warnings: List[str]
    ) -> dict:
        """세액 계산 (누진세율 또는 비례세율)

        Args:
            fact_ledger: 사실관계 원장
            taxable_income: 과세표준
            is_adjusted_area: 조정대상지역 여부
            traces: 계산 추적 리스트
            warnings: 경고 메시지 리스트

        Returns:
            {
                'base_tax_rate': 기본 세율,
                'progressive_deduction': 누진공제액,
                'surcharge_rate': 중과세율,
                'calculated_tax': 계산된 세액
            }
        """
        holding_period = fact_ledger.holding_period_years
        asset_type = fact_ledger.asset_type.value if fact_ledger.asset_type else 'residential'
        house_count = fact_ledger.house_count.value if fact_ledger.house_count else 1

        # 2년 미만: 단기보유 차등 비례세율
        if holding_period < 2:
            return self._calculate_short_term_tax(
                taxable_income, asset_type, holding_period, traces
            )

        # 2년 이상: 누진세율
        base_tax_rate, progressive_deduction, description = self.rule_engine.calculate_progressive_tax(
            taxable_income
        )

        # 다주택자 중과세율 확인
        surcharge_rate = self.rule_engine.get_multi_house_surcharge(
            house_count=house_count,
            is_adjusted_area=is_adjusted_area,
            holding_period_years=holding_period
        )

        # 총 세율
        total_rate = base_tax_rate + surcharge_rate

        # 세액 계산: (과세표준 × 총세율) - 누진공제액
        calculated_tax = (taxable_income * Decimal(str(total_rate))) - progressive_deduction
        calculated_tax = max(calculated_tax, Decimal('0'))

        # 추적 정보 추가
        input_facts = {
            'taxable_income': taxable_income,
            'holding_period_years': holding_period,
            'base_tax_rate': base_tax_rate,
            'progressive_deduction': progressive_deduction,
        }

        formula = f"(taxable_income × {total_rate}) - {progressive_deduction:,}"
        notes = f"{description}"

        if surcharge_rate > 0:
            input_facts['house_count'] = house_count
            input_facts['is_adjusted_area'] = is_adjusted_area
            input_facts['surcharge_rate'] = surcharge_rate
            notes += f" + 중과{surcharge_rate*100:.0f}%p (조정지역 {house_count}주택)"
            warnings.append(
                f"다주택자 중과세율 적용: {surcharge_rate*100:.0f}%p 추가 "
                f"(조정대상지역 {house_count}주택)"
            )

        traces.append(CalculationTrace(
            step_name="calculate_progressive_tax",
            input_facts=input_facts,
            applied_rule="progressive_tax_brackets",
            output_value=calculated_tax,
            formula=formula,
            legal_basis="소득세법 제104조",
            notes=notes
        ))

        return {
            'base_tax_rate': base_tax_rate,
            'progressive_deduction': progressive_deduction,
            'surcharge_rate': surcharge_rate,
            'calculated_tax': calculated_tax
        }

    def _calculate_short_term_tax(
        self,
        taxable_income: Decimal,
        asset_type: str,
        holding_period_years: int,
        traces: List[CalculationTrace]
    ) -> dict:
        """단기보유 차등 비례세율 적용

        Args:
            taxable_income: 과세표준
            asset_type: 자산 유형
            holding_period_years: 보유 기간
            traces: 계산 추적 리스트

        Returns:
            세액 계산 결과 딕셔너리
        """
        rate_info = self.rule_engine.get_short_term_rate(
            asset_type=asset_type,
            holding_period_years=holding_period_years
        )

        if not rate_info:
            raise ValueError(
                f"단기보유 세율을 찾을 수 없습니다. "
                f"asset_type={asset_type}, holding_period={holding_period_years}"
            )

        tax_rate = rate_info['rate']
        calculated_tax = taxable_income * Decimal(str(tax_rate))

        traces.append(CalculationTrace(
            step_name="calculate_short_term_tax",
            input_facts={
                'taxable_income': taxable_income,
                'asset_type': asset_type,
                'holding_period_years': holding_period_years,
                'tax_rate': tax_rate
            },
            applied_rule=rate_info['name'],
            output_value=calculated_tax,
            formula=f"taxable_income × {tax_rate}",
            legal_basis=rate_info.get('legal_basis', ''),
            notes=f"{rate_info.get('description', '')} - 비례세율"
        ))

        return {
            'base_tax_rate': tax_rate,
            'progressive_deduction': Decimal('0'),
            'surcharge_rate': 0.0,
            'calculated_tax': calculated_tax
        }

    def estimate_tax(
        self,
        disposal_price: Decimal,
        acquisition_price: Decimal,
        holding_period_years: int,
        is_adjusted_area: bool = False,
        asset_type: str = 'residential',
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
            asset_type: 자산 유형 ('residential' or 'non_residential')
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
        is_primary = kwargs.get('is_primary_residence', False)
        residence_years = kwargs.get('residence_period_years', 0)
        deduction_rate = self.rule_engine.calculate_long_term_deduction_rate(
            holding_period_years=holding_period_years,
            is_primary_residence=is_primary,
            residence_period_years=residence_years
        )
        deduction = transfer_income * Decimal(str(deduction_rate))

        # 양도소득금액
        transfer_income_amount = max(transfer_income - deduction, Decimal('0'))

        # 기본공제
        basic_deduction = self.rule_engine.get_basic_deduction()
        taxable_income = max(transfer_income_amount - basic_deduction, Decimal('0'))

        # 세율 적용
        if holding_period_years < 2:
            # 단기보유 비례세율
            rate_info = self.rule_engine.get_short_term_rate(
                asset_type=asset_type,
                holding_period_years=holding_period_years
            )
            tax_rate = rate_info['rate']
            estimated_tax = taxable_income * Decimal(str(tax_rate))
        else:
            # 누진세율
            base_rate, progressive_deduction, _ = self.rule_engine.calculate_progressive_tax(
                taxable_income
            )

            # 다주택 중과
            house_count = kwargs.get('house_count', 1)
            surcharge_rate = self.rule_engine.get_multi_house_surcharge(
                house_count=house_count,
                is_adjusted_area=is_adjusted_area,
                holding_period_years=holding_period_years
            )

            total_rate = base_rate + surcharge_rate
            estimated_tax = (taxable_income * Decimal(str(total_rate))) - progressive_deduction
            estimated_tax = max(estimated_tax, Decimal('0'))

        # 지방소득세 추가
        local_tax_rate = self.rule_engine.get_local_tax_rate()
        local_tax = estimated_tax * Decimal(str(local_tax_rate))

        return estimated_tax + local_tax
