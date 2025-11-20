"""감사 로그 서비스"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum
import json


class AuditEventType(Enum):
    """감사 이벤트 유형"""
    API_REQUEST = "API_REQUEST"
    API_RESPONSE = "API_RESPONSE"
    FACT_COLLECTED = "FACT_COLLECTED"
    FACT_CONFIRMED = "FACT_CONFIRMED"
    CALCULATION_STARTED = "CALCULATION_STARTED"
    CALCULATION_COMPLETED = "CALCULATION_COMPLETED"
    CALCULATION_STEP = "CALCULATION_STEP"
    RULE_APPLIED = "RULE_APPLIED"
    ERROR_OCCURRED = "ERROR_OCCURRED"
    DATABASE_OPERATION = "DATABASE_OPERATION"


@dataclass
class AuditEntry:
    """감사 로그 엔트리"""
    event_type: AuditEventType
    timestamp: datetime
    transaction_id: Optional[int] = None
    user_id: Optional[str] = None
    request_data: Optional[Dict[str, Any]] = None
    response_data: Optional[Dict[str, Any]] = None
    error_data: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        data = asdict(self)
        data['event_type'] = self.event_type.value
        data['timestamp'] = self.timestamp.isoformat()
        return data

    def to_json(self) -> str:
        """JSON 문자열로 변환"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class AuditService:
    """감사 로그 서비스

    모든 중요한 이벤트를 기록하고 추적합니다.
    """

    def __init__(self, log_file: Optional[str] = None):
        """
        Args:
            log_file: 로그 파일 경로 (None이면 콘솔만 출력)
        """
        self.log_file = log_file
        self.entries = []

    async def log_entry(self, entry: AuditEntry):
        """감사 엔트리 기록

        Args:
            entry: 기록할 감사 엔트리
        """
        self.entries.append(entry)

        # 콘솔 출력
        self._print_entry(entry)

        # 파일 기록
        if self.log_file:
            await self._write_to_file(entry)

    def _print_entry(self, entry: AuditEntry):
        """콘솔에 엔트리 출력"""
        print(f"[AUDIT] {entry.timestamp.isoformat()} - {entry.event_type.value}")
        if entry.transaction_id:
            print(f"  Transaction ID: {entry.transaction_id}")
        if entry.user_id:
            print(f"  User ID: {entry.user_id}")

    async def _write_to_file(self, entry: AuditEntry):
        """파일에 엔트리 기록"""
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(entry.to_json())
                f.write('\n')
        except Exception as e:
            print(f"Failed to write audit log: {e}")

    async def get_transaction_audit_trail(
        self,
        transaction_id: int
    ) -> list[AuditEntry]:
        """특정 거래의 감사 추적 조회

        Args:
            transaction_id: 거래 ID

        Returns:
            해당 거래의 모든 감사 엔트리
        """
        return [
            entry for entry in self.entries
            if entry.transaction_id == transaction_id
        ]

    async def get_calculation_audit_trail(
        self,
        transaction_id: int
    ) -> list[AuditEntry]:
        """계산 과정 감사 추적 조회

        Args:
            transaction_id: 거래 ID

        Returns:
            계산 관련 감사 엔트리만
        """
        calculation_events = {
            AuditEventType.CALCULATION_STARTED,
            AuditEventType.CALCULATION_COMPLETED,
            AuditEventType.CALCULATION_STEP,
            AuditEventType.RULE_APPLIED
        }

        return [
            entry for entry in self.entries
            if entry.transaction_id == transaction_id
            and entry.event_type in calculation_events
        ]

    async def generate_audit_report(
        self,
        transaction_id: int
    ) -> Dict[str, Any]:
        """감사 보고서 생성

        Args:
            transaction_id: 거래 ID

        Returns:
            전체 감사 보고서
        """
        trail = await self.get_transaction_audit_trail(transaction_id)

        if not trail:
            return {
                "transaction_id": transaction_id,
                "message": "No audit trail found"
            }

        return {
            "transaction_id": transaction_id,
            "total_events": len(trail),
            "start_time": trail[0].timestamp.isoformat(),
            "end_time": trail[-1].timestamp.isoformat(),
            "events": [entry.to_dict() for entry in trail],
            "summary": self._generate_summary(trail)
        }

    def _generate_summary(self, trail: list[AuditEntry]) -> Dict[str, Any]:
        """감사 추적 요약 생성"""
        event_counts = {}
        for entry in trail:
            event_type = entry.event_type.value
            event_counts[event_type] = event_counts.get(event_type, 0) + 1

        return {
            "event_counts": event_counts,
            "has_errors": any(
                entry.event_type == AuditEventType.ERROR_OCCURRED
                for entry in trail
            )
        }


# 전역 감사 서비스 인스턴스
audit_service = AuditService(log_file="logs/audit.log")
