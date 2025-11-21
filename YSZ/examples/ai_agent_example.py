"""AI 에이전트 시스템 사용 예제

AI 에이전트가 Fact를 생성하고, Rule Version을 추적하는 예제입니다.
"""

import asyncio
from datetime import date
from decimal import Decimal

from src.core import Fact, FactLedger, RuleVersion, RuleRegistry
from src.agents import (
    MockAgent,
    AgentPlan,
    AgentResult,
    PlannedAction,
    ResultStatus
)


async def example_1_agent_generated_fact():
    """예제 1: AI Agent가 Fact를 생성하는 시나리오"""
    print("=" * 60)
    print("예제 1: AI Agent가 Fact 생성")
    print("=" * 60)

    # AI Agent가 추론한 결과를 Fact로 생성
    is_primary_residence = Fact.create_from_agent(
        value=True,
        agent_id="asset_collector_001",
        reasoning="사용자가 2년 이상 실거주했으며, 다른 주택이 없음을 확인",
        confidence=0.95,
        rule_version="2024.1.0",
        reference="사용자 면담록 2024-11-21"
    )

    print(f"Agent가 생성한 Fact:")
    print(f"  값: {is_primary_residence.value}")
    print(f"  출처: {is_primary_residence.source}")
    print(f"  입력자: {is_primary_residence.entered_by}")
    print(f"  신뢰도: {is_primary_residence.confidence:.0%}")
    print(f"  확정 여부: {is_primary_residence.is_confirmed}")
    print(f"  규칙 버전: {is_primary_residence.rule_version}")
    print(f"  AI 근거: {is_primary_residence.reasoning_trace}")
    print()

    # 사용자가 검토 후 확정
    confirmed = is_primary_residence.confirm(
        confirmed_by="김세무사",
        notes="실거주 확인서 및 등기부등본 검토 완료"
    )

    print(f"확정 후:")
    print(f"  확정 여부: {confirmed.is_confirmed}")
    print(f"  신뢰도: {confirmed.confidence:.0%}")
    print(f"  확정자: {confirmed.entered_by}")
    print()


async def example_2_rule_version_management():
    """예제 2: Rule Version 관리"""
    print("=" * 60)
    print("예제 2: 세법 규칙 버전 관리")
    print("=" * 60)

    # RuleRegistry 생성
    registry = RuleRegistry()

    # 2023년 1세대 1주택 비과세 규칙
    rule_2023 = RuleVersion(
        rule_id="primary_residence_exemption",
        version="2023.1.0",
        effective_date=date(2023, 1, 1),
        rule_type="exemption",
        rule_data={
            "max_exemption": 900000000,  # 9억
            "holding_period_years": 2,
            "residence_period_years": 2
        },
        source="소득세법 제89조",
        description="1세대 1주택 비과세 (2023년)"
    )

    # 2024년 1세대 1주택 비과세 규칙 (한도 상향)
    rule_2024 = RuleVersion(
        rule_id="primary_residence_exemption",
        version="2024.1.0",
        effective_date=date(2024, 1, 1),
        rule_type="exemption",
        rule_data={
            "max_exemption": 1200000000,  # 12억
            "holding_period_years": 2,
            "residence_period_years": 2
        },
        source="소득세법 제89조",
        description="1세대 1주택 비과세 (2024년, 한도 상향)",
        supersedes="2023.1.0"
    )

    registry.register_rule(rule_2023)
    registry.register_rule(rule_2024)

    # 2023년 거래에는 2023년 규칙 적용
    disposal_date_2023 = date(2023, 6, 1)
    rule = registry.get_rule("primary_residence_exemption", disposal_date_2023)

    print(f"양도일: {disposal_date_2023}")
    print(f"적용 규칙: {rule.version}")
    print(f"비과세 한도: {rule.get_value('max_exemption'):,}원")
    print()

    # 2024년 거래에는 2024년 규칙 적용
    disposal_date_2024 = date(2024, 11, 1)
    rule = registry.get_rule("primary_residence_exemption", disposal_date_2024)

    print(f"양도일: {disposal_date_2024}")
    print(f"적용 규칙: {rule.version}")
    print(f"비과세 한도: {rule.get_value('max_exemption'):,}원")
    print()


async def example_3_agent_workflow():
    """예제 3: Agent의 Plan-Execute 워크플로우"""
    print("=" * 60)
    print("예제 3: Agent Plan-Execute 워크플로우")
    print("=" * 60)

    # Mock Agent 생성
    agent = MockAgent(
        agent_id="asset_collector_001",
        agent_type="asset_collector"
    )

    # 컨텍스트 준비
    context = {
        "user_input": {
            "acquisition_date": "2020-01-01",
            "disposal_date": "2023-12-31",
            "is_only_house": True,
            "residence_years": 3
        }
    }

    print(f"Agent: {agent}")
    print(f"초기 상태: {agent.get_status()}")
    print()

    # Agent 실행 (Plan -> Validate -> Execute)
    execution = await agent.run(context)

    print(f"실행 완료:")
    print(f"  실행 ID: {execution.execution_id}")
    print(f"  Agent: {execution.agent_type}")
    print(f"  실행 시간: {execution.duration_ms}ms")
    print()

    print(f"계획 (Plan):")
    if execution.plan:
        print(f"  계획 ID: {execution.plan.plan_id}")
        print(f"  추론: {execution.plan.reasoning or '(Mock Agent - 추론 없음)'}")
        print(f"  액션 수: {len(execution.plan.actions)}")
        print(f"  신뢰도: {execution.plan.confidence:.0%}")
    print()

    print(f"검증 (Validation):")
    if execution.plan_validation:
        print(f"  검증 통과: {execution.plan_validation.is_valid}")
        print(f"  오류: {execution.plan_validation.errors or '없음'}")
        print(f"  경고: {execution.plan_validation.warnings or '없음'}")
    print()

    print(f"실행 결과 (Result):")
    if execution.result:
        print(f"  결과 ID: {execution.result.result_id}")
        print(f"  상태: {execution.result.status.value}")
        print(f"  생성된 Facts: {len(execution.result.generated_facts)}개")
        print(f"  오류: {execution.result.errors or '없음'}")
    print()


async def example_4_full_scenario():
    """예제 4: 전체 시나리오 (사용자 입력 + Agent 추론 + 확정)"""
    print("=" * 60)
    print("예제 4: 전체 시나리오")
    print("=" * 60)

    # 1. 사용자 입력으로 FactLedger 생성
    print("Step 1: 사용자 입력 수집")
    ledger = FactLedger.create({
        "acquisition_date": date(2020, 1, 1),
        "acquisition_price": Decimal("500000000"),
        "disposal_date": date(2024, 11, 1),
        "disposal_price": Decimal("800000000")
    }, created_by="김세무사")

    print(f"  취득일: {ledger.acquisition_date.value}")
    print(f"  취득가액: {ledger.acquisition_price.value:,}원")
    print(f"  양도일: {ledger.disposal_date.value}")
    print(f"  양도가액: {ledger.disposal_price.value:,}원")
    print()

    # 2. Rule Registry 준비
    print("Step 2: 규칙 레지스트리 준비")
    registry = RuleRegistry()
    rule = RuleVersion(
        rule_id="primary_residence_exemption",
        version="2024.1.0",
        effective_date=date(2024, 1, 1),
        rule_type="exemption",
        rule_data={"max_exemption": 1200000000},
        source="소득세법 제89조",
        description="1세대 1주택 비과세"
    )
    registry.register_rule(rule)
    print(f"  규칙 등록: {rule.rule_id} v{rule.version}")
    print()

    # 3. Agent가 추가 정보 추론
    print("Step 3: Agent가 추가 정보 추론")
    agent = MockAgent(agent_id="asset_collector_001")

    # Agent가 보유기간 계산
    holding_years = (ledger.disposal_date.value - ledger.acquisition_date.value).days // 365

    holding_fact = Fact.create_from_agent(
        value=holding_years,
        agent_id="asset_collector_001",
        reasoning=f"취득일({ledger.acquisition_date.value})과 양도일({ledger.disposal_date.value})로부터 계산",
        rule_version="2024.1.0",
        confidence=1.0
    )

    ledger.update_field("residence_period_years", holding_fact)
    print(f"  Agent가 추론한 보유기간: {holding_years}년")
    print(f"  신뢰도: {holding_fact.confidence:.0%}")
    print(f"  확정 여부: {holding_fact.is_confirmed}")
    print()

    # Agent가 1세대 1주택 여부 추론
    is_primary = Fact.create_from_agent(
        value=True,
        agent_id="asset_collector_001",
        reasoning="보유기간 2년 이상, 사용자 면담 결과 실거주 확인",
        rule_version="2024.1.0",
        confidence=0.90
    )

    ledger.update_field("is_primary_residence", is_primary)
    print(f"  Agent가 추론한 1세대1주택: {is_primary.value}")
    print(f"  신뢰도: {is_primary.confidence:.0%}")
    print(f"  AI 근거: {is_primary.reasoning_trace}")
    print()

    # 4. 세무사 검토 및 확정
    print("Step 4: 세무사 검토 및 확정")
    confirmed_primary = is_primary.confirm(
        confirmed_by="김세무사",
        notes="실거주 확인서 및 전입세대 열람 결과 확인"
    )
    ledger.update_field("is_primary_residence", confirmed_primary)

    confirmed_holding = holding_fact.confirm(
        confirmed_by="김세무사",
        notes="등기부등본 확인"
    )
    ledger.update_field("residence_period_years", confirmed_holding)

    print(f"  1세대1주택 확정: {confirmed_primary.is_confirmed}")
    print(f"  보유기간 확정: {confirmed_holding.is_confirmed}")
    print()

    # 5. 양도차익 계산
    print("Step 5: 양도차익 계산")
    capital_gain = ledger.capital_gain
    print(f"  양도차익: {capital_gain:,}원")
    print()

    # 6. 감사 추적 정보
    print("Step 6: 감사 추적")
    print(f"  사용된 규칙 버전:")
    print(f"    - 1세대1주택: {ledger.is_primary_residence.rule_version}")
    print(f"    - 보유기간: {ledger.residence_period_years.rule_version}")
    print(f"  AI 판단 근거:")
    print(f"    - {ledger.is_primary_residence.reasoning_trace}")
    print()


async def main():
    """모든 예제 실행"""
    await example_1_agent_generated_fact()
    await example_2_rule_version_management()
    await example_3_agent_workflow()
    await example_4_full_scenario()


if __name__ == "__main__":
    asyncio.run(main())
