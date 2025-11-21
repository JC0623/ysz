"""Strategy Agent: 전략 수립 에이전트

케이스를 분류하고 여러 시나리오를 제시하는 핵심 에이전트입니다.

핵심 원칙:
1. 분류는 100% 결정론적 로직 (IF-THEN 규칙)
2. 시나리오 생성은 계산 기반 (TaxCalculator 활용)
3. LLM은 "설명 생성"과 "추가 조언"만 담당
"""

from typing import Dict, Any, Optional, List
from datetime import date, datetime, timedelta
from decimal import Decimal
import os

try:
    from anthropic import Anthropic
    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False

from .strategy_models import (
    Strategy,
    Scenario,
    Risk,
    MissingInfo,
    CaseCategory,
    RiskLevel,
    ClassificationRule
)
from ..core import FactLedger, TaxCalculator, RuleRegistry, get_default_registry


class StrategyAgent:
    """전략 수립 에이전트

    역할:
    1. 케이스 분류 (결정론적 규칙 기반)
    2. 시나리오 생성 (계산 기반)
    3. 리스크 분석 (규칙 기반)
    4. 추천 로직 (우선순위 기반)
    5. (선택) LLM으로 설명 생성
    """

    def __init__(
        self,
        rule_registry: Optional[RuleRegistry] = None,
        claude_api_key: Optional[str] = None,
        enable_llm: bool = False
    ):
        """
        Args:
            rule_registry: 규칙 레지스트리 (None이면 기본)
            claude_api_key: Claude API 키 (None이면 환경변수에서 읽음)
            enable_llm: LLM 설명 생성 활성화 (기본 False)
        """
        self.rule_registry = rule_registry or get_default_registry()
        self.calculator = TaxCalculator()

        # 분류 규칙 초기화
        self._classification_rules = self._init_classification_rules()

        # Claude 클라이언트 초기화 (선택적)
        self.enable_llm = enable_llm and CLAUDE_AVAILABLE
        self.claude = None

        if self.enable_llm:
            api_key = claude_api_key or os.getenv("ANTHROPIC_API_KEY")
            if api_key:
                self.claude = Anthropic(api_key=api_key)
            else:
                print("Warning: LLM enabled but no API key provided. LLM features disabled.")
                self.enable_llm = False

    def _init_classification_rules(self) -> List[ClassificationRule]:
        """분류 규칙 초기화 (결정론적)

        우선순위 순서대로 체크됩니다.
        """
        return [
            # 1. 범위 외 체크 (최우선)
            ClassificationRule(
                rule_id="R001",
                condition="법인 양도",
                category=CaseCategory.CORPORATE,
                priority=1
            ),
            ClassificationRule(
                rule_id="R002",
                condition="상속 취득 자산",
                category=CaseCategory.INHERITANCE,
                priority=2
            ),

            # 2. 다주택 체크
            ClassificationRule(
                rule_id="R010",
                condition="주택 수 >= 2 AND 조정대상지역",
                category=CaseCategory.ADJUSTED_AREA_HEAVY,
                priority=10
            ),
            ClassificationRule(
                rule_id="R011",
                condition="주택 수 >= 3",
                category=CaseCategory.MULTI_HOUSE_HEAVY,
                priority=11
            ),
            ClassificationRule(
                rule_id="R012",
                condition="주택 수 == 2",
                category=CaseCategory.MULTI_HOUSE_GENERAL,
                priority=12
            ),

            # 3. 1주택 체크
            ClassificationRule(
                rule_id="R020",
                condition="주택 수 == 1 AND 보유기간 >= 2년 AND 거주기간 >= 2년",
                category=CaseCategory.SINGLE_HOUSE_EXEMPT,
                priority=20
            ),
            ClassificationRule(
                rule_id="R021",
                condition="주택 수 == 1 AND (보유기간 < 2년 OR 거주기간 < 2년)",
                category=CaseCategory.SINGLE_HOUSE_TAXABLE,
                priority=21
            ),

            # 4. 기타
            ClassificationRule(
                rule_id="R099",
                condition="기타",
                category=CaseCategory.COMPLEX,
                priority=99
            )
        ]

    async def analyze(self, fact_ledger: FactLedger) -> Strategy:
        """케이스 분석 및 전략 수립

        Args:
            fact_ledger: 수집된 사실관계

        Returns:
            Strategy (분류 + 시나리오 + 추천)
        """
        strategy = Strategy()

        # 1. 케이스 분류 (결정론적)
        strategy.category, classification_rule = self._classify_case(fact_ledger)
        strategy.classification_reasoning = self._explain_classification(
            fact_ledger,
            strategy.category,
            classification_rule
        )
        strategy.classification_rules_applied = [classification_rule.rule_id] if classification_rule else []

        # 2. 시나리오 생성 (계산 기반)
        strategy.scenarios = await self._generate_scenarios(fact_ledger, strategy.category)

        # 3. 리스크 분석 (규칙 기반)
        strategy.risks = self._analyze_risks(fact_ledger, strategy.category)

        # 4. 추가 정보 체크
        strategy.missing_info = self._check_missing_info(fact_ledger, strategy.category)

        # 5. 추천 선택 (로직 기반)
        strategy.recommended_scenario_id = self._select_best_scenario(strategy.scenarios)
        strategy.recommendation_reasoning = self._explain_recommendation(strategy.scenarios, strategy.recommended_scenario_id)

        # 6. 신뢰도 계산
        strategy.confidence_score = self._calculate_confidence(fact_ledger, strategy)

        # 7. (선택) LLM으로 친절한 설명 생성
        if self.enable_llm and self.claude:
            strategy.llm_explanation = await self._generate_explanation_claude(strategy, fact_ledger)
            strategy.llm_additional_advice = await self._generate_advice_claude(strategy, fact_ledger)

        return strategy

    def _classify_case(self, ledger: FactLedger) -> tuple[CaseCategory, Optional[ClassificationRule]]:
        """케이스 분류 (결정론적)

        Returns:
            (CaseCategory, 적용된 규칙)
        """
        # 필드 추출
        house_count = ledger.house_count.value if ledger.house_count else 1
        is_adjusted_area = ledger.is_adjusted_area.value if ledger.is_adjusted_area else False

        # 보유기간 계산
        holding_years = 0
        if ledger.acquisition_date and ledger.disposal_date:
            days = (ledger.disposal_date.value - ledger.acquisition_date.value).days
            holding_years = days / 365.0

        # 거주기간
        residence_years = ledger.residence_period_years.value if ledger.residence_period_years else 0

        # 우선순위 순서대로 규칙 체크
        for rule in sorted(self._classification_rules, key=lambda r: r.priority):
            matched = False

            if rule.rule_id == "R001":  # 법인
                # MVP에서는 법인 케이스 없음
                matched = False

            elif rule.rule_id == "R002":  # 상속
                # 상속 여부는 asset_type이나 별도 플래그로 확인 가능
                matched = False

            elif rule.rule_id == "R010":  # 조정지역 다주택
                matched = (house_count >= 2 and is_adjusted_area)

            elif rule.rule_id == "R011":  # 3주택 이상
                matched = (house_count >= 3)

            elif rule.rule_id == "R012":  # 2주택
                matched = (house_count == 2)

            elif rule.rule_id == "R020":  # 1주택 비과세
                matched = (
                    house_count == 1
                    and holding_years >= 2
                    and residence_years >= 2
                )

            elif rule.rule_id == "R021":  # 1주택 과세
                matched = (
                    house_count == 1
                    and (holding_years < 2 or residence_years < 2)
                )

            elif rule.rule_id == "R099":  # 기타
                matched = True

            if matched:
                return rule.category, rule

        return CaseCategory.COMPLEX, None

    def _explain_classification(
        self,
        ledger: FactLedger,
        category: CaseCategory,
        rule: Optional[ClassificationRule]
    ) -> str:
        """분류 근거 설명 (로직 기반)"""
        lines = []

        lines.append(f"케이스 분류: {category.value}")

        if rule:
            lines.append(f"적용 규칙: {rule.rule_id} - {rule.condition}")

        # 판단 근거
        house_count = ledger.house_count.value if ledger.house_count else 1
        lines.append(f"보유 주택 수: {house_count}채")

        if ledger.acquisition_date and ledger.disposal_date:
            days = (ledger.disposal_date.value - ledger.acquisition_date.value).days
            years = days / 365.0
            lines.append(f"보유 기간: {years:.1f}년 ({days}일)")

        if ledger.residence_period_years:
            lines.append(f"거주 기간: {ledger.residence_period_years.value}년")

        if ledger.is_adjusted_area:
            lines.append(f"조정대상지역: {'예' if ledger.is_adjusted_area.value else '아니오'}")

        return "\n".join(lines)

    async def _generate_scenarios(
        self,
        ledger: FactLedger,
        category: CaseCategory
    ) -> List[Scenario]:
        """시나리오 생성 (계산 기반)

        각 카테고리별로 의미 있는 시나리오를 생성합니다.
        """
        scenarios = []

        # 시나리오 1: 현재 양도 (기본)
        scenario_now = await self._create_scenario_immediate(ledger, category)
        scenarios.append(scenario_now)

        # 시나리오 2: 1년 후 양도 (조건부)
        if category in [CaseCategory.SINGLE_HOUSE_TAXABLE, CaseCategory.MULTI_HOUSE_GENERAL]:
            scenario_later = await self._create_scenario_delayed(ledger, category, years=1)
            if scenario_later:
                scenarios.append(scenario_later)

        # 시나리오 3: 증여 후 양도 (고급)
        # 나중에 추가 가능

        return scenarios

    async def _create_scenario_immediate(
        self,
        ledger: FactLedger,
        category: CaseCategory
    ) -> Scenario:
        """즉시 양도 시나리오"""

        # 계산 수행
        result = self.calculator.calculate(ledger)

        scenario = Scenario(
            scenario_id="SC_NOW",
            name="지금_양도",
            description="현재 시점에서 즉시 양도",
            timing="즉시",
            actions=["양도"],
            expected_tax=result.calculated_tax,
            expected_local_tax=result.local_tax,
            total_cost=result.total_tax
        )

        # 장단점 (로직 기반)
        if category == CaseCategory.SINGLE_HOUSE_EXEMPT:
            scenario.pros = [
                "비과세 적용 (세금 0원)",
                "즉시 현금화 가능",
                "양도소득세 부담 없음"
            ]
            scenario.cons = [
                "향후 시세 상승 기회 상실"
            ]
            scenario.legal_basis = ["소득세법 제89조 (1세대 1주택 비과세)"]

        elif category == CaseCategory.SINGLE_HOUSE_TAXABLE:
            scenario.pros = [
                "즉시 현금화 가능"
            ]
            scenario.cons = [
                f"양도소득세 {result.total_tax:,}원 발생",
                "비과세 요건 미달"
            ]

        else:
            scenario.pros = ["즉시 현금화 가능"]
            scenario.cons = [f"양도소득세 {result.total_tax:,}원 발생"]

        # 필수 조건
        scenario.required_conditions = self._get_required_conditions(category)

        scenario.is_feasible = True

        return scenario

    async def _create_scenario_delayed(
        self,
        ledger: FactLedger,
        category: CaseCategory,
        years: int
    ) -> Optional[Scenario]:
        """{years}년 후 양도 시나리오"""

        # 미래 날짜로 조정된 FactLedger 생성
        future_ledger = self._create_future_ledger(ledger, years)

        # 미래 계산
        result = self.calculator.calculate(future_ledger)

        # 추가 비용 계산 (보유세 등)
        annual_holding_tax = self._estimate_holding_tax(ledger)

        scenario = Scenario(
            scenario_id=f"SC_DELAY_{years}Y",
            name=f"{years}년_후_양도",
            description=f"{years}년 더 보유 후 양도",
            timing=f"{years}년_후",
            actions=["보유", "양도"],
            expected_tax=result.calculated_tax,
            expected_local_tax=result.local_tax,
            total_cost=result.total_tax,
            additional_costs={
                f"{years}년_보유세": annual_holding_tax * years
            }
        )

        # 장단점
        scenario.pros = [
            f"{years}년 추가 보유로 비과세 요건 충족 가능",
            "시세 상승 시 이익"
        ]
        scenario.cons = [
            f"보유세 추가 부담 (연 {annual_holding_tax:,}원)",
            "시세 하락 리스크"
        ]

        scenario.required_conditions = [
            f"{years}년 이상 보유",
            "실거주 유지"
        ]

        scenario.is_feasible = True
        scenario.feasibility_notes = f"{years}년 대기 필요"

        return scenario

    def _create_future_ledger(self, ledger: FactLedger, years: int) -> FactLedger:
        """미래 시점의 FactLedger 생성"""
        # 새 FactLedger 생성 (얕은 복사)
        future_ledger = FactLedger()

        # 기존 필드 복사
        for field_name in ledger.__dataclass_fields__:
            setattr(future_ledger, field_name, getattr(ledger, field_name))

        # 양도일만 미래로 조정
        if ledger.disposal_date:
            future_date = ledger.disposal_date.value + timedelta(days=years * 365)
            from ..core import Fact
            future_ledger.disposal_date = Fact(
                value=future_date,
                source="scenario_simulation",
                entered_by="strategy_agent"
            )

        return future_ledger

    def _estimate_holding_tax(self, ledger: FactLedger) -> Decimal:
        """보유세 추정 (간단한 계산)"""
        if not ledger.disposal_price:
            return Decimal(0)

        # 간단히 시가의 0.1% 정도로 가정 (재산세 + 종부세 개략)
        estimated_value = ledger.disposal_price.value
        return estimated_value * Decimal("0.001")

    def _analyze_risks(self, ledger: FactLedger, category: CaseCategory) -> List[Risk]:
        """리스크 분석 (규칙 기반)"""
        risks = []

        # 리스크 1: 고액 양도차익
        if ledger.capital_gain and ledger.capital_gain > Decimal("500000000"):
            risks.append(Risk(
                risk_id="RISK_HIGH_GAIN",
                level=RiskLevel.MEDIUM,
                title="고액 양도차익",
                description=f"양도차익이 {ledger.capital_gain:,}원으로 고액입니다.",
                impact="세무 조사 대상이 될 가능성",
                mitigation="계산 근거 자료 철저히 준비"
            ))

        # 리스크 2: 비과세 요건 불확실
        if category == CaseCategory.SINGLE_HOUSE_EXEMPT:
            if not ledger.residence_period_years or not ledger.residence_period_years.is_confirmed:
                risks.append(Risk(
                    risk_id="RISK_RESIDENCE",
                    level=RiskLevel.HIGH,
                    title="실거주 기간 미확정",
                    description="실거주 기간이 확정되지 않았습니다.",
                    impact="비과세 적용 불가 시 세금 발생",
                    mitigation="전입세대 열람을 통해 실거주 기간 확정 필요"
                ))

        # 리스크 3: 조정대상지역 중과
        if ledger.is_adjusted_area and ledger.is_adjusted_area.value:
            risks.append(Risk(
                risk_id="RISK_ADJUSTED_AREA",
                level=RiskLevel.HIGH,
                title="조정대상지역 중과세",
                description="조정대상지역으로 세율이 높습니다.",
                impact="세액 증가 (최대 세율 적용)",
                mitigation="양도 시기 조정 또는 해제 시점 대기 고려"
            ))

        return risks

    def _check_missing_info(self, ledger: FactLedger, category: CaseCategory) -> List[MissingInfo]:
        """추가 필요 정보 체크"""
        missing = []

        # 필수 필드 체크
        if not ledger.residence_period_years:
            missing.append(MissingInfo(
                info_id="MISS_RESIDENCE",
                field_name="residence_period_years",
                description="실거주 기간",
                reason="비과세 적용 판단을 위해 필수",
                is_critical=True,
                how_to_obtain="전입세대 열람"
            ))

        if category == CaseCategory.SINGLE_HOUSE_EXEMPT:
            # 비과세 요건 확인 필요
            if ledger.is_primary_residence and not ledger.is_primary_residence.is_confirmed:
                missing.append(MissingInfo(
                    info_id="MISS_PRIMARY_CONFIRM",
                    field_name="is_primary_residence",
                    description="1세대 1주택 확정",
                    reason="비과세 적용 확정을 위해 필요",
                    is_critical=True,
                    how_to_obtain="세무사 확인"
                ))

        return missing

    def _select_best_scenario(self, scenarios: List[Scenario]) -> Optional[str]:
        """최적 시나리오 선택 (로직 기반)

        우선순위:
        1. 세금 최소화
        2. 순 편익 최대화
        3. 실행 가능성
        """
        if not scenarios:
            return None

        # 실행 가능한 시나리오만
        feasible = [s for s in scenarios if s.is_feasible]
        if not feasible:
            return scenarios[0].scenario_id

        # 순 편익 기준 정렬
        best = max(feasible, key=lambda s: s.net_benefit())

        return best.scenario_id

    def _explain_recommendation(
        self,
        scenarios: List[Scenario],
        recommended_id: Optional[str]
    ) -> str:
        """추천 근거 설명 (로직 기반)"""
        if not recommended_id:
            return "추천 시나리오 없음"

        recommended = next((s for s in scenarios if s.scenario_id == recommended_id), None)
        if not recommended:
            return "추천 시나리오 찾을 수 없음"

        lines = []
        lines.append(f"추천 시나리오: {recommended.name}")
        lines.append(f"예상 세금: {recommended.expected_tax:,}원")
        lines.append(f"순 편익: {recommended.net_benefit():,}원")

        # 다른 시나리오와 비교
        for other in scenarios:
            if other.scenario_id != recommended_id:
                diff = recommended.net_benefit() - other.net_benefit()
                lines.append(f"{other.name} 대비 {diff:,}원 유리")

        return "\n".join(lines)

    def _get_required_conditions(self, category: CaseCategory) -> List[str]:
        """카테고리별 필수 조건"""
        conditions_map = {
            CaseCategory.SINGLE_HOUSE_EXEMPT: [
                "2년 이상 보유",
                "2년 이상 실거주",
                "1세대 1주택"
            ],
            CaseCategory.SINGLE_HOUSE_TAXABLE: [
                "1세대 1주택"
            ],
            CaseCategory.MULTI_HOUSE_GENERAL: [
                "2주택 보유"
            ],
            CaseCategory.MULTI_HOUSE_HEAVY: [
                "3주택 이상 보유"
            ]
        }
        return conditions_map.get(category, [])

    def _calculate_confidence(self, ledger: FactLedger, strategy: Strategy) -> float:
        """전체 전략의 신뢰도 계산

        모든 Fact의 신뢰도를 종합합니다.
        """
        confidences = []

        # 주요 필드의 신뢰도 수집
        for field_name in ['acquisition_date', 'acquisition_price', 'disposal_date', 'disposal_price']:
            fact = getattr(ledger, field_name, None)
            if fact and hasattr(fact, 'confidence'):
                confidences.append(fact.confidence)

        if not confidences:
            return 0.5

        # 평균 신뢰도
        return sum(confidences) / len(confidences)

    async def _generate_explanation_claude(self, strategy: Strategy, ledger: FactLedger) -> str:
        """Claude로 사용자 친화적 설명 생성

        LLM은 계산이나 분류를 하지 않고, 이미 결정된 로직 결과를
        일반인도 이해할 수 있게 설명하는 역할만 합니다.
        """
        if not self.claude:
            return ""

        # 로직 결과 요약
        recommended = strategy.get_recommended_scenario()

        prompt = f"""당신은 세무 전문가입니다. 다음 양도소득세 분석 결과를 일반 고객이 이해하기 쉽게 설명해주세요.

**분석 결과 (이미 계산된 결과입니다)**
- 케이스 분류: {strategy.category.value}
- 총 시나리오: {len(strategy.scenarios)}개
- 추천 시나리오: {recommended.name if recommended else '없음'}
- 예상 세금: {recommended.expected_tax if recommended else 0:,}원

**고객 상황**
- 보유 주택: {ledger.house_count.value if ledger.house_count else 1}채
- 양도차익: {ledger.capital_gain:,}원
- 거주 기간: {ledger.residence_period_years.value if ledger.residence_period_years else '미확인'}년

**요청사항**
위 분석 결과를 바탕으로 고객에게 친절하게 설명해주세요 (3-5문장).
계산을 다시 하지 말고, 이미 나온 결과를 쉽게 풀어서 설명만 하세요.
전문 용어는 최소화하고, 고객이 어떤 선택을 할 수 있는지 안내해주세요.
"""

        try:
            message = self.claude.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                temperature=0.7,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            return message.content[0].text if message.content else ""

        except Exception as e:
            print(f"Claude explanation generation failed: {e}")
            return ""

    async def _generate_advice_claude(self, strategy: Strategy, ledger: FactLedger) -> str:
        """Claude로 추가 전문가 조언 생성

        로직으로 발견하기 어려운 엣지 케이스나 추가 고려사항을
        전문가 관점에서 제시합니다.
        """
        if not self.claude:
            return ""

        # 리스크 요약
        high_risks = [r.title for r in strategy.get_high_risks()]
        missing_info = [m.description for m in strategy.get_critical_missing_info()]

        prompt = f"""당신은 20년 경력의 세무사입니다. 다음 케이스에 대해 추가 전문가 조언을 해주세요.

**케이스 개요**
- 분류: {strategy.category.value}
- 고위험 요소: {', '.join(high_risks) if high_risks else '없음'}
- 부족 정보: {', '.join(missing_info) if missing_info else '없음'}

**요청사항**
1. 이 케이스에서 주의해야 할 추가 사항 (로직으로 발견 못한 것)
2. 국세청 세무조사 대비 팁
3. 세법 개정 시 고려사항
4. 유사 케이스에서 자주 발생하는 실수

간결하게 3-4개 bullet point로 작성해주세요.
"""

        try:
            message = self.claude.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                temperature=0.7,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            return message.content[0].text if message.content else ""

        except Exception as e:
            print(f"Claude advice generation failed: {e}")
            return ""
