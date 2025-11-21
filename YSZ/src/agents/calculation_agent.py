"""세액 산출 에이전트 (Tax Calculation Agent)

수집된 사실관계를 바탕으로 양도소득세를 계산합니다.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from decimal import Decimal

from ..core import TaxCalculator, FactLedger


class TaxCalculationAgent:
    """세액 산출 에이전트

    역할:
    - 기본 세액 계산
    - 시나리오 시뮬레이션
    - 계산 보고서 생성
    """

    def __init__(self, openai_api_key: Optional[str] = None, mock_mode: bool = True):
        """
        Args:
            openai_api_key: OpenAI API 키 (현재 사용 안함)
            mock_mode: True면 mock 모드 (현재 의미 없음, 계산기는 항상 동일)
        """
        self.mock_mode = mock_mode
        self.calculator = TaxCalculator()

    async def calculate(self, facts: Dict[str, Any]) -> Dict[str, Any]:
        """세액 계산

        Args:
            facts: 수집된 사실관계 정보
                - acquisition_date
                - acquisition_price
                - disposal_date
                - disposal_price
                - asset_type
                - is_primary_residence
                - necessary_expenses
                - house_count
                - is_adjusted_area

        Returns:
            {
                "status": "success",
                "disposal_price": 1000000000,
                "acquisition_price": 500000000,
                "capital_gain": 500000000,
                "necessary_expenses": 5000000,
                "long_term_deduction": 80000000,
                "basic_deduction": 2500000,
                "taxable_income": 412500000,
                "calculated_tax": 123750000,
                "local_tax": 12375000,
                "total_tax": 136125000,
                "applied_tax_rate": 0.30,
                "warnings": [],
                "calculation_details": {...}
            }
        """
        print(f"[TaxCalculation] Calculating tax...")

        try:
            # FactLedger 생성
            ledger = self._create_fact_ledger(facts)

            # 계산 수행
            result = self.calculator.calculate(ledger)

            # 결과를 dict로 변환
            tax_result = self._convert_result_to_dict(result, ledger)

            # 추가 정보 포함
            tax_result['status'] = 'success'
            tax_result['calculated_at'] = datetime.now().isoformat()

            print(f"[TaxCalculation] Total tax: {tax_result['total_tax']:,} KRW")

            return tax_result

        except Exception as e:
            print(f"[TaxCalculation] ERROR: {str(e)}")
            import traceback
            traceback.print_exc()

            return {
                "status": "error",
                "message": f"계산 중 오류: {str(e)}",
                "error": str(e)
            }

    def _create_fact_ledger(self, facts: Dict[str, Any]) -> FactLedger:
        """FactLedger 생성 및 확정"""

        # 날짜 변환
        from datetime import datetime as dt

        acquisition_date = facts.get('acquisition_date')
        if isinstance(acquisition_date, str):
            acquisition_date = dt.strptime(acquisition_date, "%Y-%m-%d").date()

        disposal_date = facts.get('disposal_date')
        if isinstance(disposal_date, str):
            disposal_date = dt.strptime(disposal_date, "%Y-%m-%d").date()

        # FactLedger용 dict 생성
        facts_dict = {
            'acquisition_date': acquisition_date,
            'acquisition_price': Decimal(str(facts.get('acquisition_price', 0))),
            'disposal_date': disposal_date,
            'disposal_price': Decimal(str(facts.get('disposal_price', 0))),
            'asset_type': facts.get('asset_type', 'residential'),
            'is_primary_residence': facts.get('is_primary_residence', False),
            'necessary_expenses': Decimal(str(facts.get('necessary_expenses', 0))),
            'house_count': facts.get('house_count', 1),
            'is_adjusted_area': facts.get('is_adjusted_area', False),
        }

        # Ledger 생성
        ledger = FactLedger.create(facts_dict, created_by="agent")

        # Fact 확정 (계산을 위해)
        from ..core.fact import Fact

        for attr_name in vars(ledger):
            attr = getattr(ledger, attr_name)
            if isinstance(attr, Fact) and not attr.is_confirmed:
                # Fact 확정
                object.__setattr__(attr, 'is_confirmed', True)
                object.__setattr__(attr, 'confidence', 1.0)
                object.__setattr__(attr, 'entered_by', 'agent')
                object.__setattr__(attr, 'entered_at', datetime.now())

        # Ledger freeze
        ledger.is_frozen = True

        return ledger

    def _convert_result_to_dict(
        self,
        result: Any,
        ledger: FactLedger
    ) -> Dict[str, Any]:
        """계산 결과를 dict로 변환"""

        disposal_price = float(ledger.disposal_price.value)
        acquisition_price = float(ledger.acquisition_price.value)
        necessary_expenses = float(ledger.necessary_expenses.value) if ledger.necessary_expenses else 0

        return {
            'disposal_price': disposal_price,
            'acquisition_price': acquisition_price,
            'capital_gain': disposal_price - acquisition_price,
            'necessary_expenses': necessary_expenses,
            'long_term_deduction': float(getattr(result, 'long_term_deduction', 0)),
            'basic_deduction': float(getattr(result, 'basic_deduction', 0)),
            'taxable_income': float(getattr(result, 'taxable_income', 0)),
            'calculated_tax': float(getattr(result, 'calculated_tax', 0)),
            'local_tax': float(getattr(result, 'local_tax', 0)),
            'total_tax': float(getattr(result, 'total_tax', 0)),
            'applied_tax_rate': float(getattr(result, 'applied_tax_rate', 0)),
            'warnings': getattr(result, 'warnings', []),
            'calculation_details': {
                'acquisition_date': str(ledger.acquisition_date.value),
                'disposal_date': str(ledger.disposal_date.value),
                'asset_type': ledger.asset_type.value,
                'is_primary_residence': ledger.is_primary_residence.value,
                'house_count': ledger.house_count.value,
                'is_adjusted_area': ledger.is_adjusted_area.value
            }
        }

    async def simulate_scenarios(self, facts: Dict[str, Any]) -> List[Dict[str, Any]]:
        """여러 시나리오 시뮬레이션

        예시:
        - 1년 더 보유하면?
        - 필요경비를 더 인정받으면?
        - 양도가액이 다르면?

        Args:
            facts: 기본 사실관계

        Returns:
            [
                {
                    "scenario_name": "1년 더 보유",
                    "changes": {"disposal_date": "2025-12-20"},
                    "tax_result": {...},
                    "comparison": {
                        "tax_difference": -15000000,
                        "tax_rate_change": -0.1
                    }
                },
                ...
            ]
        """
        print(f"[TaxCalculation] Simulating scenarios...")

        # 기본 시나리오 계산
        base_result = await self.calculate(facts)

        scenarios = []

        # TODO: 시나리오 생성 및 계산
        # - 보유 기간 연장
        # - 필요경비 변경
        # - 양도가액 변경
        # - 1세대1주택 요건 충족

        return scenarios

    def generate_report(self, tax_result: Dict[str, Any]) -> str:
        """계산 보고서 생성

        Returns:
            Markdown 형식의 보고서
        """
        lines = [
            "## 양도소득세 계산 결과",
            "",
            "### 기본 정보",
            f"- 양도가액: {tax_result['disposal_price']:,} 원",
            f"- 취득가액: {tax_result['acquisition_price']:,} 원",
            f"- 양도차익: {tax_result['capital_gain']:,} 원",
            "",
            "### 세액 계산",
            f"- 필요경비: {tax_result['necessary_expenses']:,} 원",
            f"- 장기보유특별공제: {tax_result['long_term_deduction']:,} 원",
            f"- 기본공제: {tax_result['basic_deduction']:,} 원",
            f"- 과세표준: {tax_result['taxable_income']:,} 원",
            "",
            "### 납부세액",
            f"- 산출세액: {tax_result['calculated_tax']:,} 원",
            f"- 지방소득세: {tax_result['local_tax']:,} 원",
            f"- **총 납부세액: {tax_result['total_tax']:,} 원**",
            "",
            f"적용 세율: {tax_result['applied_tax_rate'] * 100:.1f}%",
            ""
        ]

        # 경고 사항
        if tax_result.get('warnings'):
            lines.extend([
                "### 주의사항",
                ""
            ])
            for warning in tax_result['warnings']:
                lines.append(f"- {warning}")
            lines.append("")

        return "\n".join(lines)
