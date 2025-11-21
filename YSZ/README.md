# 양상증닷컴 (YangSangJeung.com)

양도소득세 자동 계산 SaaS 프로그램

## 프로젝트 개요

세무법인에서 사용할 양도소득세 자동 계산 프로그램 MVP

## 핵심 아키텍처 원칙

1. **사실관계 중심**: 모든 계산은 확정된 사실관계(FactLedger) 기반으로 수행
2. **불변 객체**: 사실관계는 한 번 확정되면 변경 불가
3. **추적 가능성**: 모든 계산 과정과 사용된 사실관계를 완전히 기록

## 기술 스택

- **Backend**: Python 3.11 + FastAPI + SQLAlchemy
- **Database**: PostgreSQL
- **Frontend**: React (향후 추가 예정)
- **환경 관리**: Conda

## 프로젝트 구조

```
ysz/
├── docs/               # 프로젝트 문서
├── src/                # 소스 코드
│   ├── core/          # 핵심 비즈니스 로직
│   ├── api/           # FastAPI 엔드포인트
│   ├── models/        # 데이터베이스 모델
│   └── utils/         # 유틸리티 함수
├── tests/              # 테스트 코드
├── environment.yml     # Conda 환경 설정
└── requirements.txt    # Python 패키지 목록
```

## 시작하기

### 환경 설정

```bash
# 저장소 클론
git clone https://github.com/JC0623/ysz.git
cd ysz

# Conda 환경 생성 및 활성화
conda env create -f environment.yml
conda activate ysz

# 또는 pip 사용
pip install -r requirements.txt
```

### 사용 예제

```python
from datetime import date
from decimal import Decimal
from src.core import Fact, FactLedger

# 1. FactLedger 생성 (Fact 래핑 방식)
ledger = FactLedger.create({
    "acquisition_date": Fact(
        value=date(2020, 1, 1),
        source="user_input",
        is_confirmed=True,
        confidence=1.0,
        entered_by="김세무사"
    ),
    "acquisition_price": Decimal("500000000"),  # 자동으로 Fact 래핑
    "disposal_date": Fact(
        value=date(2023, 12, 31),
        is_confirmed=True,
        confidence=1.0,
        entered_by="김세무사"
    ),
    "disposal_price": Decimal("700000000")
}, created_by="김세무사")

# 2. 확정되지 않은 필드 확인
unconfirmed = ledger.get_unconfirmed_fields()
print(f"확정 필요: {unconfirmed}")

# 3. 추정값 확정
if ledger.acquisition_price and not ledger.acquisition_price.is_confirmed:
    confirmed = ledger.acquisition_price.confirm(
        confirmed_by="김세무사",
        notes="등기부등본 확인"
    )
    ledger.update_field('acquisition_price', confirmed)

# 4. 모든 필드 확정 후 freeze
ledger.freeze()
print(f"양도차익: {ledger.capital_gain:,}원")
```

### StrategyAgent 예제 (로직 기반)

```python
from datetime import date
from decimal import Decimal
from src.core import FactLedger
from src.agents import StrategyAgent

# 1. 사실관계 수집
ledger = FactLedger.create({
    "acquisition_date": date(2020, 1, 1),
    "acquisition_price": Decimal("500000000"),
    "disposal_date": date(2024, 11, 21),
    "disposal_price": Decimal("800000000"),
    "house_count": 1,
    "residence_period_years": 4
}, created_by="김세무사")

# 2. 전략 분석 (100% 결정론적!)
agent = StrategyAgent()
strategy = await agent.analyze(ledger)

# 3. 결과 확인
print(f"케이스 분류: {strategy.category.value}")
# → "1주택_비과세"

print(f"시나리오 수: {len(strategy.scenarios)}")
# → 1개 (지금_양도)

print(f"추천 시나리오: {strategy.recommended_scenario_id}")
# → "SC_NOW"

print(f"예상 세금: {strategy.scenarios[0].expected_tax:,}원")
# → 0원 (비과세)

# 4. 리스크 확인
for risk in strategy.risks:
    print(f"[{risk.level.value}] {risk.title}")

# 5. 추가 필요 정보
if not strategy.is_ready_to_execute():
    for info in strategy.get_critical_missing_info():
        print(f"필수: {info.description}")
```

### StrategyAgent + Claude 예제 (NEW! 🤖)

```python
from src.agents import StrategyAgent

# Claude 3.5 Sonnet 활성화 (API 키 필요)
agent = StrategyAgent(enable_llm=True)

# 분석 실행 (로직은 동일, 설명이 추가됨)
strategy = await agent.analyze(ledger)

# 로직 결과 (100% 동일)
print(f"케이스: {strategy.category.value}")  # 1주택_비과세
print(f"세금: {strategy.scenarios[0].expected_tax:,}원")  # 0원

# Claude가 생성한 고객용 설명
print("\n💬 고객용 설명:")
print(strategy.llm_explanation)
# → "고객님의 경우 1주택 비과세 요건을 모두 충족하셨습니다.
#    2년 이상 보유하시고 실제 거주도 하셨기 때문에,
#    양도소득세가 전혀 발생하지 않습니다..."

# Claude가 생성한 전문가 조언
print("\n👨‍💼 전문가 추가 조언:")
print(strategy.llm_additional_advice)
# → "- 비과세 적용을 위해 전입세대 열람 원본 보관 권장
#    - 양도일로부터 2개월 이내 예정신고 기한 준수
#    - 향후 재취득 시 비과세 재적용 요건 확인 필요"
```

**특징**:
- ✅ LLM 없이도 완벽히 동작 (enable_llm=False가 기본값)
- ✅ 모든 분류/계산/추천은 로직이 수행 (LLM은 설명만)
- ✅ Claude API 오류가 발생해도 분석은 성공
- 💰 비용: 케이스당 약 6원 (월 1,000건 기준 6,000원)

### 개발 현황

#### Phase 1: 핵심 기반 (완료)
- [x] 프로젝트 초기 설정
- [x] Git 저장소 구성
- [x] **Fact 클래스 구현** (추적 가능한 사실 정보)
- [x] **FactLedger 구현** (Fact 래핑, freeze 메커니즘)
- [x] **양도소득세 계산 엔진** (RuleEngine, TaxCalculator)
- [x] **계산 추적 시스템** (CalculationTrace, CalculationResult)
- [x] **세법 규칙 관리** (YAML 기반)
- [x] **테스트 코드** (43개 테스트 통과)

#### Phase 2: AI 에이전트 시스템 통합 (완료) ✅

**기반 구조**
- [x] **AI 에이전트 시스템 명세서** 작성
- [x] **Fact 클래스 강화** (rule_version, reasoning_trace 추가)
- [x] **RuleVersion & RuleRegistry** (세법 규칙 버전 관리)
- [x] **Agent Models** (AgentPlan, AgentResult, AgentExecution)
- [x] **BaseAgent & AgentProtocol** (Plan-Validate-Execute 패턴)
- [x] **통합 테스트 코드** 작성

**StrategyAgent (100% 완료) 🎯**
- [x] **케이스 분류 로직** (100% 결정론적 IF-THEN 규칙)
- [x] **시나리오 생성 엔진** (TaxCalculator 기반 계산)
- [x] **리스크 분석** (규칙 기반 체크)
- [x] **추천 로직** (순 편익 최대화)
- [x] **Claude 3.5 Sonnet 통합** (설명 생성, 추가 조언)
- [x] **테스트 & 문서** (17개 로직 테스트 + 8개 LLM 테스트, 7개 예제)

**다음 단계 (Phase 2.5)**
- [ ] Orchestrator에 StrategyAgent 통합
- [ ] VerificationAgent 구현 (로직 검증, 법규 버전 체크)
- [ ] 기존 Agent들 리팩토링

#### Phase 3: 향후 계획
- [ ] **정확한 누진세율 적용** (현재는 단순 평면 세율)
- [ ] FastAPI REST API
- [ ] PostgreSQL 연동
- [ ] React 프론트엔드

## 문서

자세한 문서는 [docs](./docs) 폴더를 참조하세요.

## 라이선스

Proprietary - 모든 권리 보유
