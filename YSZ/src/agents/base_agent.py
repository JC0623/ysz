"""Base Agent: 모든 AI 에이전트의 기반 클래스

핵심 원칙:
1. 계획(Plan) - LLM이 생성
2. 검증(Validate) - 규칙 기반 검증
3. 실행(Execute) - 결정론적 코드 실행
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Protocol
from datetime import datetime
import time

from .agent_models import (
    AgentPlan,
    AgentResult,
    AgentStatus,
    AgentExecution,
    ValidationResult,
    ResultStatus
)
from ..core.fact_ledger import FactLedger
from ..core.rule_version import RuleRegistry, get_default_registry


class AgentProtocol(Protocol):
    """모든 Agent가 따라야 하는 인터페이스

    Protocol을 사용하여 duck typing을 지원합니다.
    """

    agent_id: str
    agent_type: str

    async def plan(self, context: Dict[str, Any]) -> AgentPlan:
        """계획 생성 (LLM 호출)"""
        ...

    async def execute(self, plan: AgentPlan, context: Dict[str, Any]) -> AgentResult:
        """계획 실행 (결정론적)"""
        ...

    def get_status(self) -> AgentStatus:
        """현재 상태 조회"""
        ...


class BaseAgent(ABC):
    """모든 Agent의 기반 클래스

    Plan-Validate-Execute 패턴을 구현합니다.

    Attributes:
        agent_id: Agent 고유 식별자
        agent_type: Agent 유형
        rule_registry: 규칙 레지스트리
        status: 현재 상태
        current_execution: 현재 실행 중인 AgentExecution
    """

    def __init__(
        self,
        agent_id: str,
        agent_type: str,
        rule_registry: Optional[RuleRegistry] = None
    ):
        """
        Args:
            agent_id: Agent 고유 ID
            agent_type: Agent 유형 ("asset_collector", "calculator", etc.)
            rule_registry: 규칙 레지스트리 (None이면 기본 레지스트리 사용)
        """
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.rule_registry = rule_registry or get_default_registry()
        self.status = AgentStatus.IDLE
        self.current_execution: Optional[AgentExecution] = None

    async def run(self, context: Dict[str, Any]) -> AgentExecution:
        """전체 Agent 실행 (Plan -> Validate -> Execute)

        Args:
            context: 실행 컨텍스트
                - fact_ledger: FactLedger (선택)
                - user_input: 사용자 입력
                - rule_snapshot: 규칙 스냅샷 (선택)

        Returns:
            AgentExecution 객체 (계획, 검증, 결과 포함)
        """
        execution = AgentExecution(
            agent_id=self.agent_id,
            agent_type=self.agent_type
        )
        self.current_execution = execution

        try:
            # 1. Plan (LLM)
            self.status = AgentStatus.PLANNING
            plan = await self.plan(context)
            execution.plan = plan

            # 2. Validate (Rule-based)
            self.status = AgentStatus.VALIDATING
            validation = self.validate_plan(plan, context)
            execution.plan_validation = validation

            if not validation.is_valid:
                # 검증 실패
                result = AgentResult(
                    agent_id=self.agent_id,
                    agent_type=self.agent_type,
                    plan_id=plan.plan_id,
                    status=ResultStatus.FAILED
                )
                result.errors.extend(validation.errors)
                execution.result = result
                execution.complete()
                self.status = AgentStatus.FAILED
                return execution

            # 3. Execute (Deterministic)
            self.status = AgentStatus.EXECUTING
            start_time = time.time()

            result = await self.execute(plan, context)
            result.execution_time_ms = int((time.time() - start_time) * 1000)

            execution.result = result

            # 추적 정보 업데이트
            if 'fact_ledger' in context:
                execution.facts_read = self._get_facts_read(context['fact_ledger'])
            execution.facts_created = list(result.generated_facts.keys())
            execution.rules_applied = plan.applicable_rules

            execution.complete()
            self.status = AgentStatus.COMPLETED

            return execution

        except Exception as e:
            # 실행 중 오류
            result = AgentResult(
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                plan_id=execution.plan.plan_id if execution.plan else "",
                status=ResultStatus.FAILED
            )
            result.add_error(f"Execution failed: {str(e)}")

            execution.result = result
            execution.complete()
            self.status = AgentStatus.FAILED

            raise

    @abstractmethod
    async def plan(self, context: Dict[str, Any]) -> AgentPlan:
        """계획 생성 (LLM 호출)

        서브클래스에서 반드시 구현해야 합니다.
        LLM을 호출하여 Agent의 실행 계획을 생성합니다.

        Args:
            context: 컨텍스트 정보

        Returns:
            생성된 AgentPlan
        """
        pass

    @abstractmethod
    async def execute(self, plan: AgentPlan, context: Dict[str, Any]) -> AgentResult:
        """계획 실행 (결정론적)

        서브클래스에서 반드시 구현해야 합니다.
        계획을 기반으로 실제 작업을 수행합니다. (LLM 호출 없음)

        Args:
            plan: 실행할 계획
            context: 컨텍스트 정보

        Returns:
            실행 결과 AgentResult
        """
        pass

    def validate_plan(self, plan: AgentPlan, context: Dict[str, Any]) -> ValidationResult:
        """계획 검증 (규칙 기반)

        생성된 계획이 세법 규칙에 맞는지 검증합니다.
        서브클래스에서 필요시 오버라이드할 수 있습니다.

        Args:
            plan: 검증할 계획
            context: 컨텍스트 정보

        Returns:
            검증 결과
        """
        validation = ValidationResult()

        # 기본 검증: 필수 필드 확인
        if not plan.actions:
            validation.add_error("Plan has no actions")

        if not plan.reasoning:
            validation.add_warning("Plan has no reasoning provided")

        # 규칙 버전 확인
        for rule_id in plan.applicable_rules:
            rule = self.rule_registry.get_rule_by_version(rule_id, plan.rule_version or "")
            if not rule:
                validation.add_error(f"Rule {rule_id} version {plan.rule_version} not found")

        # 서브클래스에서 추가 검증 로직 구현 가능
        self._validate_plan_custom(plan, context, validation)

        return validation

    def _validate_plan_custom(
        self,
        plan: AgentPlan,
        context: Dict[str, Any],
        validation: ValidationResult
    ) -> None:
        """커스텀 계획 검증 (서브클래스 오버라이드용)

        Args:
            plan: 검증할 계획
            context: 컨텍스트
            validation: 검증 결과 (여기에 오류/경고 추가)
        """
        pass

    def get_status(self) -> AgentStatus:
        """현재 Agent 상태 조회

        Returns:
            현재 AgentStatus
        """
        return self.status

    def _get_facts_read(self, fact_ledger: FactLedger) -> list[str]:
        """읽은 Fact 필드 목록 추출

        Args:
            fact_ledger: FactLedger

        Returns:
            Fact 필드명 리스트
        """
        # 실제로는 실행 중 추적이 필요하지만, 여기서는 모든 non-None 필드 반환
        facts_read = []
        for field_name in fact_ledger.__dataclass_fields__:
            if field_name.startswith('_'):
                continue
            fact = getattr(fact_ledger, field_name, None)
            if fact is not None:
                facts_read.append(field_name)
        return facts_read

    def __str__(self) -> str:
        return f"{self.agent_type}Agent(id={self.agent_id}, status={self.status.value})"

    def __repr__(self) -> str:
        return f"BaseAgent(agent_id={self.agent_id!r}, agent_type={self.agent_type!r})"


class MockAgent(BaseAgent):
    """테스트용 Mock Agent

    LLM 없이 미리 정의된 계획과 결과를 반환합니다.
    """

    def __init__(
        self,
        agent_id: str = "mock_agent",
        agent_type: str = "mock",
        mock_plan: Optional[AgentPlan] = None,
        mock_result: Optional[AgentResult] = None
    ):
        super().__init__(agent_id, agent_type)
        self.mock_plan = mock_plan
        self.mock_result = mock_result

    async def plan(self, context: Dict[str, Any]) -> AgentPlan:
        """Mock 계획 반환"""
        if self.mock_plan:
            return self.mock_plan

        # 기본 Mock 계획
        return AgentPlan(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            reasoning="Mock reasoning",
            actions=[],
            model_used="mock",
            confidence=1.0
        )

    async def execute(self, plan: AgentPlan, context: Dict[str, Any]) -> AgentResult:
        """Mock 결과 반환"""
        if self.mock_result:
            self.mock_result.plan_id = plan.plan_id
            return self.mock_result

        # 기본 Mock 결과
        return AgentResult(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            plan_id=plan.plan_id,
            status=ResultStatus.SUCCESS
        )
