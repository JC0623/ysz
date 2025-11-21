# [Project 양상증] AI 에이전트 시스템 통합 명세서 (v1.0)

## 0. 시스템 개요 (System Overview)

**프로젝트명**: 양상증 (YangSangJeung) - AI Tax Engine

### 핵심 철학

1. **사실관계 우선 (Fact-First)**: 모든 계산은 확정된 Fact Container 위에서만 수행된다.
2. **결정론적 실행 (Deterministic Execution)**: LLM은 '계획'만 하고, 계산은 '코드'가 한다.
3. **검증 가능성 (Auditability)**: 모든 판단과 계산은 근거(Rule Version)와 함께 기록된다.

### 아키텍처 원칙

```
┌─────────────────────────────────────────────────────────────┐
│                     AI Agent Layer                          │
│  (Planning & Decision Making - Non-Deterministic)          │
├─────────────────────────────────────────────────────────────┤
│                  Fact Container Layer                       │
│         (Immutable Facts - Single Source of Truth)          │
├─────────────────────────────────────────────────────────────┤
│                   Execution Engine                          │
│        (Deterministic Calculation - Rule Based)             │
└─────────────────────────────────────────────────────────────┘
```

## 1. Fact Container 시스템

### 1.1 Fact 클래스 (이미 구현됨)

**목적**: 추적 가능한 사실 정보를 담는 불변 객체

**핵심 속성**:
- `value`: 실제 값 (날짜, 금액 등)
- `source`: 출처 (`user_input`, `system`, `api`, `document`, `agent_generated`)
- `confidence`: 신뢰도 (0.0~1.0)
- `is_confirmed`: 확정 여부
- `entered_by`: 입력자 (사용자 ID 또는 Agent ID)
- `entered_at`: 입력 시각
- `notes`: 추가 메모
- `reference`: 근거 자료
- **NEW**: `rule_version`: 사용된 세법 규칙 버전
- **NEW**: `reasoning_trace`: AI 판단 근거 (LLM 출력)

### 1.2 FactLedger 강화

**현재**: 기본적인 Fact 관리
**추가 필요**:
- Agent 생성 Fact 추적
- Rule Version 연결
- Reasoning Trace 저장

## 2. AI Agent 인터페이스

### 2.1 Base Agent Protocol

모든 Agent는 다음 인터페이스를 따른다:

```python
class AgentProtocol(Protocol):
    """모든 Agent가 따라야 하는 인터페이스"""

    agent_id: str
    agent_type: str  # "asset_collector", "calculator", "verifier", "filing", "orchestrator"

    async def plan(self, context: Dict[str, Any]) -> AgentPlan
    async def execute(self, plan: AgentPlan) -> AgentResult
    def get_status(self) -> AgentStatus
```

### 2.2 AgentPlan (LLM Output)

**목적**: LLM이 생성한 계획 (비결정론적)

```python
@dataclass
class AgentPlan:
    """Agent의 실행 계획"""
    plan_id: str
    agent_id: str
    created_at: datetime

    # LLM이 생성한 계획
    reasoning: str  # LLM의 사고 과정
    actions: List[PlannedAction]  # 수행할 액션 목록
    required_facts: List[str]  # 필요한 Fact 필드

    # Rule 참조
    applicable_rules: List[str]  # 적용될 세법 규칙 ID
    rule_version: str  # 규칙 버전

    # 메타데이터
    model_used: str  # "gpt-4", "claude-3-opus" etc.
    temperature: float
    confidence: float  # 계획의 신뢰도
```

### 2.3 AgentResult (Execution Output)

**목적**: Agent의 실행 결과 (결정론적)

```python
@dataclass
class AgentResult:
    """Agent의 실행 결과"""
    result_id: str
    agent_id: str
    plan_id: str
    executed_at: datetime

    # 생성된 Facts
    generated_facts: Dict[str, Fact]  # field_name -> Fact

    # 계산 결과
    calculations: Dict[str, Any]  # calculation_name -> value
    calculation_traces: List[CalculationTrace]  # 계산 추적

    # 상태
    status: str  # "success", "partial", "failed"
    errors: List[str]
    warnings: List[str]

    # 추적 정보
    execution_time_ms: int
    code_version: str  # 실행된 코드의 버전
```

## 3. Rule Version 추적 시스템

### 3.1 RuleVersion

```python
@dataclass
class RuleVersion:
    """세법 규칙 버전"""
    rule_id: str
    version: str  # "2024.1.0"
    effective_date: date  # 시행일

    # 규칙 내용
    rule_type: str  # "tax_rate", "deduction", "exemption"
    rule_data: Dict[str, Any]  # YAML에서 로드된 규칙

    # 메타데이터
    source: str  # "소득세법 제95조"
    description: str
    supersedes: Optional[str]  # 이전 버전 ID
```

### 3.2 RuleRegistry

**목적**: 세법 규칙 버전 관리

```python
class RuleRegistry:
    """세법 규칙 레지스트리"""

    def get_rule(self, rule_id: str, effective_date: date) -> RuleVersion
    def get_latest_rule(self, rule_id: str) -> RuleVersion
    def list_rules(self, rule_type: str) -> List[RuleVersion]
    def register_rule(self, rule: RuleVersion) -> None
```

## 4. Agent Orchestration

### 4.1 OrchestratorAgent 강화

**현재**: 기본적인 워크플로우 관리
**추가 필요**:

```python
class OrchestratorAgent:
    """총괄 Agent - 강화 버전"""

    async def process_case(self, user_input: Dict[str, Any]) -> CaseResult:
        """전체 케이스 처리"""

        # 1. 컨텍스트 준비
        context = self._prepare_context(user_input)

        # 2. Agent들의 계획 생성 (LLM 호출)
        plans = await self._create_plans(context)

        # 3. 계획 검증 (Rule 기반)
        validated_plans = self._validate_plans(plans)

        # 4. 계획 실행 (결정론적)
        results = await self._execute_plans(validated_plans)

        # 5. 결과 병합 & 검증
        final_result = self._merge_and_verify(results)

        return final_result
```

### 4.2 계획-실행 분리

```
┌──────────────────────────────────────────────────────────┐
│  Planning Phase (Non-Deterministic)                      │
│                                                           │
│  LLM Input: Context + Rules + Previous Facts             │
│  LLM Output: AgentPlan (reasoning + actions)             │
│                                                           │
│  → Saved for audit trail                                 │
└──────────────────────────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────────┐
│  Validation Phase (Rule-Based)                           │
│                                                           │
│  Check: Plan 합법성, Rule 적용 가능성                      │
│  Result: Validated Plan or Rejection                     │
└──────────────────────────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────────┐
│  Execution Phase (Deterministic)                         │
│                                                           │
│  Input: Validated Plan + Fact Container                  │
│  Execution: Pure Functions (no LLM)                      │
│  Output: AgentResult + New Facts                         │
│                                                           │
│  → All steps logged with Rule Version                    │
└──────────────────────────────────────────────────────────┘
```

## 5. Audit Trail

### 5.1 CaseAuditLog

```python
@dataclass
class CaseAuditLog:
    """케이스 전체 감사 로그"""
    case_id: str
    created_at: datetime

    # 입력
    user_input: Dict[str, Any]
    initial_context: Dict[str, Any]

    # Agent 실행 기록
    agent_executions: List[AgentExecution]

    # Fact 변경 이력
    fact_history: List[FactChange]

    # 최종 결과
    final_result: CaseResult

    # 버전 정보
    code_version: str
    rule_versions_used: List[str]
```

### 5.2 AgentExecution

```python
@dataclass
class AgentExecution:
    """Agent 실행 기록"""
    execution_id: str
    agent_id: str
    started_at: datetime
    completed_at: datetime

    # 계획
    plan: AgentPlan
    plan_validation: ValidationResult

    # 실행
    result: AgentResult

    # 추적
    facts_read: List[str]  # 읽은 Fact 필드
    facts_created: List[str]  # 생성한 Fact 필드
    rules_applied: List[str]  # 적용한 Rule ID
```

## 6. 구현 우선순위

### Phase 1: 기반 강화 (현재)
- [x] Fact, FactLedger 기본 구조
- [ ] Fact에 `rule_version`, `reasoning_trace` 추가
- [ ] RuleVersion, RuleRegistry 구현
- [ ] AgentPlan, AgentResult 데이터 클래스 구현

### Phase 2: Agent 인터페이스
- [ ] AgentProtocol 정의
- [ ] Base Agent 클래스 구현
- [ ] Plan-Validate-Execute 패턴 구현

### Phase 3: Orchestration
- [ ] OrchestratorAgent 강화
- [ ] 계획-실행 분리 로직
- [ ] Agent 간 데이터 전달 표준화

### Phase 4: Audit & Compliance
- [ ] CaseAuditLog 구현
- [ ] AgentExecution 추적
- [ ] 감사 보고서 생성

## 7. 예제 플로우

### 7.1 단순 케이스

```python
# 사용자 입력
user_input = {
    "acquisition_date": "2020-01-01",
    "acquisition_price": 500_000_000,
    "disposal_date": "2023-12-31",
    "disposal_price": 700_000_000,
    "is_primary_residence": True
}

# 1. Orchestrator가 컨텍스트 준비
context = orchestrator._prepare_context(user_input)

# 2. AssetCollectorAgent가 계획 생성 (LLM)
plan = await asset_collector.plan(context)
# plan.reasoning = "1세대 1주택으로 보이며, 비과세 가능성 검토 필요"
# plan.actions = [
#     PlannedAction("confirm_primary_residence", ...),
#     PlannedAction("check_holding_period", ...)
# ]

# 3. 계획 검증 (Rule 기반)
validation = rule_engine.validate_plan(plan)

# 4. 계획 실행 (결정론적)
result = await asset_collector.execute(plan)
# result.generated_facts = {
#     "is_primary_residence": Fact(
#         value=True,
#         source="agent_generated",
#         rule_version="2024.1.0",
#         reasoning_trace=plan.reasoning,
#         is_confirmed=False  # 아직 확정 안 됨
#     )
# }

# 5. Fact Container 업데이트
fact_ledger.update_from_agent_result(result)
```

## 8. 보안 및 제약사항

### 8.1 LLM 권한 제한
- LLM은 **계획만** 생성 (실행 안 함)
- LLM은 Fact를 **제안만** (강제 확정 안 함)
- LLM 출력은 항상 **Rule 검증** 통과 필요

### 8.2 Fact 무결성
- Fact는 **불변 객체**
- 수정 시 항상 **새 버전** 생성
- 모든 변경은 **감사 로그** 기록

### 8.3 Rule 버전 고정
- 케이스 처리 시작 시 **Rule 버전 스냅샷**
- 처리 중 Rule 변경 **불가**
- 모든 계산에 **Rule Version 태깅**

## 9. 다음 단계

1. [src/core/fact.py](../src/core/fact.py) 에 `rule_version`, `reasoning_trace` 필드 추가
2. [src/core/rule_version.py](../src/core/rule_version.py) 생성
3. [src/agents/base_agent.py](../src/agents/base_agent.py) 생성
4. [src/agents/orchestrator_agent.py](../src/agents/orchestrator_agent.py) 강화
5. 테스트 케이스 작성

---

**문서 버전**: v1.0
**작성일**: 2025-11-21
**다음 리뷰**: Phase 1 완료 후
