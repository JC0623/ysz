"""AI 에이전트 시스템 통합 테스트

AI 에이전트의 Fact-First, Plan-Execute 패턴을 테스트합니다.
"""

import pytest
from datetime import date, datetime
from decimal import Decimal

from src.core import Fact, FactLedger, RuleVersion, RuleRegistry
from src.agents import (
    BaseAgent,
    MockAgent,
    AgentPlan,
    AgentResult,
    AgentStatus,
    PlannedAction,
    ResultStatus
)


class TestFactEnhancements:
    """Fact 클래스 강화 테스트"""

    def test_fact_with_rule_version(self):
        """Fact에 rule_version 추가 테스트"""
        fact = Fact(
            value=Decimal("500000000"),
            source="agent_generated",
            rule_version="2024.1.0",
            entered_by="asset_collector_agent"
        )

        assert fact.rule_version == "2024.1.0"
        assert fact.source == "agent_generated"

    def test_fact_with_reasoning_trace(self):
        """Fact에 reasoning_trace 추가 테스트"""
        reasoning = "1세대 1주택으로 판단됨. 보유기간 2년 이상, 실거주 확인."

        fact = Fact(
            value=True,
            source="agent_generated",
            reasoning_trace=reasoning,
            entered_by="asset_collector_agent"
        )

        assert fact.reasoning_trace == reasoning
        assert fact.value is True

    def test_fact_create_from_agent(self):
        """Agent가 생성한 Fact 헬퍼 메서드 테스트"""
        fact = Fact.create_from_agent(
            value=True,
            agent_id="asset_collector_001",
            reasoning="보유기간 2년 이상 확인",
            confidence=0.95,
            rule_version="2024.1.0"
        )

        assert fact.value is True
        assert fact.source == "agent_generated"
        assert fact.entered_by == "asset_collector_001"
        assert fact.reasoning_trace == "보유기간 2년 이상 확인"
        assert fact.rule_version == "2024.1.0"
        assert fact.confidence == 0.95
        assert fact.is_confirmed is False


class TestRuleVersion:
    """RuleVersion 시스템 테스트"""

    def test_rule_version_creation(self):
        """RuleVersion 생성 테스트"""
        rule = RuleVersion(
            rule_id="primary_residence_exemption",
            version="2024.1.0",
            effective_date=date(2024, 1, 1),
            rule_type="exemption",
            rule_data={
                "max_exemption": 1200000000,
                "holding_period_years": 2
            },
            source="소득세법 제89조",
            description="1세대 1주택 비과세"
        )

        assert rule.rule_id == "primary_residence_exemption"
        assert rule.version == "2024.1.0"
        assert rule.get_value("max_exemption") == 1200000000

    def test_rule_effective_date(self):
        """규칙 시행일 검증 테스트"""
        rule = RuleVersion(
            rule_id="test_rule",
            version="2024.1.0",
            effective_date=date(2024, 1, 1),
            rule_type="test",
            rule_data={},
            source="test",
            description="test"
        )

        assert rule.is_effective_on(date(2024, 6, 1)) is True
        assert rule.is_effective_on(date(2023, 12, 31)) is False

    def test_rule_registry(self):
        """RuleRegistry 기본 동작 테스트"""
        registry = RuleRegistry()

        rule = RuleVersion(
            rule_id="test_rule",
            version="2024.1.0",
            effective_date=date(2024, 1, 1),
            rule_type="test",
            rule_data={"value": 100},
            source="test",
            description="test"
        )

        registry.register_rule(rule)

        # 최신 규칙 가져오기
        latest = registry.get_latest_rule("test_rule")
        assert latest is not None
        assert latest.version == "2024.1.0"

        # 날짜 기준 규칙 가져오기
        effective_rule = registry.get_rule("test_rule", date(2024, 6, 1))
        assert effective_rule is not None
        assert effective_rule.version == "2024.1.0"

    def test_rule_registry_multiple_versions(self):
        """여러 버전의 규칙 관리 테스트"""
        registry = RuleRegistry()

        # 2023 버전
        rule_2023 = RuleVersion(
            rule_id="tax_rate",
            version="2023.1.0",
            effective_date=date(2023, 1, 1),
            rule_type="rate",
            rule_data={"rate": 0.40},
            source="test",
            description="2023 세율"
        )

        # 2024 버전
        rule_2024 = RuleVersion(
            rule_id="tax_rate",
            version="2024.1.0",
            effective_date=date(2024, 1, 1),
            rule_type="rate",
            rule_data={"rate": 0.45},
            source="test",
            description="2024 세율",
            supersedes="2023.1.0"
        )

        registry.register_rule(rule_2023)
        registry.register_rule(rule_2024)

        # 2023년 거래 -> 2023 규칙
        rule = registry.get_rule("tax_rate", date(2023, 6, 1))
        assert rule.version == "2023.1.0"
        assert rule.get_value("rate") == 0.40

        # 2024년 거래 -> 2024 규칙
        rule = registry.get_rule("tax_rate", date(2024, 6, 1))
        assert rule.version == "2024.1.0"
        assert rule.get_value("rate") == 0.45

        # 최신 규칙
        latest = registry.get_latest_rule("tax_rate")
        assert latest.version == "2024.1.0"


class TestAgentModels:
    """Agent 모델 테스트"""

    def test_agent_plan_creation(self):
        """AgentPlan 생성 테스트"""
        plan = AgentPlan(
            agent_id="asset_collector_001",
            agent_type="asset_collector",
            reasoning="사용자 입력에서 1세대 1주택으로 보임",
            actions=[
                PlannedAction(
                    action_type="collect_fact",
                    description="보유기간 계산",
                    parameters={"field": "holding_period_years"}
                )
            ],
            applicable_rules=["primary_residence_exemption"],
            rule_version="2024.1.0",
            model_used="gpt-4",
            confidence=0.95
        )

        assert plan.agent_type == "asset_collector"
        assert len(plan.actions) == 1
        assert plan.confidence == 0.95

    def test_agent_result_creation(self):
        """AgentResult 생성 테스트"""
        result = AgentResult(
            agent_id="asset_collector_001",
            agent_type="asset_collector",
            plan_id="test-plan-id",
            status=ResultStatus.SUCCESS
        )

        # Fact 추가
        fact = Fact.create_from_agent(
            value=2,
            agent_id="asset_collector_001",
            reasoning="계산 결과 2년",
            rule_version="2024.1.0"
        )
        result.add_fact("holding_period_years", fact)

        assert len(result.generated_facts) == 1
        assert "holding_period_years" in result.generated_facts
        assert result.status == ResultStatus.SUCCESS

    def test_agent_result_error_handling(self):
        """AgentResult 오류 처리 테스트"""
        result = AgentResult(
            agent_id="test_agent",
            agent_type="test",
            plan_id="test-plan"
        )

        result.add_warning("경고: 데이터 불완전")
        assert len(result.warnings) == 1

        result.add_error("오류: 필수 필드 누락")
        assert len(result.errors) == 1
        assert result.status == ResultStatus.PARTIAL

        result.mark_failed("치명적 오류")
        assert result.status == ResultStatus.FAILED
        assert len(result.errors) == 2


class TestBaseAgent:
    """BaseAgent 테스트"""

    @pytest.mark.asyncio
    async def test_mock_agent_basic(self):
        """MockAgent 기본 동작 테스트"""
        agent = MockAgent(
            agent_id="test_agent_001",
            agent_type="test"
        )

        assert agent.get_status() == AgentStatus.IDLE

        # Plan 생성
        context = {"test": "data"}
        plan = await agent.plan(context)

        assert plan.agent_id == "test_agent_001"
        assert plan.agent_type == "test"

        # Execute
        result = await agent.execute(plan, context)

        assert result.agent_id == "test_agent_001"
        assert result.status == ResultStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_agent_run_workflow(self):
        """Agent의 Plan-Validate-Execute 전체 워크플로우 테스트"""
        agent = MockAgent(
            agent_id="workflow_test_agent",
            agent_type="test"
        )

        context = {"test": "workflow"}

        # 전체 실행
        execution = await agent.run(context)

        assert execution.agent_id == "workflow_test_agent"
        assert execution.plan is not None
        assert execution.plan_validation is not None
        assert execution.plan_validation.is_valid is True
        assert execution.result is not None
        assert execution.result.status == ResultStatus.SUCCESS
        assert execution.completed_at is not None
        assert execution.duration_ms > 0

    @pytest.mark.asyncio
    async def test_agent_validation_failure(self):
        """계획 검증 실패 테스트"""
        # 빈 액션의 계획 (검증 실패)
        mock_plan = AgentPlan(
            agent_id="test",
            agent_type="test",
            reasoning="",  # 빈 reasoning
            actions=[]  # 빈 액션
        )

        agent = MockAgent(mock_plan=mock_plan)
        context = {}

        execution = await agent.run(context)

        assert execution.plan_validation is not None
        assert execution.plan_validation.is_valid is False
        assert len(execution.plan_validation.errors) > 0
        assert execution.result.status == ResultStatus.FAILED


class TestIntegration:
    """통합 시나리오 테스트"""

    @pytest.mark.asyncio
    async def test_fact_ledger_with_agent_facts(self):
        """Agent가 생성한 Fact를 FactLedger에 추가하는 시나리오"""

        # 1. 초기 FactLedger (사용자 입력)
        ledger = FactLedger.create({
            "acquisition_date": date(2020, 1, 1),
            "acquisition_price": Decimal("500000000"),
            "disposal_date": date(2023, 12, 31),
            "disposal_price": Decimal("700000000")
        }, created_by="김세무사")

        # 2. Agent가 추가 정보 추론
        agent = MockAgent(agent_id="asset_collector_001")

        # Agent가 생성한 Fact
        is_primary_residence_fact = Fact.create_from_agent(
            value=True,
            agent_id="asset_collector_001",
            reasoning="보유기간 2년 이상, 실거주 확인",
            rule_version="2024.1.0",
            confidence=0.95
        )

        # 3. FactLedger 업데이트
        ledger.update_field("is_primary_residence", is_primary_residence_fact)

        # 4. 검증
        assert ledger.is_primary_residence is not None
        assert ledger.is_primary_residence.value is True
        assert ledger.is_primary_residence.source == "agent_generated"
        assert ledger.is_primary_residence.rule_version == "2024.1.0"
        assert ledger.is_primary_residence.is_confirmed is False

        # 5. 사용자가 확정
        confirmed_fact = is_primary_residence_fact.confirm(
            confirmed_by="김세무사",
            notes="실거주 확인 완료"
        )
        ledger.update_field("is_primary_residence", confirmed_fact)

        assert ledger.is_primary_residence.is_confirmed is True
        assert ledger.is_primary_residence.confidence == 1.0

    def test_rule_snapshot_for_case(self):
        """케이스 처리 시작 시 규칙 스냅샷 생성"""
        registry = RuleRegistry()

        # 여러 규칙 등록
        registry.register_rule(RuleVersion(
            rule_id="tax_rate",
            version="2024.1.0",
            effective_date=date(2024, 1, 1),
            rule_type="rate",
            rule_data={"rate": 0.45},
            source="test",
            description="test"
        ))

        registry.register_rule(RuleVersion(
            rule_id="exemption",
            version="2024.1.0",
            effective_date=date(2024, 1, 1),
            rule_type="exemption",
            rule_data={"max": 1200000000},
            source="test",
            description="test"
        ))

        # 2024년 6월 1일 기준 스냅샷
        snapshot = registry.snapshot(date(2024, 6, 1))

        assert len(snapshot) == 2
        assert "tax_rate" in snapshot
        assert "exemption" in snapshot
        assert snapshot["tax_rate"].version == "2024.1.0"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
