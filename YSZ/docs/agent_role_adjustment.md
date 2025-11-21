# Agent 역할 조정 계획

## 목표 시나리오 vs 현재 구현 비교

### MVP 목표 (5개 Agent, AI는 1개만)

```
┌─────────────────────────────────────────────────────────┐
│  1. Collector (수집가)  🤖 순수 Python                  │
│     - API 호출, 입력값 받기, OCR                         │
│     - AI 필요 없음                                       │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│  2. Triage (분류자)  🤖 IF문                            │
│     - IF 주택수 == 1 THEN 계속                          │
│     - ELSE 중단 (MVP 범위 밖)                            │
│     - AI 필요 없음 (단순 조건문)                         │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│  3. Calculator (계산기)  🤖 Python 수식                 │
│     - 100% 결정론적 계산                                │
│     - 절대 AI 쓰면 안 됨                                │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│  4. Auditor (감사관)  🧠 LLM (유일한 AI)                │
│     - "이 데이터랑 결과 보고 이상한 점 찾아줘"           │
│     - 여기만 LLM 사용                                    │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│  5. CEO (총괄)  🔗 LangGraph                            │
│     - 1 → 2 → 3 → 4 순서대로 실행                       │
│     - 단순 연결자                                        │
└─────────────────────────────────────────────────────────┘
```

---

## 현재 구현 (6개 Agent)

```
현재:
1. AssetCollectorAgent (수집) ✅ 맞음
2. (없음) ❌ Triage 누락!
3. TaxCalculationAgent (계산) ✅ 맞음
4. CalculationVerificationAgent (검증) ⚠️ LLM 추가 필요
5. FilingAgent (신고서) ⚠️ MVP 필요 없음?
6. TaxAdvisorAgent (상담) ⚠️ MVP 필요 없음?
7. OrchestratorAgent (총괄) ✅ 맞음
```

---

## 조정 계획

### Phase 1: Triage Agent 추가 (필수)

**새 파일**: `src/agents/triage_agent.py`

```python
class TriageAgent:
    """분류 에이전트 (MVP: 1주택자만 처리)

    역할:
    - 주택 수 확인
    - 1주택자 → 진행
    - 다주택자 → 중단 (MVP 범위 밖)

    AI 사용: 없음 (순수 IF문)
    """

    async def triage(self, facts: Dict[str, Any]) -> Dict[str, Any]:
        house_count = facts.get('house_count', 0)

        if house_count == 1:
            return {
                "status": "proceed",
                "category": "single_house",
                "message": "1세대 1주택 - 계산 진행"
            }
        else:
            return {
                "status": "out_of_scope",
                "category": "multiple_houses",
                "message": f"다주택자({house_count}채) - MVP 범위 밖"
            }
```

### Phase 2: Verification Agent에 LLM 추가

**현재**: 순수 코드 검증만
**목표**: LLM으로 "이상한 점" 탐지

```python
class CalculationVerificationAgent:

    async def verify_with_llm(self, facts, tax_result):
        """LLM으로 이상 징후 탐지"""

        prompt = f"""
        다음 양도소득세 계산 결과를 검토해주세요.

        입력 데이터:
        - 취득가액: {facts['acquisition_price']:,}원
        - 양도가액: {facts['disposal_price']:,}원
        - 보유기간: {facts.get('holding_years', 0)}년

        계산 결과:
        - 양도차익: {tax_result['capital_gain']:,}원
        - 세액: {tax_result['total_tax']:,}원

        이상한 점이나 주의할 점을 찾아주세요.
        """

        # LLM 호출
        response = await self.llm.chat(prompt)
        return response
```

### Phase 3: Orchestrator를 LangGraph로 (선택)

**현재**: 단순 async 함수 체인
**목표**: LangGraph로 구조화 (향후 확장성)

```python
from langgraph.graph import Graph, StateGraph

def create_tax_workflow():
    """LangGraph로 워크플로우 정의"""

    workflow = StateGraph(dict)

    # 노드 추가
    workflow.add_node("collect", collector.collect)
    workflow.add_node("triage", triage.triage)
    workflow.add_node("calculate", calculator.calculate)
    workflow.add_node("audit", auditor.verify_with_llm)

    # 엣지 정의
    workflow.add_edge("collect", "triage")
    workflow.add_conditional_edges(
        "triage",
        lambda x: "calculate" if x["status"] == "proceed" else "end"
    )
    workflow.add_edge("calculate", "audit")
    workflow.add_edge("audit", "end")

    return workflow.compile()
```

---

## 최종 MVP 구조 (권장)

### 5개 Agent, AI는 1개만

| # | Agent | 구현 방식 | AI 사용 | 현재 상태 |
|---|-------|----------|---------|----------|
| 1 | **Collector** | Python 코드 | ❌ | ✅ 완료 |
| 2 | **Triage** | IF문 | ❌ | ❌ 추가 필요 |
| 3 | **Calculator** | Python 수식 | ❌ | ✅ 완료 |
| 4 | **Auditor** | LLM 호출 | ✅ | ⚠️ LLM 추가 |
| 5 | **CEO** | LangGraph | ❌ | ⚠️ 단순화 |

### FilingAgent, TaxAdvisorAgent는?

**권장**: MVP에서 제외하거나 Phase 2로 연기
- **FilingAgent**: 신고서 작성은 계산 후 단계
- **TaxAdvisorAgent**: 상담은 부가 기능

MVP는 "계산만" 확실하게!

---

## 실행 계획

### Step 1: Triage Agent 추가 (30분)
```bash
src/agents/triage_agent.py
tests/test_triage_agent.py
```

### Step 2: Verification에 LLM 추가 (1시간)
```python
# verification_agent.py에 추가
async def verify_with_llm(self, ...):
    # LLM 호출 로직
```

### Step 3: Orchestrator 단순화 (1시간)
```python
# orchestrator_agent.py 수정
async def run_mvp_workflow(self, user_input):
    # 1. Collect
    facts = await self.collector.collect(user_input)

    # 2. Triage (신규!)
    triage_result = await self.triage.triage(facts)
    if triage_result['status'] != 'proceed':
        return {"error": "MVP 범위 밖"}

    # 3. Calculate
    tax_result = await self.calculator.calculate(facts)

    # 4. Audit (LLM 사용!)
    audit_result = await self.auditor.verify_with_llm(facts, tax_result)

    return {
        "facts": facts,
        "tax_result": tax_result,
        "audit": audit_result
    }
```

### Step 4: LangGraph 전환 (선택, 2시간)
- 기존 async 체인을 LangGraph로 변환
- 향후 복잡한 분기 대비

---

## 기존 BaseAgent 프레임워크는?

**유지합니다!** 왜냐하면:

1. **Plan-Validate-Execute 패턴** → 좋은 구조
2. **Fact-First 원칙** → 핵심 철학
3. **Rule Version 추적** → 감사 필수

다만, MVP에서는:
- Collector, Triage, Calculator → 단순 Python (BaseAgent 안 써도 됨)
- Auditor → LLM 사용 시 BaseAgent 활용
- 향후 확장 시 BaseAgent로 리팩토링

**결론**: BaseAgent는 "나중을 위한 좋은 준비"이므로 그대로 두되, MVP는 단순하게!

---

## 요약

### ✅ 유지
- AssetCollectorAgent (순수 코드)
- TaxCalculationAgent (100% 결정론적)
- OrchestratorAgent (연결자)
- BaseAgent 프레임워크 (향후 확장용)

### ➕ 추가
- **TriageAgent** (IF문으로 1주택자 필터링)

### 🔄 변경
- **VerificationAgent**: LLM 추가 (유일한 AI 사용처)

### ⏸️ 보류 (MVP 후)
- FilingAgent
- TaxAdvisorAgent
- LangGraph 전환 (선택)

---

**다음 액션**: TriageAgent 먼저 추가할까요?
