# YSZ AI 에이전트 아키텍처 (v2.0)

## Phase 2 완료: StrategyAgent 중심 설계

---

## 📋 목차
1. [전체 구조](#전체-구조)
2. [Phase 2 핵심 완료 사항](#phase-2-핵심-완료-사항)
3. [StrategyAgent (핵심 뇌)](#strategyagent-핵심-뇌)
4. [VerificationAgent (검증)](#verificationagent-검증)
5. [기타 에이전트 (향후)](#기타-에이전트-향후)
6. [구현 로드맵](#구현-로드맵)

---

## 전체 구조

```
사용자 입력 (자연어/문서/API)
           ↓
    ┌──────────────────┐
    │  Orchestrator    │ ← 워크플로우 조율
    └──────────────────┘
           ↓
    ┌─────┴─────┬─────┐
    ↓           ↓     ↓
┌────────┐ ┌────────┐ ┌────────┐
│Strategy│ │Verify  │ │Filing  │
│Agent   │ │Agent   │ │Agent   │
│(핵심뇌)│ │(검증)  │ │(신고)  │
└────────┘ └────────┘ └────────┘
    │
    └──────────┘
           ↓
   최종 신고/보고서
```

---

## Phase 2 핵심 완료 사항

### ✅ StrategyAgent (100% 완료)

**파일 위치**: `src/agents/strategy_agent.py`

**역할**: 양도소득세 케이스 분류 및 전략 수립 (프로젝트의 "뇌")

#### 핵심 기능

1. **케이스 분류 (100% 결정론적 IF-THEN 규칙)**
   ```python
   CaseCategory.SINGLE_HOUSE_EXEMPT    # 1주택 비과세
   CaseCategory.SINGLE_HOUSE_TAXABLE   # 1주택 과세
   CaseCategory.MULTI_HOUSE_GENERAL    # 다주택 일반
   CaseCategory.MULTI_HOUSE_HEAVY      # 다주택 중과
   CaseCategory.ADJUSTED_AREA_HEAVY    # 조정지역 중과
   CaseCategory.CORPORATE              # 법인
   CaseCategory.INHERITANCE            # 상속
   CaseCategory.COMPLEX                # 복잡 케이스
   CaseCategory.OTHER                  # 기타
   ```

2. **시나리오 생성 (TaxCalculator 기반)**
   - 지금 양도 시나리오
   - 2년 보유 후 양도 시나리오
   - 비용 최적화 시나리오
   - 각 시나리오별 예상 세금, 총 비용, 순 편익 계산

3. **리스크 분석 (규칙 기반)**
   - 높은 세금 부담 (1억 이상)
   - 1주택 비과세 요건 미충족
   - 조정지역 중과세 리스크
   - 12억 초과 부분과세
   - 보유기간 부족 (2년 미만)

4. **추천 로직 (순 편익 최대화)**
   - 실행 가능한 시나리오 중 순 편익이 가장 큰 시나리오 선택
   - 신뢰도 점수 계산 (데이터 완정성 기반)

5. **Claude 3.5 Sonnet 통합 (선택적)**
   - 고객용 친화적 설명 생성
   - 전문가 추가 조언 제공
   - **중요**: LLM은 설명만! 분류/계산/추천은 100% 로직

#### 사용 예제

```python
from src.agents import StrategyAgent
from src.core import FactLedger
from datetime import date
from decimal import Decimal

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
agent = StrategyAgent(enable_llm=False)  # LLM 없이도 완벽 작동
strategy = await agent.analyze(ledger)

# 3. 결과 확인
print(f"케이스 분류: {strategy.category.value}")  # "1주택_비과세"
print(f"시나리오 수: {len(strategy.scenarios)}")  # 1개 (지금_양도)
print(f"추천 시나리오: {strategy.recommended_scenario_id}")  # "SC_NOW"
print(f"예상 세금: {strategy.scenarios[0].expected_tax:,}원")  # 0원 (비과세)

# 4. Claude 통합 (선택적)
agent_with_llm = StrategyAgent(enable_llm=True)
strategy_with_llm = await agent_with_llm.analyze(ledger)
print(strategy_with_llm.llm_explanation)  # 고객용 친화적 설명
print(strategy_with_llm.llm_additional_advice)  # 전문가 조언
```

#### 테스트 현황

- ✅ 17개 로직 테스트 (`tests/test_strategy_agent.py`)
- ✅ 8개 LLM 통합 테스트 (`tests/test_strategy_agent_claude.py`)
- ✅ 7개 예제 코드 (`examples/strategy_agent_*.py`)

---

## StrategyAgent (핵심 뇌)

### 역할 정의

StrategyAgent는 **세무사의 두뇌를 대신하는 핵심 에이전트**입니다.

#### 세무사가 하는 일
1. 고객 사례를 듣고 → **케이스 분류**
2. 여러 시나리오를 만들고 → **시나리오 생성**
3. 각 옵션의 장단점 분석 → **리스크 분석**
4. 고객에게 최선의 방법 추천 → **추천**

#### StrategyAgent가 하는 일
위 모든 과정을 **100% 로직 기반**으로 자동화!

### 아키텍처 원칙

```
┌─────────────────────────────────────────────────────────┐
│  StrategyAgent (전략 수립 - 핵심 뇌)                     │
│                                                          │
│  입력: FactLedger (확정된 사실관계)                      │
│  처리: 100% 결정론적 IF-THEN 규칙                        │
│  출력: Strategy (케이스분류 + 시나리오 + 추천)           │
│                                                          │
│  LLM 역할: 설명 생성만! (enable_llm=True 시)            │
└─────────────────────────────────────────────────────────┘
```

### 핵심 철학

1. **사실관계 우선 (Fact-First)**: 모든 분석은 확정된 FactLedger 기반
2. **결정론적 실행 (Deterministic Logic)**: LLM은 설명만, 분류/계산은 코드
3. **검증 가능성 (Auditability)**: 모든 판단은 Rule Version과 함께 기록

---

## VerificationAgent (검증)

### Phase 2.5에서 구현 예정

**역할**: 로직 검증, 법규 버전 체크, 분쟁 대비

#### 구현 계획

```python
class VerificationAgent:
    """검증 에이전트 (Phase 2.5)

    역할:
    1. 로직 검증: StrategyAgent의 분류가 올바른지
    2. 세법 버전 체크: 최신 세율/공제율 적용 확인
    3. 분쟁 대비: 국세청 소명자료 준비

    LLM 사용: 없음 (순수 규칙 기반 검증)
    """

    async def verify(self, strategy: Strategy, ledger: FactLedger):
        issues = []

        # 1. 분류 검증
        expected_category = self._recalculate_category(ledger)
        if expected_category != strategy.category:
            issues.append({
                "level": "ERROR",
                "message": f"케이스 분류 불일치"
            })

        # 2. 세법 버전 체크
        if not self._is_latest_rule_version():
            issues.append({
                "level": "WARNING",
                "message": "세법 규칙 업데이트 필요"
            })

        # 3. 리스크 검증
        for risk in strategy.risks:
            if risk.level == RiskLevel.HIGH:
                issues.append({
                    "level": "INFO",
                    "message": f"고위험 항목: {risk.title}"
                })

        return {
            "status": "PASS" if not any(i["level"] == "ERROR" for i in issues) else "FAIL",
            "issues": issues
        }
```

---

## 기타 에이전트 (향후)

### AssetCollectorAgent (Phase 3)
- 문서 OCR 처리
- 외부 API 조회 (국토부 실거래가 등)
- 자연어 입력 파싱

### FilingAgent (Phase 3)
- 신고서 작성
- 납부 안내
- 증빙 서류 관리

### OrchestratorAgent (Phase 2.5)
- StrategyAgent 통합
- VerificationAgent 통합
- 전체 워크플로우 조율

---

## 구현 로드맵

### ✅ Phase 1: 핵심 기반 (완료)
- [x] Fact 클래스 구현
- [x] FactLedger 구현
- [x] TaxCalculator (양도소득세 계산 엔진)
- [x] RuleEngine (세법 규칙 관리)

### ✅ Phase 2: AI 에이전트 시스템 통합 (완료)
- [x] Fact 클래스 강화 (rule_version, reasoning_trace)
- [x] RuleVersion & RuleRegistry
- [x] Agent Models (AgentPlan, AgentResult, AgentExecution)
- [x] BaseAgent & AgentProtocol
- [x] **StrategyAgent (100% 완료)**
  - [x] 케이스 분류 로직
  - [x] 시나리오 생성 엔진
  - [x] 리스크 분석
  - [x] 추천 로직
  - [x] Claude 3.5 Sonnet 통합
  - [x] 테스트 & 문서 (17+8 테스트, 7 예제)

### 🔄 Phase 2.5: Orchestrator & Verification (진행 예정)
- [ ] Orchestrator에 StrategyAgent 통합
- [ ] VerificationAgent 구현
  - [ ] 로직 검증
  - [ ] 세법 버전 체크
  - [ ] 분쟁 대비 자료 준비
- [ ] 기존 Agent들 리팩토링

### 📅 Phase 3: 정보 수집 & 신고 (향후)
- [ ] AssetCollectorAgent
  - [ ] OCR 통합 (Tesseract/Google Vision)
  - [ ] API 연동 (국토부 실거래가)
  - [ ] 자연어 처리
- [ ] FilingAgent
  - [ ] 신고서 양식 생성
  - [ ] 납부 안내 자동화

---

## 기술 스택

### 1. LLM (Large Language Model)
```python
# Claude 3.5 Sonnet (StrategyAgent 설명 생성용)
from anthropic import Anthropic
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
```

### 2. 에이전트 프레임워크
```python
# BaseAgent (자체 구현)
from src.agents.base_agent import BaseAgent

# LangChain/LangGraph (향후 고려)
from langchain.agents import AgentExecutor
from langgraph.graph import StateGraph
```

### 3. 데이터베이스
```python
# PostgreSQL - 메인 DB
from sqlalchemy import create_engine
engine = create_engine("postgresql://user:pass@localhost/ysz")
```

---

## 예상 성능

### 처리 속도
- **케이스 분류**: <1초 (100% 로직)
- **시나리오 생성**: 2-5초 (TaxCalculator 호출)
- **전체 프로세스**: 5-10초 (LLM 설명 포함)

### 정확도 목표
- **케이스 분류**: 100% (결정론적 규칙)
- **세액 계산**: 99.5% 이상 (TaxCalculator)
- **리스크 탐지**: 95% 이상

---

## 현재 구현 통계 (Phase 2 완료)

### 신규 파일
- `src/core/rule_version.py` (RuleVersion, RuleRegistry)
- `src/agents/agent_models.py` (AgentPlan, AgentResult, AgentExecution)
- `src/agents/base_agent.py` (BaseAgent, AgentProtocol)
- `src/agents/strategy_agent.py` (StrategyAgent - 핵심!)
- `src/agents/strategy_models.py` (CaseCategory, Strategy, Scenario, Risk)

### 테스트
- `tests/test_agent_integration.py` (통합 테스트)
- `tests/test_strategy_agent.py` (17개 로직 테스트)
- `tests/test_strategy_agent_claude.py` (8개 LLM 테스트)

### 예제
- `examples/ai_agent_example.py`
- `examples/strategy_agent_example.py` (6개 시나리오)
- `examples/strategy_agent_claude_example.py` (4개 시나리오)

### 문서
- `docs/ai_agent_integration_spec.md`
- `docs/implementation_summary.md` (Phase 2 상세)
- `docs/strategy_agent.md` (StrategyAgent 완전 가이드)
- `docs/agent_architecture.md` (본 문서)

---

## 참고 자료

### 프레임워크 문서
- **Anthropic Claude**: https://docs.anthropic.com/
- **LangChain**: https://python.langchain.com/
- **LangGraph**: https://github.com/langchain-ai/langgraph

### API
- **국토교통부 실거래가**: https://www.data.go.kr/
- **홈택스 API**: https://www.hometax.go.kr/

---

**문서 버전**: v2.0 (Phase 2 완료 반영)
**최종 업데이트**: 2025-11-22
**다음 리뷰**: Phase 2.5 완료 후
