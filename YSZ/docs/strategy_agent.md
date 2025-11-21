# StrategyAgent: 전략 수립 에이전트

**작성일**: 2025-11-21
**버전**: 1.0

## 개요

StrategyAgent는 세무사의 핵심 업무인 "케이스 분류"와 "시나리오 제시"를 자동화하는 에이전트입니다.

### 핵심 철학

**"LLM은 보조, 로직이 주인공"**

1. **분류는 100% 결정론적** - IF-THEN 규칙으로 명확히
2. **시나리오는 계산 기반** - TaxCalculator로 정확하게
3. **LLM은 설명만** - 친절한 설명과 추가 조언 생성용 (선택)

---

## 핵심 기능

### 1. 케이스 분류 (Classification)

**입력**: FactLedger
**출력**: CaseCategory
**방식**: 결정론적 규칙 (ClassificationRule)

#### 지원하는 카테고리

| 카테고리 | 조건 | 규칙 ID |
|---------|------|---------|
| 1주택_비과세 | 주택 1채 + 보유 2년 + 거주 2년 | R020 |
| 1주택_과세 | 주택 1채 + (보유<2년 OR 거주<2년) | R021 |
| 다주택_일반 | 주택 2채 + 비조정지역 | R012 |
| 다주택_중과 | 주택 3채 이상 | R011 |
| 조정지역_중과 | 주택 2채 이상 + 조정지역 | R010 |

#### 분류 로직

```python
# 우선순위 순서대로 규칙 체크
for rule in sorted(rules, key=priority):
    if rule.condition_matches(ledger):
        return rule.category
```

**특징**:
- 명확한 IF-THEN 로직
- 우선순위 기반 (높은 우선순위부터 체크)
- 100% 재현 가능
- LLM 사용 안 함!

---

### 2. 시나리오 생성 (Scenario Generation)

**입력**: FactLedger + CaseCategory
**출력**: List[Scenario]
**방식**: TaxCalculator로 계산

#### 시나리오 종류

1. **즉시 양도** (SC_NOW)
   - 현재 시점에서 바로 양도
   - 모든 케이스에 기본 생성

2. **지연 양도** (SC_DELAY_1Y, SC_DELAY_2Y)
   - 1년, 2년 후 양도
   - 비과세 요건 미달 시 생성

3. **증여 후 양도** (추후 추가)
   - 증여 → 양도 전략
   - Phase 2에서 구현

#### 시나리오 계산

```python
# 각 시나리오마다 TaxCalculator 실행
for scenario_config in configs:
    # 1. 미래 FactLedger 생성
    future_ledger = adjust_ledger(ledger, scenario_config)

    # 2. 세금 계산 (결정론적!)
    result = calculator.calculate(future_ledger)

    # 3. 추가 비용 계산 (로직 기반)
    additional_costs = calculate_costs(scenario_config)

    # 4. Scenario 객체 생성
    scenario = Scenario(
        expected_tax=result.calculated_tax,
        additional_costs=additional_costs,
        ...
    )
```

**특징**:
- 모든 계산은 TaxCalculator 사용 (결정론적)
- 추가 비용도 로직으로 계산 (보유세 = 시가 × 0.1%)
- LLM 사용 안 함!

---

### 3. 리스크 분석 (Risk Analysis)

**입력**: FactLedger + CaseCategory
**출력**: List[Risk]
**방식**: 규칙 기반 체크

#### 체크하는 리스크

| 리스크 ID | 조건 | 수준 |
|----------|------|------|
| RISK_HIGH_GAIN | 양도차익 > 5억 | MEDIUM |
| RISK_RESIDENCE | 실거주 기간 미확정 | HIGH |
| RISK_ADJUSTED_AREA | 조정지역 + 다주택 | HIGH |

```python
risks = []

# 리스크 1: 고액 양도차익
if capital_gain > 500_000_000:
    risks.append(Risk(
        level=RiskLevel.MEDIUM,
        title="고액 양도차익",
        description="세무 조사 대상 가능성",
        mitigation="근거 자료 철저 준비"
    ))

# 리스크 2: 실거주 미확정
if not residence_period.is_confirmed:
    risks.append(Risk(
        level=RiskLevel.HIGH,
        title="실거주 기간 미확정",
        impact="비과세 적용 불가 시 세금 발생",
        mitigation="전입세대 열람"
    ))
```

**특징**:
- 규칙 기반 체크
- 명확한 조건
- LLM 사용 안 함!

---

### 4. 추가 정보 체크 (Missing Info)

**입력**: FactLedger + CaseCategory
**출력**: List[MissingInfo]
**방식**: 필수 필드 체크

```python
missing = []

# 실거주 기간 누락?
if not ledger.residence_period_years:
    missing.append(MissingInfo(
        field_name="residence_period_years",
        description="실거주 기간",
        is_critical=True,
        how_to_obtain="전입세대 열람"
    ))
```

---

### 5. 추천 로직 (Recommendation)

**입력**: List[Scenario]
**출력**: recommended_scenario_id
**방식**: 순 편익 최대화

```python
# 순 편익 = 예상 수익 - (세금 + 추가 비용)
def net_benefit(scenario):
    gains = sum(scenario.expected_gains.values())
    costs = scenario.total_cost + sum(scenario.additional_costs.values())
    return gains - costs

# 실행 가능한 시나리오 중 순 편익 최대
best = max(
    [s for s in scenarios if s.is_feasible],
    key=net_benefit
)
```

**특징**:
- 명확한 우선순위 (순 편익 최대화)
- 로직 기반 선택
- LLM 사용 안 함!

---

## 데이터 모델

### Strategy

```python
@dataclass
class Strategy:
    """전략 (분류 + 시나리오 + 분석)"""

    # 분류
    category: CaseCategory
    classification_reasoning: str
    classification_rules_applied: List[str]

    # 시나리오
    scenarios: List[Scenario]

    # 추천
    recommended_scenario_id: str
    recommendation_reasoning: str

    # 분석
    risks: List[Risk]
    missing_info: List[MissingInfo]

    # 메타
    confidence_score: float
    rule_version: str

    # LLM 생성 (선택)
    llm_explanation: Optional[str]
    llm_additional_advice: Optional[str]
```

### Scenario

```python
@dataclass
class Scenario:
    """시나리오 (계산된 옵션)"""

    scenario_id: str
    name: str
    description: str

    # 계산 결과 (결정론적)
    expected_tax: Decimal
    expected_local_tax: Decimal
    total_cost: Decimal

    # 추가 비용/수익
    additional_costs: Dict[str, Decimal]
    expected_gains: Dict[str, Decimal]

    # 평가 (로직 기반)
    pros: List[str]
    cons: List[str]
    required_conditions: List[str]
    legal_basis: List[str]

    def net_benefit(self) -> Decimal:
        """순 편익"""
        return sum(gains) - (total_cost + sum(costs))
```

---

## 사용 예제

### 기본 사용

```python
from src.core import FactLedger
from src.agents import StrategyAgent

# 1. FactLedger 준비
ledger = FactLedger.create({
    "acquisition_date": date(2020, 1, 1),
    "acquisition_price": Decimal("500000000"),
    "disposal_date": date(2024, 11, 21),
    "disposal_price": Decimal("700000000"),
    "house_count": 1,
    "residence_period_years": 3
})

# 2. StrategyAgent 실행
agent = StrategyAgent()
strategy = await agent.analyze(ledger)

# 3. 결과 확인
print(f"분류: {strategy.category.value}")
print(f"시나리오 수: {len(strategy.scenarios)}")
print(f"추천: {strategy.recommended_scenario_id}")
```

### 시나리오 비교

```python
for scenario in strategy.scenarios:
    print(f"{scenario.name}:")
    print(f"  세금: {scenario.expected_tax:,}원")
    print(f"  순편익: {scenario.net_benefit():,}원")
```

### 리스크 확인

```python
high_risks = strategy.get_high_risks()
for risk in high_risks:
    print(f"[{risk.level}] {risk.title}")
    print(f"  완화: {risk.mitigation}")
```

### 추가 정보 체크

```python
if not strategy.is_ready_to_execute():
    missing = strategy.get_critical_missing_info()
    print("필수 정보 부족:")
    for info in missing:
        print(f"  - {info.description}")
        print(f"    취득: {info.how_to_obtain}")
```

---

## LLM 통합 (Claude 3.5 Sonnet) ✅

**Phase 2 완료**: Claude 3.5 Sonnet 통합 완료!

### 통합 방식

```python
from src.agents import StrategyAgent

# LLM 활성화 (API 키 필요)
agent = StrategyAgent(
    enable_llm=True,
    claude_api_key="your-api-key"  # 또는 환경변수 ANTHROPIC_API_KEY
)

strategy = await agent.analyze(ledger)

# LLM 생성 설명
print(strategy.llm_explanation)  # 고객용 친절한 설명
print(strategy.llm_additional_advice)  # 전문가 추가 조언
```

### 주요 특징

1. **100% 선택적**: LLM 없이도 완벽히 동작
2. **로직 우선**: 모든 분류/계산/추천은 로직이 수행
3. **설명만 생성**: LLM은 결과를 설명하는 역할만

```python
# LLM 비활성화 (기본값)
agent = StrategyAgent(enable_llm=False)
strategy = await agent.analyze(ledger)

# 로직 결과는 동일
assert strategy.category == CaseCategory.SINGLE_HOUSE_EXEMPT
assert strategy.scenarios[0].expected_tax == Decimal(0)

# 설명만 없음
assert strategy.llm_explanation is None
```

### Claude의 역할

**✅ Claude가 하는 일**:
1. **친절한 설명 생성** (`llm_explanation`)
   - 로직 결과를 일반인도 이해할 수 있게 설명
   - 전문 용어 최소화
   - 3-5문장으로 간결하게

2. **전문가 추가 조언** (`llm_additional_advice`)
   - 로직으로 발견 못한 엣지 케이스 감지
   - 세무조사 대비 팁
   - 세법 개정 고려사항
   - 유사 케이스 실수 방지

**❌ Claude가 하지 않는 일**:
- 케이스 분류 (로직이 100% 결정)
- 세금 계산 (TaxCalculator가 수행)
- 시나리오 추천 (순편익 로직이 선택)
- 사실관계 추정 (Fact Container 기반)

### 사용 예제

```python
# 1. 환경변수로 API 키 설정
import os
os.environ["ANTHROPIC_API_KEY"] = "sk-ant-..."

# 2. LLM 활성화
agent = StrategyAgent(enable_llm=True)

# 3. 분석 실행
ledger = FactLedger.create({
    "acquisition_date": date(2020, 1, 1),
    "acquisition_price": Decimal("500000000"),
    "disposal_date": date(2024, 11, 21),
    "disposal_price": Decimal("800000000"),
    "house_count": 1,
    "residence_period_years": 4
})

strategy = await agent.analyze(ledger)

# 4. 로직 결과
print(f"분류: {strategy.category.value}")  # "1주택_비과세"
print(f"세금: {strategy.scenarios[0].expected_tax:,}원")  # 0원

# 5. Claude 설명
print("\n고객용 설명:")
print(strategy.llm_explanation)
# 출력 예: "고객님의 경우 1주택 비과세 요건을 모두 충족하셨습니다.
#          2년 이상 보유하시고 실제 거주도 하셨기 때문에,
#          양도소득세가 전혀 발생하지 않습니다..."

print("\n전문가 조언:")
print(strategy.llm_additional_advice)
# 출력 예: "- 비과세 적용을 위해 전입세대 열람 원본 보관 권장
#          - 양도일로부터 2개월 이내 예정신고 기한 준수
#          - 향후 재취득 시 비과세 재적용 요건 확인 필요"
```

### 비용 추정

Claude 3.5 Sonnet 사용 비용 (2024년 11월 기준):
- Input: $3 / 1M tokens
- Output: $15 / 1M tokens

케이스당 예상 비용:
- Input: ~500 tokens (분석 결과)
- Output: ~300 tokens (설명 + 조언)
- **케이스당 약 6원**

월 1,000건 분석 시: **약 6,000원/월**

### 오류 처리

Claude API 오류가 발생해도 전체 분석은 성공합니다:

```python
strategy = await agent.analyze(ledger)

# 로직 결과는 항상 성공
assert strategy.category is not None
assert len(strategy.scenarios) > 0

# Claude 오류 시 빈 문자열
if not strategy.llm_explanation:
    print("LLM 설명 생성 실패 (로직 결과는 정상)")
```

---

## 테스트

### 분류 테스트

```python
@pytest.mark.asyncio
async def test_single_house_exempt():
    agent = StrategyAgent()

    ledger = FactLedger.create({
        "house_count": 1,
        "residence_period_years": 3,
        # 보유 4년
    })

    strategy = await agent.analyze(ledger)

    assert strategy.category == CaseCategory.SINGLE_HOUSE_EXEMPT
    assert "R020" in strategy.classification_rules_applied
```

### 시나리오 테스트

```python
@pytest.mark.asyncio
async def test_scenarios_generated():
    agent = StrategyAgent()
    strategy = await agent.analyze(ledger)

    # 최소 1개 (지금 양도)
    assert len(strategy.scenarios) >= 1

    # 첫 시나리오는 "지금"
    assert strategy.scenarios[0].scenario_id == "SC_NOW"
```

### 리스크 테스트

```python
@pytest.mark.asyncio
async def test_high_capital_gain_risk():
    # 차익 9억
    ledger = FactLedger.create({
        "capital_gain": Decimal("900000000")
    })

    strategy = await agent.analyze(ledger)

    # 고액 차익 리스크 발견
    assert any(r.risk_id == "RISK_HIGH_GAIN" for r in strategy.risks)
```

전체 테스트: [tests/test_strategy_agent.py](../tests/test_strategy_agent.py)

---

## 확장 계획

### ~~Phase 2: LLM 통합~~ ✅ 완료!
- ✅ Claude 3.5 Sonnet 통합
- ✅ 친절한 설명 생성
- ✅ 추가 조언 제시
- ⏸️ 유사 케이스 검색 (Phase 3으로 이동)

### Phase 3: 추가 시나리오
- 증여 후 양도
- 법인 전환 후 양도
- 임대 후 양도
- 1년/2년 후 양도 시나리오 확장

### Phase 4: 학습 기능
- 세무사 피드백 수집
- 규칙 자동 업데이트
- A/B 테스트
- Claude Fine-tuning (선택)

---

## 요약

**StrategyAgent = 세무사의 두뇌**

- ✅ **분류**: 100% 로직 (IF-THEN)
- ✅ **계산**: TaxCalculator (결정론적)
- ✅ **리스크**: 규칙 기반 체크
- ✅ **추천**: 순 편익 최대화
- ✅ **설명**: Claude 3.5 Sonnet (선택적)

**"LLM 없이도 완벽히 동작, LLM은 설명 보조"**

### 핵심 철학 달성 ✅

1. **사실관계 중심**: FactLedger 기반 계산 ✓
2. **결정론적 실행**: 로직이 주인공, LLM은 설명만 ✓
3. **검증 가능성**: 모든 계산 근거 추적 가능 ✓

### 구현 완료 항목

- [x] 케이스 분류 (9개 카테고리, 결정론적 규칙)
- [x] 시나리오 생성 (TaxCalculator 기반)
- [x] 리스크 분석 (규칙 기반 체크)
- [x] 추천 로직 (순 편익 최대화)
- [x] Claude 3.5 Sonnet 통합
- [x] 17개 단위 테스트 + 8개 LLM 테스트
- [x] 6개 사용 예제 + Claude 통합 예제
- [x] 완전한 문서화
