"""Agent Models: AI 에이전트 계획 및 실행 결과 모델

LLM이 생성한 계획(Plan)과 결정론적 실행 결과(Result)를 구분하여 관리합니다.

핵심 원칙:
- AgentPlan: LLM 출력 (비결정론적, 감사용)
- AgentResult: 코드 실행 결과 (결정론적, 계산 추적)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import uuid4
from enum import Enum

from ..core.fact import Fact
from ..core.calculation_trace import CalculationTrace


class AgentStatus(str, Enum):
    """Agent 상태"""
    IDLE = "idle"
    PLANNING = "planning"
    VALIDATING = "validating"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


class ResultStatus(str, Enum):
    """실행 결과 상태"""
    SUCCESS = "success"
    PARTIAL = "partial"  # 일부만 성공
    FAILED = "failed"


@dataclass
class PlannedAction:
    """Agent가 수행할 계획된 액션

    Attributes:
        action_type: 액션 유형 ("collect_fact", "calculate", "verify", "search_rule")
        description: 액션 설명 (LLM 출력)
        parameters: 액션 파라미터
        required_facts: 이 액션에 필요한 Fact 필드
        expected_output: 예상 출력 (LLM의 추측)
    """
    action_type: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    required_facts: List[str] = field(default_factory=list)
    expected_output: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'action_type': self.action_type,
            'description': self.description,
            'parameters': self.parameters,
            'required_facts': self.required_facts,
            'expected_output': self.expected_output
        }


@dataclass
class AgentPlan:
    """Agent의 실행 계획 (LLM 출력)

    LLM이 생성한 계획으로, 비결정론적이며 감사 추적용으로 저장됩니다.

    Attributes:
        plan_id: 계획 고유 ID
        agent_id: 이 계획을 생성한 Agent ID
        agent_type: Agent 유형 ("asset_collector", "calculator", etc.)
        created_at: 생성 시각

        reasoning: LLM의 사고 과정 (CoT)
        actions: 수행할 액션 목록
        required_facts: 필요한 Fact 필드 목록

        applicable_rules: 적용될 세법 규칙 ID 목록
        rule_version: 사용할 규칙 버전

        model_used: 사용된 LLM 모델
        temperature: LLM temperature
        confidence: 계획의 신뢰도 (0.0~1.0)
    """
    plan_id: str = field(default_factory=lambda: str(uuid4()))
    agent_id: str = ""
    agent_type: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    # LLM 출력
    reasoning: str = ""
    actions: List[PlannedAction] = field(default_factory=list)
    required_facts: List[str] = field(default_factory=list)

    # 규칙 참조
    applicable_rules: List[str] = field(default_factory=list)
    rule_version: Optional[str] = None

    # 메타데이터
    model_used: str = "unknown"
    temperature: float = 0.0
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'plan_id': self.plan_id,
            'agent_id': self.agent_id,
            'agent_type': self.agent_type,
            'created_at': self.created_at.isoformat(),
            'reasoning': self.reasoning,
            'actions': [action.to_dict() for action in self.actions],
            'required_facts': self.required_facts,
            'applicable_rules': self.applicable_rules,
            'rule_version': self.rule_version,
            'model_used': self.model_used,
            'temperature': self.temperature,
            'confidence': self.confidence
        }

    def __str__(self) -> str:
        return (
            f"AgentPlan(id={self.plan_id[:8]}, agent={self.agent_type}, "
            f"actions={len(self.actions)}, confidence={self.confidence:.0%})"
        )


@dataclass
class AgentResult:
    """Agent의 실행 결과 (결정론적)

    Agent가 계획을 실행한 결과로, 생성된 Facts와 계산 추적을 포함합니다.

    Attributes:
        result_id: 결과 고유 ID
        agent_id: 실행한 Agent ID
        agent_type: Agent 유형
        plan_id: 실행한 계획 ID
        executed_at: 실행 시각

        generated_facts: 생성된 Facts (field_name -> Fact)
        calculations: 계산 결과 (calculation_name -> value)
        calculation_traces: 계산 추적 목록

        status: 실행 상태
        errors: 오류 목록
        warnings: 경고 목록

        execution_time_ms: 실행 시간 (밀리초)
        code_version: 실행된 코드의 버전
    """
    result_id: str = field(default_factory=lambda: str(uuid4()))
    agent_id: str = ""
    agent_type: str = ""
    plan_id: str = ""
    executed_at: datetime = field(default_factory=datetime.now)

    # 생성된 데이터
    generated_facts: Dict[str, Fact] = field(default_factory=dict)
    calculations: Dict[str, Any] = field(default_factory=dict)
    calculation_traces: List[CalculationTrace] = field(default_factory=list)

    # 상태
    status: ResultStatus = ResultStatus.SUCCESS
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # 메타데이터
    execution_time_ms: int = 0
    code_version: str = "1.0.0"

    def add_fact(self, field_name: str, fact: Fact) -> None:
        """생성된 Fact 추가

        Args:
            field_name: Fact 필드명
            fact: Fact 객체
        """
        self.generated_facts[field_name] = fact

    def add_calculation(self, name: str, value: Any, trace: Optional[CalculationTrace] = None) -> None:
        """계산 결과 추가

        Args:
            name: 계산 이름
            value: 계산 값
            trace: 계산 추적 (선택)
        """
        self.calculations[name] = value
        if trace:
            self.calculation_traces.append(trace)

    def add_error(self, error: str) -> None:
        """오류 추가

        Args:
            error: 오류 메시지
        """
        self.errors.append(error)
        if self.status == ResultStatus.SUCCESS:
            self.status = ResultStatus.PARTIAL

    def add_warning(self, warning: str) -> None:
        """경고 추가

        Args:
            warning: 경고 메시지
        """
        self.warnings.append(warning)

    def mark_failed(self, error: str) -> None:
        """실패로 표시

        Args:
            error: 실패 사유
        """
        self.status = ResultStatus.FAILED
        self.add_error(error)

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'result_id': self.result_id,
            'agent_id': self.agent_id,
            'agent_type': self.agent_type,
            'plan_id': self.plan_id,
            'executed_at': self.executed_at.isoformat(),
            'generated_facts': {
                k: v.to_dict() for k, v in self.generated_facts.items()
            },
            'calculations': self.calculations,
            'calculation_traces': [trace.to_dict() for trace in self.calculation_traces],
            'status': self.status.value,
            'errors': self.errors,
            'warnings': self.warnings,
            'execution_time_ms': self.execution_time_ms,
            'code_version': self.code_version
        }

    def __str__(self) -> str:
        return (
            f"AgentResult(id={self.result_id[:8]}, agent={self.agent_type}, "
            f"status={self.status.value}, facts={len(self.generated_facts)})"
        )


@dataclass
class ValidationResult:
    """계획 검증 결과

    Agent의 계획이 세법 규칙에 맞는지 검증한 결과입니다.

    Attributes:
        is_valid: 검증 통과 여부
        errors: 검증 오류 목록
        warnings: 검증 경고 목록
        validated_at: 검증 시각
    """
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    validated_at: datetime = field(default_factory=datetime.now)

    def add_error(self, error: str) -> None:
        """검증 오류 추가

        Args:
            error: 오류 메시지
        """
        self.is_valid = False
        self.errors.append(error)

    def add_warning(self, warning: str) -> None:
        """검증 경고 추가

        Args:
            warning: 경고 메시지
        """
        self.warnings.append(warning)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'is_valid': self.is_valid,
            'errors': self.errors,
            'warnings': self.warnings,
            'validated_at': self.validated_at.isoformat()
        }


@dataclass
class AgentExecution:
    """Agent 실행 기록 (감사용)

    한 번의 Agent 실행 전체를 기록합니다.

    Attributes:
        execution_id: 실행 고유 ID
        agent_id: Agent ID
        agent_type: Agent 유형
        started_at: 시작 시각
        completed_at: 완료 시각

        plan: Agent의 계획
        plan_validation: 계획 검증 결과
        result: 실행 결과

        facts_read: 읽은 Fact 필드 목록
        facts_created: 생성한 Fact 필드 목록
        rules_applied: 적용한 규칙 ID 목록
    """
    execution_id: str = field(default_factory=lambda: str(uuid4()))
    agent_id: str = ""
    agent_type: str = ""
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    # 계획 & 검증
    plan: Optional[AgentPlan] = None
    plan_validation: Optional[ValidationResult] = None

    # 실행 결과
    result: Optional[AgentResult] = None

    # 추적 정보
    facts_read: List[str] = field(default_factory=list)
    facts_created: List[str] = field(default_factory=list)
    rules_applied: List[str] = field(default_factory=list)

    def complete(self) -> None:
        """실행 완료 표시"""
        self.completed_at = datetime.now()

    @property
    def duration_ms(self) -> int:
        """실행 시간 (밀리초)"""
        if self.completed_at:
            delta = self.completed_at - self.started_at
            return int(delta.total_seconds() * 1000)
        return 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'execution_id': self.execution_id,
            'agent_id': self.agent_id,
            'agent_type': self.agent_type,
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'plan': self.plan.to_dict() if self.plan else None,
            'plan_validation': self.plan_validation.to_dict() if self.plan_validation else None,
            'result': self.result.to_dict() if self.result else None,
            'facts_read': self.facts_read,
            'facts_created': self.facts_created,
            'rules_applied': self.rules_applied,
            'duration_ms': self.duration_ms
        }

    def __str__(self) -> str:
        status = "completed" if self.completed_at else "running"
        return (
            f"AgentExecution(id={self.execution_id[:8]}, agent={self.agent_type}, "
            f"status={status}, duration={self.duration_ms}ms)"
        )
