"""StrategyAgent 테스트

결정론적 로직 기반 분류 및 시나리오 생성 테스트
"""

import pytest
from datetime import date
from decimal import Decimal

from src.core import Fact, FactLedger
from src.agents import StrategyAgent, CaseCategory, RiskLevel


class TestCaseClassification:
    """케이스 분류 테스트 (결정론적)"""

    @pytest.mark.asyncio
    async def test_single_house_exempt(self):
        """1주택 비과세 케이스"""
        agent = StrategyAgent()

        # 비과세 조건 충족: 1주택, 2년 이상 보유, 2년 이상 거주
        ledger = FactLedger.create({
            "acquisition_date": date(2020, 1, 1),
            "acquisition_price": Decimal("500000000"),
            "disposal_date": date(2024, 6, 1),
            "disposal_price": Decimal("700000000"),
            "house_count": 1,
            "residence_period_years": 3
        })

        strategy = await agent.analyze(ledger)

        assert strategy.category == CaseCategory.SINGLE_HOUSE_EXEMPT
        assert "R020" in strategy.classification_rules_applied
        assert len(strategy.scenarios) > 0
        assert strategy.scenarios[0].expected_tax == Decimal(0)  # 비과세

    @pytest.mark.asyncio
    async def test_single_house_taxable(self):
        """1주택 과세 케이스 (보유기간 미달)"""
        agent = StrategyAgent()

        # 비과세 요건 미달: 1주택이지만 보유기간 1년
        ledger = FactLedger.create({
            "acquisition_date": date(2023, 1, 1),
            "acquisition_price": Decimal("500000000"),
            "disposal_date": date(2024, 6, 1),
            "disposal_price": Decimal("700000000"),
            "house_count": 1,
            "residence_period_years": 1
        })

        strategy = await agent.analyze(ledger)

        assert strategy.category == CaseCategory.SINGLE_HOUSE_TAXABLE
        assert "R021" in strategy.classification_rules_applied
        assert len(strategy.scenarios) > 0
        # 과세되므로 세금 > 0
        assert strategy.scenarios[0].expected_tax > Decimal(0)

    @pytest.mark.asyncio
    async def test_multi_house_general(self):
        """2주택 일반과세 케이스"""
        agent = StrategyAgent()

        ledger = FactLedger.create({
            "acquisition_date": date(2020, 1, 1),
            "acquisition_price": Decimal("500000000"),
            "disposal_date": date(2024, 6, 1),
            "disposal_price": Decimal("700000000"),
            "house_count": 2,
            "is_adjusted_area": False
        })

        strategy = await agent.analyze(ledger)

        assert strategy.category == CaseCategory.MULTI_HOUSE_GENERAL
        assert "R012" in strategy.classification_rules_applied

    @pytest.mark.asyncio
    async def test_multi_house_heavy(self):
        """3주택 이상 중과 케이스"""
        agent = StrategyAgent()

        ledger = FactLedger.create({
            "acquisition_date": date(2020, 1, 1),
            "acquisition_price": Decimal("500000000"),
            "disposal_date": date(2024, 6, 1),
            "disposal_price": Decimal("700000000"),
            "house_count": 3
        })

        strategy = await agent.analyze(ledger)

        assert strategy.category == CaseCategory.MULTI_HOUSE_HEAVY
        assert "R011" in strategy.classification_rules_applied


class TestScenarioGeneration:
    """시나리오 생성 테스트 (계산 기반)"""

    @pytest.mark.asyncio
    async def test_immediate_scenario(self):
        """즉시 양도 시나리오"""
        agent = StrategyAgent()

        ledger = FactLedger.create({
            "acquisition_date": date(2020, 1, 1),
            "acquisition_price": Decimal("500000000"),
            "disposal_date": date(2024, 6, 1),
            "disposal_price": Decimal("700000000"),
            "house_count": 1,
            "residence_period_years": 3
        })

        strategy = await agent.analyze(ledger)

        # 기본적으로 "지금_양도" 시나리오는 항상 생성
        now_scenario = next(s for s in strategy.scenarios if s.scenario_id == "SC_NOW")
        assert now_scenario is not None
        assert now_scenario.name == "지금_양도"
        assert now_scenario.timing == "즉시"
        assert len(now_scenario.pros) > 0
        assert len(now_scenario.cons) > 0

    @pytest.mark.asyncio
    async def test_multiple_scenarios_for_taxable(self):
        """과세 케이스는 여러 시나리오 생성"""
        agent = StrategyAgent()

        # 1주택이지만 보유 1년 (비과세 미달)
        ledger = FactLedger.create({
            "acquisition_date": date(2023, 6, 1),
            "acquisition_price": Decimal("500000000"),
            "disposal_date": date(2024, 6, 1),
            "disposal_price": Decimal("700000000"),
            "house_count": 1,
            "residence_period_years": 1
        })

        strategy = await agent.analyze(ledger)

        # 과세 케이스는 "지금"과 "1년 후" 시나리오 생성
        assert len(strategy.scenarios) >= 2

        # "1년_후_양도" 시나리오 확인
        later_scenario = next((s for s in strategy.scenarios if "DELAY" in s.scenario_id), None)
        assert later_scenario is not None
        assert "보유세" in later_scenario.additional_costs or len(later_scenario.additional_costs) > 0

    @pytest.mark.asyncio
    async def test_scenario_net_benefit(self):
        """시나리오 순 편익 계산"""
        agent = StrategyAgent()

        ledger = FactLedger.create({
            "acquisition_date": date(2020, 1, 1),
            "acquisition_price": Decimal("500000000"),
            "disposal_date": date(2024, 6, 1),
            "disposal_price": Decimal("700000000"),
            "house_count": 1,
            "residence_period_years": 3
        })

        strategy = await agent.analyze(ledger)
        scenario = strategy.scenarios[0]

        # 순 편익 = 예상 수익 - (세금 + 추가 비용)
        net = scenario.net_benefit()
        assert isinstance(net, Decimal)


class TestRiskAnalysis:
    """리스크 분석 테스트 (규칙 기반)"""

    @pytest.mark.asyncio
    async def test_high_capital_gain_risk(self):
        """고액 양도차익 리스크"""
        agent = StrategyAgent()

        # 양도차익 5억 이상
        ledger = FactLedger.create({
            "acquisition_date": date(2020, 1, 1),
            "acquisition_price": Decimal("300000000"),
            "disposal_date": date(2024, 6, 1),
            "disposal_price": Decimal("1000000000"),  # 차익 7억
            "house_count": 1,
            "residence_period_years": 3
        })

        strategy = await agent.analyze(ledger)

        # 고액 양도차익 리스크 발견
        high_gain_risk = next((r for r in strategy.risks if r.risk_id == "RISK_HIGH_GAIN"), None)
        assert high_gain_risk is not None
        assert high_gain_risk.level in [RiskLevel.MEDIUM, RiskLevel.HIGH]

    @pytest.mark.asyncio
    async def test_unconfirmed_residence_risk(self):
        """미확정 실거주 리스크"""
        agent = StrategyAgent()

        # 실거주 기간이 Fact이지만 미확정
        ledger = FactLedger()
        ledger.acquisition_date = Fact(value=date(2020, 1, 1), is_confirmed=True)
        ledger.acquisition_price = Fact(value=Decimal("500000000"), is_confirmed=True)
        ledger.disposal_date = Fact(value=date(2024, 6, 1), is_confirmed=True)
        ledger.disposal_price = Fact(value=Decimal("700000000"), is_confirmed=True)
        ledger.house_count = Fact(value=1, is_confirmed=True)
        ledger.residence_period_years = Fact(
            value=3,
            is_confirmed=False,  # 미확정!
            confidence=0.8
        )

        strategy = await agent.analyze(ledger)

        # 실거주 기간 미확정 리스크
        residence_risk = next((r for r in strategy.risks if r.risk_id == "RISK_RESIDENCE"), None)
        assert residence_risk is not None
        assert residence_risk.level == RiskLevel.HIGH

    @pytest.mark.asyncio
    async def test_adjusted_area_risk(self):
        """조정대상지역 리스크"""
        agent = StrategyAgent()

        ledger = FactLedger.create({
            "acquisition_date": date(2020, 1, 1),
            "acquisition_price": Decimal("500000000"),
            "disposal_date": date(2024, 6, 1),
            "disposal_price": Decimal("700000000"),
            "house_count": 2,
            "is_adjusted_area": True  # 조정대상지역!
        })

        strategy = await agent.analyze(ledger)

        # 조정지역 중과 리스크
        adjusted_risk = next((r for r in strategy.risks if r.risk_id == "RISK_ADJUSTED_AREA"), None)
        assert adjusted_risk is not None
        assert adjusted_risk.level == RiskLevel.HIGH


class TestMissingInfo:
    """추가 필요 정보 체크 테스트"""

    @pytest.mark.asyncio
    async def test_missing_residence_period(self):
        """실거주 기간 누락"""
        agent = StrategyAgent()

        ledger = FactLedger.create({
            "acquisition_date": date(2020, 1, 1),
            "acquisition_price": Decimal("500000000"),
            "disposal_date": date(2024, 6, 1),
            "disposal_price": Decimal("700000000"),
            "house_count": 1
            # residence_period_years 누락!
        })

        strategy = await agent.analyze(ledger)

        # 실거주 기간 필요
        residence_missing = next((m for m in strategy.missing_info if m.field_name == "residence_period_years"), None)
        assert residence_missing is not None
        assert residence_missing.is_critical is True


class TestRecommendation:
    """추천 로직 테스트"""

    @pytest.mark.asyncio
    async def test_recommendation_logic(self):
        """최적 시나리오 추천 로직"""
        agent = StrategyAgent()

        ledger = FactLedger.create({
            "acquisition_date": date(2020, 1, 1),
            "acquisition_price": Decimal("500000000"),
            "disposal_date": date(2024, 6, 1),
            "disposal_price": Decimal("700000000"),
            "house_count": 1,
            "residence_period_years": 3
        })

        strategy = await agent.analyze(ledger)

        # 추천 시나리오가 있어야 함
        assert strategy.recommended_scenario_id is not None

        # 추천 시나리오 조회 가능
        recommended = strategy.get_recommended_scenario()
        assert recommended is not None

        # 추천 근거 있음
        assert len(strategy.recommendation_reasoning) > 0

    @pytest.mark.asyncio
    async def test_best_scenario_is_lowest_tax(self):
        """최적 시나리오는 세금이 가장 적은 것"""
        agent = StrategyAgent()

        # 비과세 케이스
        ledger = FactLedger.create({
            "acquisition_date": date(2020, 1, 1),
            "acquisition_price": Decimal("500000000"),
            "disposal_date": date(2024, 6, 1),
            "disposal_price": Decimal("700000000"),
            "house_count": 1,
            "residence_period_years": 3
        })

        strategy = await agent.analyze(ledger)
        recommended = strategy.get_recommended_scenario()

        # 비과세이므로 추천 시나리오의 세금은 0
        assert recommended.expected_tax == Decimal(0)


class TestConfidence:
    """신뢰도 계산 테스트"""

    @pytest.mark.asyncio
    async def test_confidence_with_confirmed_facts(self):
        """확정된 Fact들의 신뢰도"""
        agent = StrategyAgent()

        ledger = FactLedger()
        ledger.acquisition_date = Fact(value=date(2020, 1, 1), is_confirmed=True, confidence=1.0)
        ledger.acquisition_price = Fact(value=Decimal("500000000"), is_confirmed=True, confidence=1.0)
        ledger.disposal_date = Fact(value=date(2024, 6, 1), is_confirmed=True, confidence=1.0)
        ledger.disposal_price = Fact(value=Decimal("700000000"), is_confirmed=True, confidence=1.0)
        ledger.house_count = Fact(value=1, is_confirmed=True, confidence=1.0)

        strategy = await agent.analyze(ledger)

        # 모두 확정이므로 신뢰도 1.0
        assert strategy.confidence_score == 1.0

    @pytest.mark.asyncio
    async def test_confidence_with_estimated_facts(self):
        """추정된 Fact들의 신뢰도"""
        agent = StrategyAgent()

        ledger = FactLedger()
        ledger.acquisition_date = Fact(value=date(2020, 1, 1), confidence=0.8)
        ledger.acquisition_price = Fact(value=Decimal("500000000"), confidence=0.9)
        ledger.disposal_date = Fact(value=date(2024, 6, 1), confidence=1.0)
        ledger.disposal_price = Fact(value=Decimal("700000000"), confidence=0.85)

        strategy = await agent.analyze(ledger)

        # 평균 신뢰도
        expected = (0.8 + 0.9 + 1.0 + 0.85) / 4
        assert abs(strategy.confidence_score - expected) < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
