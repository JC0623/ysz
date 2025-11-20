"""계산 과정 감사 추적"""

from datetime import datetime
from typing import Dict, Any, List
from decimal import Decimal

from .audit_service import AuditService, AuditEntry, AuditEventType, audit_service
from ..core import Fact


class CalculationAuditor:
    """세금 계산 과정 완전 추적

    계산의 각 단계를 상세히 기록하여
    나중에 계산 과정을 완전히 재현할 수 있도록 합니다.
    """

    def __init__(
        self,
        transaction_id: int,
        audit_service: AuditService = audit_service
    ):
        """
        Args:
            transaction_id: 거래 ID
            audit_service: 감사 서비스
        """
        self.transaction_id = transaction_id
        self.audit_service = audit_service
        self.calculation_steps = []

    async def log_calculation_start(
        self,
        input_facts: Dict[str, Any]
    ):
        """계산 시작 로깅

        Args:
            input_facts: 입력 사실관계
        """
        entry = AuditEntry(
            event_type=AuditEventType.CALCULATION_STARTED,
            timestamp=datetime.now(),
            transaction_id=self.transaction_id,
            request_data={
                "input_facts": self._serialize_facts(input_facts)
            }
        )

        await self.audit_service.log_entry(entry)

    async def log_calculation_step(
        self,
        step_name: str,
        step_description: str,
        input_values: Dict[str, Any],
        output_value: Any,
        rule_applied: str,
        legal_basis: str
    ):
        """계산 단계 로깅

        Args:
            step_name: 단계 이름
            step_description: 단계 설명
            input_values: 입력 값들
            output_value: 출력 값
            rule_applied: 적용된 규칙
            legal_basis: 법적 근거
        """
        step_data = {
            "step_name": step_name,
            "step_description": step_description,
            "input_values": self._serialize_values(input_values),
            "output_value": self._serialize_value(output_value),
            "rule_applied": rule_applied,
            "legal_basis": legal_basis,
            "timestamp": datetime.now().isoformat()
        }

        self.calculation_steps.append(step_data)

        entry = AuditEntry(
            event_type=AuditEventType.CALCULATION_STEP,
            timestamp=datetime.now(),
            transaction_id=self.transaction_id,
            metadata=step_data
        )

        await self.audit_service.log_entry(entry)

    async def log_rule_application(
        self,
        rule_id: str,
        rule_description: str,
        condition_met: bool,
        input_facts: Dict[str, Any],
        result: Any
    ):
        """규칙 적용 로깅

        Args:
            rule_id: 규칙 ID
            rule_description: 규칙 설명
            condition_met: 조건 충족 여부
            input_facts: 입력 사실
            result: 적용 결과
        """
        entry = AuditEntry(
            event_type=AuditEventType.RULE_APPLIED,
            timestamp=datetime.now(),
            transaction_id=self.transaction_id,
            metadata={
                "rule_id": rule_id,
                "rule_description": rule_description,
                "condition_met": condition_met,
                "input_facts": self._serialize_facts(input_facts),
                "result": self._serialize_value(result)
            }
        )

        await self.audit_service.log_entry(entry)

    async def log_calculation_complete(
        self,
        final_result: Dict[str, Any]
    ):
        """계산 완료 로깅

        Args:
            final_result: 최종 계산 결과
        """
        entry = AuditEntry(
            event_type=AuditEventType.CALCULATION_COMPLETED,
            timestamp=datetime.now(),
            transaction_id=self.transaction_id,
            response_data={
                "final_result": self._serialize_values(final_result),
                "total_steps": len(self.calculation_steps),
                "calculation_steps": self.calculation_steps
            }
        )

        await self.audit_service.log_entry(entry)

    async def get_calculation_trace(self) -> List[Dict[str, Any]]:
        """계산 추적 정보 조회

        Returns:
            계산 단계별 추적 정보
        """
        return self.calculation_steps

    async def generate_calculation_report(self) -> Dict[str, Any]:
        """계산 보고서 생성

        Returns:
            전체 계산 과정 보고서
        """
        audit_trail = await self.audit_service.get_calculation_audit_trail(
            self.transaction_id
        )

        return {
            "transaction_id": self.transaction_id,
            "total_steps": len(self.calculation_steps),
            "calculation_steps": self.calculation_steps,
            "audit_events": [entry.to_dict() for entry in audit_trail],
            "generated_at": datetime.now().isoformat()
        }

    def _serialize_facts(self, facts: Dict[str, Any]) -> Dict[str, Any]:
        """Fact 딕셔너리를 직렬화

        Args:
            facts: Fact 딕셔너리

        Returns:
            직렬화된 딕셔너리
        """
        serialized = {}
        for key, value in facts.items():
            if isinstance(value, Fact):
                serialized[key] = {
                    "value": self._serialize_value(value.value),
                    "source": value.source,
                    "confidence": float(value.confidence),
                    "is_confirmed": value.is_confirmed
                }
            else:
                serialized[key] = self._serialize_value(value)
        return serialized

    def _serialize_values(self, values: Dict[str, Any]) -> Dict[str, Any]:
        """값 딕셔너리를 직렬화

        Args:
            values: 값 딕셔너리

        Returns:
            직렬화된 딕셔너리
        """
        return {
            key: self._serialize_value(value)
            for key, value in values.items()
        }

    def _serialize_value(self, value: Any) -> Any:
        """단일 값을 직렬화

        Args:
            value: 직렬화할 값

        Returns:
            직렬화된 값
        """
        if isinstance(value, Decimal):
            return float(value)
        elif hasattr(value, 'isoformat'):  # date, datetime
            return value.isoformat()
        elif isinstance(value, (list, tuple)):
            return [self._serialize_value(v) for v in value]
        elif isinstance(value, dict):
            return self._serialize_values(value)
        else:
            return value
