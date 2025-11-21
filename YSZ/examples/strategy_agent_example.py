"""StrategyAgent 사용 예제

결정론적 로직 기반의 케이스 분류 및 시나리오 생성 예제
"""

import asyncio
from datetime import date
from decimal import Decimal

from src.core import Fact, FactLedger
from src.agents import StrategyAgent, CaseCategory


async def example_1_single_house_exempt():
    """예제 1: 1주택 비과세 케이스"""
    print("=" * 60)
    print("예제 1: 1주택 비과세 케이스 분석")
    print("=" * 60)

    # FactLedger 생성
    ledger = FactLedger.create({
        "acquisition_date": date(2020, 1, 1),
        "acquisition_price": Decimal("500000000"),
        "disposal_date": date(2024, 11, 21),
        "disposal_price": Decimal("800000000"),
        "house_count": 1,
        "residence_period_years": 4
    }, created_by="김세무사")

    # StrategyAgent로 분석
    agent = StrategyAgent()
    strategy = await agent.analyze(ledger)

    print(f"\n📊 분류 결과: {strategy.category.value}")
    print(f"적용 규칙: {strategy.classification_rules_applied}")
    print(f"\n분류 근거:")
    print(strategy.classification_reasoning)

    print(f"\n💡 시나리오 ({len(strategy.scenarios)}개)")
    for i, scenario in enumerate(strategy.scenarios, 1):
        print(f"\n{i}. {scenario.name}")
        print(f"   예상 세금: {scenario.expected_tax:,}원")
        print(f"   지방세: {scenario.expected_local_tax:,}원")
        print(f"   총 비용: {scenario.total_cost:,}원")
        print(f"   장점: {', '.join(scenario.pros)}")
        print(f"   단점: {', '.join(scenario.cons)}")
        if scenario.additional_costs:
            print(f"   추가 비용: {scenario.additional_costs}")

    print(f"\n✅ 추천: {strategy.recommended_scenario_id}")
    print(f"추천 근거:")
    print(strategy.recommendation_reasoning)

    print(f"\n⚠️ 리스크 ({len(strategy.risks)}건)")
    for risk in strategy.risks:
        print(f"- [{risk.level.value}] {risk.title}: {risk.description}")

    print(f"\n📝 신뢰도: {strategy.confidence_score:.0%}")
    print()


async def example_2_single_house_taxable():
    """예제 2: 1주택 과세 케이스 (보유기간 미달)"""
    print("=" * 60)
    print("예제 2: 1주택 과세 케이스 (비과세 요건 미달)")
    print("=" * 60)

    # 보유기간 1년 (비과세 요건 2년 미달)
    ledger = FactLedger.create({
        "acquisition_date": date(2023, 6, 1),
        "acquisition_price": Decimal("500000000"),
        "disposal_date": date(2024, 11, 21),
        "disposal_price": Decimal("700000000"),
        "house_count": 1,
        "residence_period_years": 1
    }, created_by="김세무사")

    agent = StrategyAgent()
    strategy = await agent.analyze(ledger)

    print(f"\n📊 분류 결과: {strategy.category.value}")
    print(f"\n분류 근거:")
    print(strategy.classification_reasoning)

    print(f"\n💡 시나리오 ({len(strategy.scenarios)}개)")
    for i, scenario in enumerate(strategy.scenarios, 1):
        print(f"\n{i}. {scenario.name}")
        print(f"   타이밍: {scenario.timing}")
        print(f"   예상 세금: {scenario.expected_tax:,}원")
        print(f"   순 편익: {scenario.net_benefit():,}원")

        if scenario.additional_costs:
            print(f"   추가 비용:")
            for cost_name, amount in scenario.additional_costs.items():
                print(f"     - {cost_name}: {amount:,}원")

    recommended = strategy.get_recommended_scenario()
    if recommended:
        print(f"\n✅ 추천 시나리오: {recommended.name}")
        print(f"   예상 세금: {recommended.expected_tax:,}원")
        print(f"   이유: {strategy.recommendation_reasoning}")

    print()


async def example_3_multi_house():
    """예제 3: 다주택 케이스"""
    print("=" * 60)
    print("예제 3: 다주택 케이스")
    print("=" * 60)

    # 2주택 보유
    ledger = FactLedger.create({
        "acquisition_date": date(2020, 1, 1),
        "acquisition_price": Decimal("500000000"),
        "disposal_date": date(2024, 11, 21),
        "disposal_price": Decimal("800000000"),
        "house_count": 2,  # 2주택!
        "is_adjusted_area": False
    }, created_by="김세무사")

    agent = StrategyAgent()
    strategy = await agent.analyze(ledger)

    print(f"\n📊 분류 결과: {strategy.category.value}")
    print(f"적용 규칙: {strategy.classification_rules_applied}")

    # MVP 범위 체크
    if strategy.category not in [CaseCategory.SINGLE_HOUSE_EXEMPT, CaseCategory.SINGLE_HOUSE_TAXABLE]:
        print(f"\n⚠️ 주의: 이 케이스는 현재 MVP 범위를 벗어납니다.")
        print(f"다주택 케이스는 Phase 2에서 지원 예정입니다.")
    else:
        print(f"\n💡 시나리오:")
        for scenario in strategy.scenarios:
            print(f"- {scenario.name}: 세금 {scenario.expected_tax:,}원")

    print()


async def example_4_risk_analysis():
    """예제 4: 리스크 분석"""
    print("=" * 60)
    print("예제 4: 리스크 분석")
    print("=" * 60)

    # 고액 양도차익 + 미확정 실거주
    ledger = FactLedger()
    ledger.acquisition_date = Fact(value=date(2020, 1, 1), is_confirmed=True)
    ledger.acquisition_price = Fact(value=Decimal("300000000"), is_confirmed=True)
    ledger.disposal_date = Fact(value=date(2024, 11, 21), is_confirmed=True)
    ledger.disposal_price = Fact(value=Decimal("1200000000"), is_confirmed=True)  # 차익 9억!
    ledger.house_count = Fact(value=1, is_confirmed=True)
    ledger.residence_period_years = Fact(
        value=3,
        is_confirmed=False,  # 미확정!
        confidence=0.8,
        entered_by="agent_estimated"
    )

    agent = StrategyAgent()
    strategy = await agent.analyze(ledger)

    print(f"\n📊 분류: {strategy.category.value}")
    print(f"양도차익: {ledger.capital_gain:,}원")

    print(f"\n⚠️ 식별된 리스크 ({len(strategy.risks)}건):")
    for risk in strategy.risks:
        print(f"\n- 리스크 ID: {risk.risk_id}")
        print(f"  수준: {risk.level.value.upper()}")
        print(f"  제목: {risk.title}")
        print(f"  설명: {risk.description}")
        print(f"  영향: {risk.impact}")
        if risk.mitigation:
            print(f"  완화 방안: {risk.mitigation}")

    # 고위험 리스크만 필터링
    high_risks = strategy.get_high_risks()
    print(f"\n🚨 높은 리스크: {len(high_risks)}건")
    for risk in high_risks:
        print(f"- {risk.title}")

    print()


async def example_5_missing_info():
    """예제 5: 추가 필요 정보"""
    print("=" * 60)
    print("예제 5: 추가 필요 정보 체크")
    print("=" * 60)

    # 실거주 기간 정보 없음
    ledger = FactLedger.create({
        "acquisition_date": date(2020, 1, 1),
        "acquisition_price": Decimal("500000000"),
        "disposal_date": date(2024, 11, 21),
        "disposal_price": Decimal("700000000"),
        "house_count": 1
        # residence_period_years 누락!
    }, created_by="김세무사")

    agent = StrategyAgent()
    strategy = await agent.analyze(ledger)

    print(f"\n📊 분류: {strategy.category.value}")

    print(f"\n📝 추가 필요 정보 ({len(strategy.missing_info)}건):")
    for info in strategy.missing_info:
        print(f"\n- 필드: {info.field_name}")
        print(f"  설명: {info.description}")
        print(f"  이유: {info.reason}")
        print(f"  필수 여부: {'필수' if info.is_critical else '선택'}")
        if info.how_to_obtain:
            print(f"  취득 방법: {info.how_to_obtain}")

    # 실행 가능 여부
    print(f"\n✅ 실행 가능 여부: {strategy.is_ready_to_execute()}")

    if not strategy.is_ready_to_execute():
        critical = strategy.get_critical_missing_info()
        print(f"필수 정보 {len(critical)}건이 부족합니다:")
        for info in critical:
            print(f"  - {info.description}")

    print()


async def example_6_scenario_comparison():
    """예제 6: 시나리오 비교"""
    print("=" * 60)
    print("예제 6: 여러 시나리오 비교")
    print("=" * 60)

    # 1년 보유 (비과세 미달)
    ledger = FactLedger.create({
        "acquisition_date": date(2023, 6, 1),
        "acquisition_price": Decimal("500000000"),
        "disposal_date": date(2024, 11, 21),
        "disposal_price": Decimal("700000000"),
        "house_count": 1,
        "residence_period_years": 1
    }, created_by="김세무사")

    agent = StrategyAgent()
    strategy = await agent.analyze(ledger)

    print(f"\n📊 케이스: {strategy.category.value}")
    print(f"\n💡 시나리오 비교표:")
    print("-" * 80)
    print(f"{'시나리오':<20} {'타이밍':<10} {'예상세금':>15} {'추가비용':>15} {'순편익':>15}")
    print("-" * 80)

    for scenario in strategy.scenarios:
        add_cost = sum(scenario.additional_costs.values(), Decimal(0))
        net = scenario.net_benefit()

        print(
            f"{scenario.name:<20} "
            f"{scenario.timing:<10} "
            f"{scenario.expected_tax:>15,} "
            f"{add_cost:>15,} "
            f"{net:>15,}"
        )

    print("-" * 80)

    recommended = strategy.get_recommended_scenario()
    if recommended:
        print(f"\n✅ 추천: {recommended.name}")
        print(f"   이유: 순 편익 최대 ({recommended.net_benefit():,}원)")

    print()


async def main():
    """모든 예제 실행"""
    await example_1_single_house_exempt()
    await example_2_single_house_taxable()
    await example_3_multi_house()
    await example_4_risk_analysis()
    await example_5_missing_info()
    await example_6_scenario_comparison()


if __name__ == "__main__":
    asyncio.run(main())
