# YSZ 프로젝트 아키텍처 리뷰 (2024-11-21)

## 목차
1. [프로젝트 개요](#1-프로젝트-개요)
2. [전체 아키텍처 흐름](#2-전체-아키텍처-흐름)
3. [계산기(Calculator) 구조](#3-계산기calculator-구조)
4. [에이전트(Agent) 구조](#4-에이전트agent-구조)
5. [핵심 객체 및 데이터 구조](#5-핵심-객체-및-데이터-구조)
6. [전체 작동 흐름 예시](#6-전체-작동-흐름-예시)
7. [설계 결정 검증](#7-설계-결정-검증)
8. [다음 단계](#8-다음-단계)

---

## 1. 프로젝트 개요

**프로젝트명**: 양상증닷컴 (YSZ - YangSangJeung.com)
**목적**: 세무법인에서 사용할 양도소득세 자동 계산 프로그램 MVP

### 핵심 원칙
- **사실관계 우선 (Fact-First)**: 모든 계산은 확정된 Fact Container 위에서만 수행
- **결정론적 실행 (Deterministic Execution)**: LLM은 '계획'만 하고, 계산은 '코드'가 한다
- **검증 가능성 (Auditability)**: 모든 판단과 계산은 근거(Rule Version)와 함께 기록

---

## 2. 전체 아키텍처 흐름

### 2.1 시스템 레이어 구조

```
┌─────────────────────────────────────────────────────────────┐
│                     FRONTEND (React)                         │
│  사용자 인터페이스 (폼, 파일 업로드, 결과 표시)                 │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────v────────────────────────────────────┐
│                    FastAPI REST API                          │
│                  /api/v1/facts  (사실관계)                    │
│                  /api/v1/calculate  (세금계산)                │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────v────────────────────────────────────┐
│                  AGENT ORCHESTRATION LAYER                   │
│                  (총괄 에이전트 - Orchestrator)               │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┬──────────────┐
        │                │                │              │
        v                v                v              v
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   Agent #1   │ │   Agent #2   │ │   Agent #3   │ │   Agent #4   │
│   Asset      │ │  Calculation │ │ Verification │ │    Filing    │
│  Collector   │ │              │ │              │ │              │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │              │
       └────────────────┼────────────────┼──────────────┘
                        │
┌───────────────────────v────────────────────────────────────┐
│             CORE BUSINESS LOGIC LAYER                       │
│                                                              │
│  ┌─────────────────┐    ┌──────────────┐                   │
│  │  FactLedger     │    │ TaxCalculator│                   │
│  │  (사실관계 관리)  │    │ (세금계산 엔진)│                  │
│  └─────────────────┘    └──────┬───────┘                   │
│          │                     │                           │
│          │        ┌────────────┴────────────┐              │
│          │        │                         │              │
│          v        v                         v              │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐         │
│  │  Fact    │  │RuleEngine│  │CalculationTrace  │         │
│  │ (추적가능 │  │(세법규칙)│  │ (계산 추적)      │         │
│  │  불변값) │  │          │  │                  │         │
│  └──────────┘  └──────────┘  └──────────────────┘         │
└──────────────────────────────────────────────────────────────┘
                        │
┌───────────────────────v────────────────────────────────────┐
│             DATABASE & PERSISTENCE LAYER                    │
│  PostgreSQL + SQLAlchemy ORM                                │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. 계산기(Calculator) 구조

### 3.1 주요 파일 위치

| 파일명 | 경로 | 역할 |
|--------|------|------|
| **TaxCalculator** | `/src/core/tax_calculator.py` | 양도소득세 계산 엔진 (핵심) |
| **RuleEngine** | `/src/core/rule_engine.py` | 세법 규칙 관리 및 적용 |
| **CalculationTrace** | `/src/core/calculation_trace.py` | 계산 과정 추적 |
| **FactLedger** | `/src/core/fact_ledger.py` | 사실관계 원장 관리 |
| **Fact** | `/src/core/fact.py` | 추적 가능한 개별 사실 |

### 3.2 TaxCalculator 계산 흐름

```
사실관계 입력
    ↓
FactLedger 생성 & freeze (확정)
    ↓
양도소득 계산
양도차익 = 양도가액 - 취득가액 - (취득비용 + 처분비용 + 개선비용)
    ↓
비과세 요건 검토 (1세대 1주택)
- 기본 요건: 거주기간 2년 이상
- 보유기간 3년 이상 또는 6년 이상
- 양도가액 한도: 12억원
    ↓
장기보유특별공제 계산
- 2년 미만: 공제 없음
- 2년 이상: 보유기간에 따라 증가
- 1세대1주택: 추가 공제
    ↓
과세표준 계산
과세표준 = 양도소득 - 장기보유공제 - 기본공제(250만원)
    ↓
세율 적용
┌─ 2년 미만: 차등 비례세율
│  - 주택: 6% → 9% 등
│  - 비주택: 12% → 27% 등
│
└─ 2년 이상: 누진세율
   - 1200만원 이하: 6%
   - 4600만원 이하: 15% - 누진공제
   - 9000만원 이하: 24% - 누진공제
   - 초과: 38% ~ 45% - 누진공제
    ↓
중과세율 적용 (다주택자, 조정대상지역)
총세율 = 기본세율 + 중과세율(최대 20%p)
    ↓
세액 계산
세액 = (과세표준 × 총세율) - 누진공제액
    ↓
지방소득세 추가 (산출세액의 10%)
    ↓
최종 납부세액 = 산출세액 + 지방소득세
```

### 3.3 RuleEngine의 역할

**주요 기능**:
1. YAML 파일에서 세법 규칙 로드 (`/rules/tax_rules_2024.yaml`)
2. 누진세율 구간별 세율 제공
3. 단기보유 차등 비례세율 계산
4. 비과세 요건 검증
5. 장기보유특별공제율 계산
6. 다주택자 중과세율 적용

---

## 4. 에이전트(Agent) 구조

### 4.1 에이전트 아키텍처

```
OrchestratorAgent (총괄)
    │
    ├─ AssetCollectorAgent (Agent #1)
    │   └─ 사용자 정보 수집 및 정규화
    │
    ├─ TaxCalculationAgent (Agent #2)
    │   └─ 세액 산출 (TaxCalculator 래핑)
    │
    ├─ CalculationVerificationAgent (Agent #3)
    │   └─ 계산 검증 및 리스크 분석
    │
    └─ FilingAgent (Agent #4)
        └─ 신고서 작성 및 납부 안내
```

### 4.2 각 에이전트의 역할

#### 4.2.1 OrchestratorAgent (총괄)
- **파일**: `/src/agents/orchestrator_agent.py`
- **역할**: 전체 워크플로우 관리 및 조율
- **워크플로우**:
  ```
  Stage 1: 자산정보 수집 (AssetCollectorAgent)
      ↓
  Stage 2: 세액 산출 (TaxCalculationAgent)
      ↓
  Stage 3: 검증 (CalculationVerificationAgent)
      ↓
  Stage 4: 신고서 작성 (FilingAgent)
      ↓
  최종 품질 관리 → 종합 보고서 생성
  ```

#### 4.2.2 AssetCollectorAgent (정보 수집)
- **파일**: `/src/agents/asset_collector_agent.py`
- **역할**:
  - 다양한 소스로부터 사실관계 정보 수집
  - 자연어 처리 (LLM)
  - 문서 OCR 처리
  - 데이터 검증 및 정규화

#### 4.2.3 TaxCalculationAgent (세액 산출)
- **파일**: `/src/agents/calculation_agent.py`
- **역할**: TaxCalculator의 Wrapper
  - FactLedger 생성 및 freeze
  - TaxCalculator.calculate() 호출
  - 결과를 dict로 변환

#### 4.2.4 CalculationVerificationAgent (검증)
- **파일**: `/src/agents/verification_agent.py`
- **역할**:
  - 계산 로직 검증
  - 착오류 통계 분석
  - 유사 사례 비교
  - 리스크 플래그 식별

#### 4.2.5 FilingAgent (신고서 작성)
- **파일**: `/src/agents/filing_agent.py`
- **역할**:
  - 신고서 작성
  - 납부 안내
  - 증빙 서류 관리
  - 신고 기한 계산

---

## 5. 핵심 객체 및 데이터 구조

### 5.1 Fact 클래스 (추적 가능한 사실)

**파일**: `/src/core/fact.py`

```python
@dataclass(frozen=True)
class Fact(Generic[T]):
    """추적 가능한 불변 사실 객체"""

    value: T                          # 실제 값
    source: str                       # 출처 (user_input, api, agent_generated 등)
    confidence: float                 # 신뢰도 (0.0~1.0)
    is_confirmed: bool                # 확정 여부
    entered_by: str                   # 입력자 (사용자명, Agent ID 등)
    entered_at: datetime              # 입력 시각
    notes: Optional[str]              # 추가 메모
    reference: Optional[str]          # 근거 자료
    rule_version: Optional[str]       # 적용한 세법 규칙 버전
    reasoning_trace: Optional[str]    # AI 판단 근거
```

**특징**:
- **불변(frozen=True)**: 생성 후 수정 불가
- **제네릭**: 어떤 타입의 값도 저장 가능
- **메타데이터**: 값의 출처와 신뢰도 추적
- **확정/추정**: is_confirmed로 값의 확정 상태 관리

### 5.2 FactLedger 클래스 (사실관계 원장)

**파일**: `/src/core/fact_ledger.py`

```python
@dataclass
class FactLedger:
    """양도소득세 계산을 위한 불변 사실관계 원장"""

    # 거래 정보
    transaction_id: str
    transaction_date: Optional[Fact[date]]

    # 자산 정보
    asset_type: Optional[Fact[str]]
    acquisition_date: Optional[Fact[date]]
    acquisition_price: Optional[Fact[Decimal]]

    # 처분 정보
    disposal_date: Optional[Fact[date]]
    disposal_price: Optional[Fact[Decimal]]

    # 비용 정보
    necessary_expenses: Optional[Fact[Decimal]]

    # 거주 정보
    is_primary_residence: Optional[Fact[bool]]
    residence_period_years: Optional[Fact[int]]

    # 다주택 정보
    house_count: Optional[Fact[int]]

    # 조정대상지역
    is_adjusted_area: Optional[Fact[bool]]

    # 메타데이터
    is_frozen: bool  # 확정 여부
```

---

## 6. 전체 작동 흐름 예시

```
사용자 입력 (브라우저/API)
        ↓
OrchestratorAgent.process_case()
        ↓
Stage 1: AssetCollectorAgent.collect()
┌──────────────────────────────────────┐
│ - 직접 입력 필드 추출                │
│ - 폼 답변 파싱                      │
│ - 자연어 메시지 파싱 (LLM)          │
│ - 파일 OCR 처리                     │
│ - 외부 API 조회                     │
│ - 데이터 검증 & 정규화              │
└──────────┬───────────────────────────┘
           │
   collected_facts (dict)
           │
Stage 2: TaxCalculationAgent.calculate()
┌──────────────────────────────────────┐
│ 1. FactLedger 생성                  │
│ 2. 모든 Fact 확정 (freeze)          │
│ 3. TaxCalculator.calculate() 호출   │
│    - 양도소득 계산                  │
│    - 비과세 검토                    │
│    - 장기보유공제 적용              │
│    - 세율 계산                      │
│ 4. 결과 dict 변환                  │
└──────────┬───────────────────────────┘
           │
   tax_result (dict)
           │
Stage 3: VerificationAgent.verify()
┌──────────────────────────────────────┐
│ - 기본 논리 검증                    │
│ - 세율 적용 검증                    │
│ - 공제 한도 검증                    │
│ - 착오류 체크                       │
│ - 유사 사례 비교                    │
│ - 리스크 플래그 생성                │
└──────────┬───────────────────────────┘
           │
   verification (dict)
           │
Stage 4: FilingAgent.prepare_filing()
┌──────────────────────────────────────┐
│ - 신고서 작성                       │
│ - 신고 기한 계산                    │
│ - 납부 정보 생성                    │
│ - 필요 서류 목록 작성               │
│ - 신고 안내 생성                    │
└──────────┬───────────────────────────┘
           │
   filing_package (dict)
           │
최종 품질 관리 & 보고서 생성
           │
           ↓
최종 결과 반환 (JSON)
{
  "status": "success",
  "case_id": "C20241121",
  "collected_facts": {...},
  "tax_result": {...},
  "verification": {...},
  "filing_package": {...},
  "quality_check": {...},
  "report": "..."
}
```

---

## 7. 설계 결정 검증

### 7.1 "계산기 먼저, 에이전트 나중" - 올바른 선택 ✅

#### 이유 1: 결정론적 핵심이 우선

```
┌─────────────────────────────────────────┐
│  에이전트 (AI Layer)                     │  ← 비결정론적 (LLM)
│  - 계획만 수립                           │     나중에 추가 ✅
│  - 사용자 의도 파악                      │
└────────────┬────────────────────────────┘
             │
┌────────────v────────────────────────────┐
│  계산기 (Calculation Engine)             │  ← 결정론적 (코드)
│  - 실제 계산 수행                        │     먼저 구현 ✅
│  - 세법 규칙 적용                        │
│  - 검증 가능                            │
└─────────────────────────────────────────┘
```

#### 이유 2: 계층 분리 (Separation of Concerns)

| 계층 | 역할 | 특징 |
|------|------|------|
| **TaxCalculator** | 순수 계산 로직 | 결정론적, 테스트 가능, 독립적 검증 |
| **Agent** | LLM 기반 판단 | 비결정론적, 유연성, 사용자 인터페이스 |

#### 이유 3: 검증 가능성

- 계산기는 에이전트 없이도 단독으로 단위 테스트 가능
- 세무사가 수동 검증 가능
- 세법 변경 시 계산 로직만 수정

#### 이유 4: 에이전트의 올바른 역할

현재 에이전트는 **TaxCalculator의 래퍼**일 뿐이며, 실제 계산은 결정론적 코드가 수행:

```python
# TaxCalculationAgent - 올바른 역할
async def calculate(facts: Dict) -> Dict:
    ledger = FactLedger.create(facts)
    ledger.freeze()
    result = TaxCalculator.calculate(ledger)  # 결정론적 계산
    return result.to_dict()
```

### 7.2 만약 순서가 반대였다면?

#### ❌ 에이전트를 먼저 만들었을 때의 문제

1. **계산 로직이 LLM 안에 숨어버림**
   - 블랙박스
   - 검증 불가
   - 세법 변경 시 재학습 필요

2. **테스트 불가능**
   - LLM 출력은 확률적이므로 일관된 테스트 불가

3. **감사 불가능**
   - 세무 당국에 "LLM이 계산했어요"라고 설명 불가

---

## 8. 다음 단계

### Phase 3: 통합 고도화 (진행 중)

참조: [ai_agent_integration_spec.md](ai_agent_integration_spec.md#L282-L287)

- [ ] Fact에 `rule_version`, `reasoning_trace` 추가
- [ ] RuleVersion, RuleRegistry 구현
- [ ] AgentPlan, AgentResult 데이터 클래스 구현
- [ ] 계획-실행 분리 (Plan-Validate-Execute) 패턴 구현

### 권장 사항

1. **계산 로직은 계속 코드로 작성**
   - 세법 규칙은 YAML에 선언적으로 관리
   - 계산은 Python 코드에서 결정론적으로 수행

2. **에이전트는 "접착제" 역할에만 집중**
   - 사용자 입력 파싱 (AssetCollectorAgent)
   - 워크플로우 조율 (OrchestratorAgent)
   - 자연어 설명 생성 (FilingAgent)

3. **계획-실행 분리 패턴 구현**
   ```python
   # Planning Phase (LLM) - 비결정론적
   plan = agent.plan(context)

   # Validation Phase (Rule) - 결정론적
   validated = rule_engine.validate(plan)

   # Execution Phase (Code) - 결정론적
   result = tax_calculator.execute(validated)
   ```

---

## 결론

YSZ 프로젝트는 **사실관계 중심의 불변 데이터 구조**와 **에이전트 기반 아키텍처**를 결합한 현대적인 세무 계산 시스템입니다.

### 핵심 성공 요인

✅ **올바른 구현 순서**: 계산기(결정론적 핵심) → 에이전트(AI 래퍼)
✅ **검증 가능성**: 세무 당국 감사 통과 가능
✅ **유지보수성**: 세법 변경 시 코드만 수정
✅ **신뢰성**: LLM 없이도 계산 가능
✅ **확장성**: 에이전트 추가/제거가 자유로움

### 프로젝트의 현재 상태

- Phase 1 (기반 강화): ✅ 완료
- Phase 2 (Agent 인터페이스): ✅ 완료
- Phase 3 (통합 고도화): 🔄 진행 중
- Phase 4 (감사 & 컴플라이언스): ⏳ 예정

---

**문서 작성일**: 2024-11-21
**작성자**: Claude Code
**문서 버전**: v1.0
