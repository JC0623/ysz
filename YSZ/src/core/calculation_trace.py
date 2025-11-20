"""CalculationTrace: 계산 과정 추적"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional, List


@dataclass
class CalculationTrace:
    """계산 과정의 각 단계를 추적하는 클래스

    모든 계산 단계를 기록하여 완전한 감사 추적(audit trail)을 제공합니다.

    Attributes:
        step_name: 계산 단계 이름
        input_facts: 입력으로 사용된 사실관계
        applied_rule: 적용된 규칙 이름
        output_value: 계산 결과값
        calculation_time: 계산 수행 시각
        legal_basis: 근거 법조문
        formula: 사용된 계산 공식
        intermediate_values: 중간 계산값들
        notes: 추가 메모
    """

    step_name: str
    input_facts: Dict[str, Any]
    applied_rule: str
    output_value: Any
    calculation_time: datetime = field(default_factory=datetime.now)
    legal_basis: Optional[str] = None
    formula: Optional[str] = None
    intermediate_values: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None

    def to_dict(self) -> dict:
        """딕셔너리로 변환

        Returns:
            계산 추적 정보를 담은 딕셔너리
        """
        return {
            'step_name': self.step_name,
            'input_facts': self._serialize_input_facts(),
            'applied_rule': self.applied_rule,
            'output_value': self._serialize_value(self.output_value),
            'calculation_time': self.calculation_time.isoformat(),
            'legal_basis': self.legal_basis,
            'formula': self.formula,
            'intermediate_values': self._serialize_intermediate_values(),
            'notes': self.notes,
        }

    def _serialize_value(self, value: Any) -> Any:
        """값을 직렬화 가능한 형태로 변환"""
        if isinstance(value, Decimal):
            return str(value)
        elif isinstance(value, (list, dict)):
            return value
        else:
            return value

    def _serialize_input_facts(self) -> Dict[str, Any]:
        """입력 사실관계를 직렬화"""
        result = {}
        for key, value in self.input_facts.items():
            result[key] = self._serialize_value(value)
        return result

    def _serialize_intermediate_values(self) -> Optional[Dict[str, Any]]:
        """중간 계산값들을 직렬화"""
        if not self.intermediate_values:
            return None

        result = {}
        for key, value in self.intermediate_values.items():
            result[key] = self._serialize_value(value)
        return result

    def __str__(self) -> str:
        """사람이 읽기 쉬운 형태로 출력"""
        output_str = f"{self.output_value:,}" if isinstance(self.output_value, (int, Decimal)) else str(self.output_value)
        return (
            f"[{self.step_name}] "
            f"규칙: {self.applied_rule}, "
            f"결과: {output_str}"
        )


@dataclass
class CalculationResult:
    """최종 계산 결과를 담는 클래스

    계산된 세액과 함께 전체 계산 과정을 추적 정보로 저장합니다.

    Attributes:
        fact_ledger_id: 사용된 FactLedger의 ID
        transfer_income: 양도소득 (양도가액 - 취득가액 - 필요경비)
        long_term_deduction: 장기보유특별공제액
        taxable_income: 과세표준 (양도소득 - 공제)
        tax_rate: 적용 세율
        calculated_tax: 계산된 세액 (과세표준 × 세율)
        exemption_amount: 비과세 금액
        final_tax: 최종 납부 세액
        traces: 계산 과정 추적 리스트
        calculation_time: 계산 수행 시각
        rule_version: 사용된 규칙 버전
        warnings: 경고 메시지 리스트
    """

    fact_ledger_id: str
    transfer_income: Decimal
    long_term_deduction: Decimal
    taxable_income: Decimal
    tax_rate: float
    calculated_tax: Decimal
    exemption_amount: Decimal
    final_tax: Decimal
    traces: List[CalculationTrace]
    calculation_time: datetime = field(default_factory=datetime.now)
    rule_version: str = "2024.11"
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """딕셔너리로 변환

        Returns:
            계산 결과를 담은 딕셔너리
        """
        return {
            'fact_ledger_id': self.fact_ledger_id,
            'transfer_income': str(self.transfer_income),
            'long_term_deduction': str(self.long_term_deduction),
            'taxable_income': str(self.taxable_income),
            'tax_rate': self.tax_rate,
            'calculated_tax': str(self.calculated_tax),
            'exemption_amount': str(self.exemption_amount),
            'final_tax': str(self.final_tax),
            'traces': [trace.to_dict() for trace in self.traces],
            'calculation_time': self.calculation_time.isoformat(),
            'rule_version': self.rule_version,
            'warnings': self.warnings,
        }

    def get_summary(self) -> str:
        """계산 결과 요약

        Returns:
            사람이 읽기 쉬운 형태의 요약
        """
        return f"""
=== 양도소득세 계산 결과 ===

양도소득:        {self.transfer_income:>15,}원
장기보유공제:    {self.long_term_deduction:>15,}원
과세표준:        {self.taxable_income:>15,}원
적용세율:        {self.tax_rate*100:>14.1f}%
계산세액:        {self.calculated_tax:>15,}원
비과세액:        {self.exemption_amount:>15,}원
─────────────────────────────────
최종납부세액:    {self.final_tax:>15,}원

규칙 버전: {self.rule_version}
계산 시각: {self.calculation_time.strftime('%Y-%m-%d %H:%M:%S')}
""".strip()

    def get_trace_summary(self) -> str:
        """계산 과정 요약

        Returns:
            각 단계별 계산 과정
        """
        lines = ["=== 계산 과정 추적 ===\n"]
        for i, trace in enumerate(self.traces, 1):
            lines.append(f"{i}. {trace}")
            if trace.legal_basis:
                lines.append(f"   근거: {trace.legal_basis}")
            if trace.formula:
                lines.append(f"   공식: {trace.formula}")
            lines.append("")

        return "\n".join(lines)

    def __str__(self) -> str:
        """사람이 읽기 쉬운 형태로 출력"""
        return self.get_summary()
