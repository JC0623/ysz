"""Fact: 추적 가능한 사실 정보를 담는 불변 객체"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional, TypeVar, Generic


T = TypeVar('T')


@dataclass(frozen=True)
class Fact(Generic[T]):
    """추적 가능한 사실 정보를 담는 불변 객체

    모든 입력값은 Fact 객체로 래핑되어 출처, 신뢰도, 확정 여부 등의
    메타데이터와 함께 저장됩니다.

    Attributes:
        value: 실제 값 (날짜, 금액 등)
        source: 출처 ('user_input', 'system', 'api', 'document', 'agent_generated' 등)
        confidence: 신뢰도 (0.0~1.0, 1.0=확정값)
        is_confirmed: 확정 여부 (True=확정, False=추정)
        entered_by: 입력자 (사용자 ID, Agent ID 또는 이름)
        entered_at: 입력 시각
        notes: 추가 메모
        reference: 근거 자료 (문서번호, URL 등)
        rule_version: 사용된 세법 규칙 버전 (예: "2024.1.0")
        reasoning_trace: AI 판단 근거 (LLM 출력, Agent가 생성한 경우)

    Example:
        >>> fact = Fact(
        ...     value=Decimal("500000000"),
        ...     source="user_input",
        ...     confidence=1.0,
        ...     is_confirmed=True,
        ...     entered_by="김세무사",
        ...     notes="등기부등본 기준"
        ... )
    """

    value: T
    source: str = "user_input"
    confidence: float = 1.0
    is_confirmed: bool = False
    entered_by: str = "system"
    entered_at: datetime = None
    notes: Optional[str] = None
    reference: Optional[str] = None
    rule_version: Optional[str] = None  # 사용된 세법 규칙 버전
    reasoning_trace: Optional[str] = None  # AI 판단 근거

    def __post_init__(self):
        """초기화 후 검증"""
        # entered_at이 None이면 현재 시각으로 설정
        if self.entered_at is None:
            object.__setattr__(self, 'entered_at', datetime.now())

        # confidence 범위 검증
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence는 0.0에서 1.0 사이여야 합니다")

        # is_confirmed가 True면 confidence는 1.0이어야 함
        if self.is_confirmed and self.confidence != 1.0:
            raise ValueError("확정된 값(is_confirmed=True)은 confidence가 1.0이어야 합니다")

    def confirm(self, confirmed_by: str, notes: Optional[str] = None) -> "Fact[T]":
        """값을 확정하고 새로운 Fact 객체 반환

        Args:
            confirmed_by: 확정한 사람
            notes: 확정 사유

        Returns:
            확정된 새로운 Fact 객체

        Example:
            >>> estimated_fact = Fact(value=5000000, confidence=0.8)
            >>> confirmed_fact = estimated_fact.confirm(
            ...     confirmed_by="김세무사",
            ...     notes="계약서 확인 완료"
            ... )
        """
        return Fact(
            value=self.value,
            source=self.source,
            confidence=1.0,
            is_confirmed=True,
            entered_by=confirmed_by,
            entered_at=datetime.now(),
            notes=notes or self.notes,
            reference=self.reference,
            rule_version=self.rule_version,
            reasoning_trace=self.reasoning_trace
        )

    def update_value(
        self,
        new_value: T,
        updated_by: str,
        notes: Optional[str] = None
    ) -> "Fact[T]":
        """값을 업데이트하고 새로운 Fact 객체 반환

        불변 객체이므로 수정 대신 새 객체를 생성합니다.
        확정 여부는 초기화됩니다.

        Args:
            new_value: 새로운 값
            updated_by: 수정한 사람
            notes: 수정 사유

        Returns:
            업데이트된 새로운 Fact 객체
        """
        return Fact(
            value=new_value,
            source=self.source,
            confidence=self.confidence,
            is_confirmed=False,  # 값 변경 시 확정 해제
            entered_by=updated_by,
            entered_at=datetime.now(),
            notes=notes or self.notes,
            reference=self.reference,
            rule_version=self.rule_version,
            reasoning_trace=self.reasoning_trace
        )

    @classmethod
    def create_user_input(
        cls,
        value: T,
        entered_by: str,
        is_confirmed: bool = False,
        notes: Optional[str] = None,
        reference: Optional[str] = None
    ) -> "Fact[T]":
        """사용자 입력 Fact 생성 헬퍼 메서드

        Args:
            value: 입력값
            entered_by: 입력자
            is_confirmed: 확정 여부
            notes: 메모
            reference: 근거 자료

        Returns:
            사용자 입력 Fact 객체
        """
        return cls(
            value=value,
            source="user_input",
            confidence=1.0 if is_confirmed else 0.9,
            is_confirmed=is_confirmed,
            entered_by=entered_by,
            notes=notes,
            reference=reference
        )

    @classmethod
    def create_estimated(
        cls,
        value: T,
        confidence: float,
        source: str = "system",
        notes: Optional[str] = None,
        reference: Optional[str] = None
    ) -> "Fact[T]":
        """추정값 Fact 생성 헬퍼 메서드

        Args:
            value: 추정값
            confidence: 신뢰도 (0.0~1.0)
            source: 출처
            notes: 메모
            reference: 근거 자료

        Returns:
            추정값 Fact 객체
        """
        return cls(
            value=value,
            source=source,
            confidence=confidence,
            is_confirmed=False,
            entered_by="system",
            notes=notes,
            reference=reference
        )

    @classmethod
    def create_from_agent(
        cls,
        value: T,
        agent_id: str,
        reasoning: str,
        confidence: float = 0.9,
        rule_version: Optional[str] = None,
        reference: Optional[str] = None
    ) -> "Fact[T]":
        """AI Agent가 생성한 Fact 생성 헬퍼 메서드

        Args:
            value: Agent가 추론한 값
            agent_id: Agent 식별자
            reasoning: AI 판단 근거 (LLM 출력)
            confidence: 신뢰도 (0.0~1.0)
            rule_version: 적용한 세법 규칙 버전
            reference: 참조한 자료

        Returns:
            Agent 생성 Fact 객체
        """
        return cls(
            value=value,
            source="agent_generated",
            confidence=confidence,
            is_confirmed=False,  # Agent 생성 값은 기본적으로 미확정
            entered_by=agent_id,
            notes=f"AI Agent가 생성한 값 (Agent: {agent_id})",
            reference=reference,
            rule_version=rule_version,
            reasoning_trace=reasoning
        )

    def to_dict(self) -> dict:
        """딕셔너리로 변환

        Returns:
            Fact 정보를 담은 딕셔너리
        """
        return {
            'value': self.value,
            'source': self.source,
            'confidence': self.confidence,
            'is_confirmed': self.is_confirmed,
            'entered_by': self.entered_by,
            'entered_at': self.entered_at.isoformat(),
            'notes': self.notes,
            'reference': self.reference,
            'rule_version': self.rule_version,
            'reasoning_trace': self.reasoning_trace,
        }

    def __str__(self) -> str:
        """사람이 읽기 쉬운 형태로 출력"""
        status = "확정" if self.is_confirmed else f"추정({self.confidence:.0%})"
        return f"Fact({self.value}, {status}, by={self.entered_by})"

    def __repr__(self) -> str:
        return (
            f"Fact(value={self.value!r}, source={self.source!r}, "
            f"confidence={self.confidence}, is_confirmed={self.is_confirmed})"
        )
