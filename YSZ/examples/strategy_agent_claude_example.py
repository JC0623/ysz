"""StrategyAgent with Claude Integration 예제

Claude 3.5 Sonnet을 사용한 사용자 친화적 설명 생성 예제
"""

import asyncio
from datetime import date
from decimal import Decimal

from src.core import FactLedger
from src.agents import StrategyAgent


async def example_with_claude():
    """Claude 통합 예제"""
    print("=" * 60)
    print("StrategyAgent + Claude 3.5 Sonnet 통합 예제")
    print("=" * 60)

    # 1. FactLedger 생성
    ledger = FactLedger.create({
        "acquisition_date": date(2020, 1, 1),
        "acquisition_price": Decimal("500000000"),
        "disposal_date": date(2024, 11, 21),
        "disposal_price": Decimal("800000000"),
        "house_count": 1,
        "residence_period_years": 4
    }, created_by="김세무사")

    print("\n📋 사실관계:")
    print(f"  취득일: {ledger.acquisition_date.value}")
    print(f"  취득가: {ledger.acquisition_price.value:,}원")
    print(f"  양도일: {ledger.disposal_date.value}")
    print(f"  양도가: {ledger.disposal_price.value:,}원")
    print(f"  양도차익: {ledger.capital_gain:,}원")
    print(f"  주택 수: {ledger.house_count.value}채")
    print(f"  거주 기간: {ledger.residence_period_years.value}년")

    # 2. StrategyAgent (Claude 활성화)
    # 주의: ANTHROPIC_API_KEY 환경변수 필요
    agent = StrategyAgent(enable_llm=True)

    print("\n🔄 분석 중...")
    strategy = await agent.analyze(ledger)

    # 3. 로직 기반 결과
    print("\n" + "=" * 60)
    print("📊 로직 기반 분석 결과 (100% 결정론적)")
    print("=" * 60)

    print(f"\n케이스 분류: {strategy.category.value}")
    print(f"적용 규칙: {strategy.classification_rules_applied}")

    print(f"\n💡 시나리오 ({len(strategy.scenarios)}개):")
    for i, scenario in enumerate(strategy.scenarios, 1):
        print(f"\n{i}. {scenario.name}")
        print(f"   예상 세금: {scenario.expected_tax:,}원")
        print(f"   총 비용: {scenario.total_cost:,}원")
        print(f"   순 편익: {scenario.net_benefit():,}원")

    print(f"\n✅ 추천 시나리오: {strategy.recommended_scenario_id}")

    print(f"\n⚠️ 리스크 ({len(strategy.risks)}건):")
    for risk in strategy.risks:
        print(f"  - [{risk.level.value}] {risk.title}")

    print(f"\n📈 신뢰도: {strategy.confidence_score:.0%}")

    # 4. Claude가 생성한 설명
    print("\n" + "=" * 60)
    print("🤖 Claude 3.5 Sonnet 생성 설명 (LLM)")
    print("=" * 60)

    if strategy.llm_explanation:
        print("\n💬 고객용 설명:")
        print(strategy.llm_explanation)
    else:
        print("\n(Claude API 키가 설정되지 않았거나 LLM이 비활성화되었습니다)")

    if strategy.llm_additional_advice:
        print("\n👨‍💼 전문가 추가 조언:")
        print(strategy.llm_additional_advice)

    print("\n" + "=" * 60)


async def example_without_claude():
    """Claude 없이 사용 (로직만)"""
    print("=" * 60)
    print("StrategyAgent (로직만, LLM 없음)")
    print("=" * 60)

    ledger = FactLedger.create({
        "acquisition_date": date(2023, 6, 1),
        "acquisition_price": Decimal("500000000"),
        "disposal_date": date(2024, 11, 21),
        "disposal_price": Decimal("700000000"),
        "house_count": 1,
        "residence_period_years": 1
    }, created_by="김세무사")

    # Claude 비활성화 (기본값)
    agent = StrategyAgent(enable_llm=False)

    strategy = await agent.analyze(ledger)

    print(f"\n케이스 분류: {strategy.category.value}")
    print(f"시나리오 수: {len(strategy.scenarios)}개")
    print(f"추천: {strategy.recommended_scenario_id}")

    print("\n✅ LLM 없이도 완벽히 동작!")
    print(f"llm_explanation: {strategy.llm_explanation or '(생성 안 됨)'}")
    print(f"llm_additional_advice: {strategy.llm_additional_advice or '(생성 안 됨)'}")

    print()


async def example_high_gain_case():
    """고액 양도차익 케이스 (Claude 조언 유용)"""
    print("=" * 60)
    print("고액 양도차익 케이스 + Claude 조언")
    print("=" * 60)

    ledger = FactLedger.create({
        "acquisition_date": date(2020, 1, 1),
        "acquisition_price": Decimal("300000000"),
        "disposal_date": date(2024, 11, 21),
        "disposal_price": Decimal("1200000000"),  # 차익 9억!
        "house_count": 1,
        "residence_period_years": 4
    }, created_by="김세무사")

    agent = StrategyAgent(enable_llm=True)
    strategy = await agent.analyze(ledger)

    print(f"\n양도차익: {ledger.capital_gain:,}원")
    print(f"\n⚠️ 발견된 리스크 ({len(strategy.risks)}건):")
    for risk in strategy.risks:
        print(f"  - [{risk.level.value}] {risk.title}: {risk.description}")

    if strategy.llm_additional_advice:
        print("\n👨‍💼 Claude의 추가 조언 (고액 차익 대비):")
        print(strategy.llm_additional_advice)

    print()


async def example_comparison():
    """같은 케이스, LLM 유/무 비교"""
    print("=" * 60)
    print("비교: LLM 유 vs 무")
    print("=" * 60)

    ledger = FactLedger.create({
        "acquisition_date": date(2020, 1, 1),
        "acquisition_price": Decimal("500000000"),
        "disposal_date": date(2024, 11, 21),
        "disposal_price": Decimal("700000000"),
        "house_count": 1,
        "residence_period_years": 3
    }, created_by="김세무사")

    # LLM 없이
    agent_no_llm = StrategyAgent(enable_llm=False)
    strategy_no_llm = await agent_no_llm.analyze(ledger)

    # LLM 사용
    agent_with_llm = StrategyAgent(enable_llm=True)
    strategy_with_llm = await agent_with_llm.analyze(ledger)

    print("\n📊 로직 결과 (동일해야 함):")
    print(f"  LLM 없음: {strategy_no_llm.category.value}, 세금 {strategy_no_llm.scenarios[0].expected_tax:,}원")
    print(f"  LLM 있음: {strategy_with_llm.category.value}, 세금 {strategy_with_llm.scenarios[0].expected_tax:,}원")

    assert strategy_no_llm.category == strategy_with_llm.category
    assert strategy_no_llm.scenarios[0].expected_tax == strategy_with_llm.scenarios[0].expected_tax
    print("  ✅ 로직 결과 동일 확인!")

    print("\n💬 설명 (차이):")
    print(f"  LLM 없음: {strategy_no_llm.llm_explanation or '(없음)'}")
    print(f"  LLM 있음: {strategy_with_llm.llm_explanation[:100] if strategy_with_llm.llm_explanation else '(없음)'}...")

    print()


async def main():
    """모든 예제 실행"""
    print("\n🚀 StrategyAgent + Claude 통합 예제 시작\n")

    # 예제 1: Claude 통합
    await example_with_claude()

    # 예제 2: Claude 없이 (로직만)
    await example_without_claude()

    # 예제 3: 고액 차익 케이스
    await example_high_gain_case()

    # 예제 4: 비교
    await example_comparison()

    print("\n✅ 모든 예제 완료!\n")


if __name__ == "__main__":
    # 환경변수 설정 안내
    print("\n" + "=" * 60)
    print("⚠️ 주의사항")
    print("=" * 60)
    print("Claude 기능을 사용하려면 환경변수 설정이 필요합니다:")
    print("  export ANTHROPIC_API_KEY='your-api-key'")
    print("또는 코드에서 직접 전달:")
    print("  agent = StrategyAgent(claude_api_key='your-key', enable_llm=True)")
    print("=" * 60 + "\n")

    asyncio.run(main())
