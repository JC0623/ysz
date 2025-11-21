# ChatAgent 명세서 (v1.0)

## 개요

**목적**: 사용자가 자연어로 양도소득세 관련 질문을 하면 AI가 답변하는 대화형 인터페이스

**위치**: 프론트엔드에 채팅 UI 추가, 백엔드에 ChatAgent 구현

---

## 1. 시스템 아키텍처

### 1.1 전체 흐름

```
사용자 메시지 입력
    ↓
[Frontend] ChatComponent.tsx
    ↓ POST /api/v1/chat/message
[Backend] ChatRouter
    ↓
[Agent] ChatAgent
    ├─ 1. 의도 파악 (Intent Classification)
    │   ├─ 일반 질문 (세법 설명)
    │   ├─ 계산 요청 (세액 산출)
    │   ├─ 전략 상담 (시나리오 비교)
    │   └─ 사실관계 확인
    │
    ├─ 2. 필요한 Agent 호출
    │   ├─ StrategyAgent (시나리오 분석)
    │   ├─ TaxCalculator (세액 계산)
    │   └─ FactLedger (사실관계 조회)
    │
    └─ 3. 자연어 응답 생성 (LLM)
        └─ Claude 3.5 Sonnet
    ↓
응답 반환 (텍스트 or 스트리밍)
    ↓
[Frontend] 메시지 표시
```

### 1.2 대화 컨텍스트 관리

```python
@dataclass
class ChatContext:
    """대화 컨텍스트"""
    session_id: str
    user_id: str

    # 대화 이력
    messages: List[ChatMessage]

    # 현재 사실관계
    current_ledger: Optional[FactLedger]

    # 마지막 계산 결과
    last_calculation: Optional[CalculationResult]

    # 마지막 전략 분석
    last_strategy: Optional[StrategyResult]

    # 메타데이터
    created_at: datetime
    updated_at: datetime
```

---

## 2. 백엔드 구현

### 2.1 ChatAgent 클래스

**파일**: `src/agents/chat_agent.py`

```python
from typing import Dict, Any, AsyncGenerator
from src.agents.base_agent import BaseAgent
from src.agents.strategy_agent import StrategyAgent
from src.core.tax_calculator import TaxCalculator
from src.core.fact_ledger import FactLedger

class ChatAgent(BaseAgent):
    """대화형 AI 세무 상담 에이전트"""

    def __init__(
        self,
        llm_client: Any,  # Claude API 클라이언트
        strategy_agent: StrategyAgent,
        enable_streaming: bool = False
    ):
        super().__init__(
            agent_id="chat_001",
            agent_type="chat"
        )
        self.llm = llm_client
        self.strategy_agent = strategy_agent
        self.enable_streaming = enable_streaming

        # 대화 컨텍스트 저장소 (실제로는 Redis/DB)
        self.contexts: Dict[str, ChatContext] = {}

    async def chat(
        self,
        message: str,
        session_id: str,
        context: Optional[ChatContext] = None
    ) -> ChatResponse:
        """
        사용자 메시지에 응답

        Args:
            message: 사용자 메시지
            session_id: 세션 ID
            context: 대화 컨텍스트 (옵션)

        Returns:
            ChatResponse: 응답 메시지 및 메타데이터
        """
        # 1. 컨텍스트 로드 또는 생성
        ctx = context or self._get_or_create_context(session_id)

        # 2. 사용자 메시지 추가
        ctx.messages.append(ChatMessage(
            role="user",
            content=message,
            timestamp=datetime.now()
        ))

        # 3. 의도 파악
        intent = await self._classify_intent(message, ctx)

        # 4. 의도별 처리
        if intent.type == "general_question":
            response = await self._handle_general_question(message, ctx)

        elif intent.type == "calculation_request":
            response = await self._handle_calculation(message, ctx)

        elif intent.type == "strategy_consultation":
            response = await self._handle_strategy(message, ctx)

        elif intent.type == "fact_inquiry":
            response = await self._handle_fact_inquiry(message, ctx)

        else:
            response = await self._handle_unknown(message, ctx)

        # 5. 응답 메시지 추가
        ctx.messages.append(ChatMessage(
            role="assistant",
            content=response.content,
            timestamp=datetime.now(),
            metadata=response.metadata
        ))

        # 6. 컨텍스트 저장
        self._save_context(ctx)

        return response

    async def _classify_intent(
        self,
        message: str,
        context: ChatContext
    ) -> Intent:
        """
        사용자 의도 파악 (LLM 사용)

        Returns:
            Intent: 의도 분류 결과
        """
        prompt = f"""
다음 사용자 메시지의 의도를 파악하세요.

사용자 메시지: "{message}"

대화 이력:
{self._format_history(context.messages[-5:])}

의도 유형:
1. general_question: 일반적인 세법 설명 질문
2. calculation_request: 세금 계산 요청
3. strategy_consultation: 전략 상담 (언제 팔지, 시나리오 비교)
4. fact_inquiry: 사실관계 확인/수정 요청

응답 형식 (JSON):
{{
  "type": "의도_유형",
  "confidence": 0.95,
  "reasoning": "판단 근거"
}}
"""

        response = await self.llm.generate(prompt)
        return Intent.from_json(response)

    async def _handle_calculation(
        self,
        message: str,
        context: ChatContext
    ) -> ChatResponse:
        """
        세금 계산 요청 처리

        1. 현재 FactLedger 확인
        2. 부족한 정보 확인
        3. TaxCalculator 실행
        4. 결과를 자연어로 설명
        """
        if not context.current_ledger:
            return ChatResponse(
                content="세금 계산을 위해 먼저 몇 가지 정보가 필요합니다.\n\n"
                       "1. 언제 집을 구입하셨나요? (취득일)\n"
                       "2. 얼마에 구입하셨나요? (취득가액)\n"
                       "3. 언제 팔 예정이신가요? (양도일)\n"
                       "4. 얼마에 팔 예정이신가요? (양도가액)\n\n"
                       "이 정보를 알려주시면 세금을 계산해드리겠습니다.",
                intent_type="calculation_request",
                requires_info=True
            )

        # 계산 실행
        ledger = context.current_ledger
        result = TaxCalculator.calculate(ledger)

        # 결과를 자연어로 변환 (LLM)
        explanation = await self._explain_calculation(result, ledger)

        # 컨텍스트에 저장
        context.last_calculation = result

        return ChatResponse(
            content=explanation,
            intent_type="calculation_request",
            metadata={
                "calculation_result": result.to_dict(),
                "total_tax": float(result.total_tax)
            }
        )

    async def _handle_strategy(
        self,
        message: str,
        context: ChatContext
    ) -> ChatResponse:
        """
        전략 상담 처리

        1. StrategyAgent 실행
        2. 시나리오 비교
        3. 추천 제시
        """
        if not context.current_ledger:
            return ChatResponse(
                content="전략 상담을 위해 먼저 정보를 입력해주세요.",
                intent_type="strategy_consultation",
                requires_info=True
            )

        # StrategyAgent 실행
        ledger = context.current_ledger
        strategy = await self.strategy_agent.analyze(ledger)

        # LLM 설명 (이미 strategy.llm_explanation에 포함)
        content = strategy.llm_explanation or self._format_strategy(strategy)

        # 컨텍스트에 저장
        context.last_strategy = strategy

        return ChatResponse(
            content=content,
            intent_type="strategy_consultation",
            metadata={
                "category": strategy.category,
                "recommended_scenario": strategy.recommended_scenario_id,
                "scenarios": [s.to_dict() for s in strategy.scenarios]
            }
        )

    async def _explain_calculation(
        self,
        result: CalculationResult,
        ledger: FactLedger
    ) -> str:
        """
        계산 결과를 자연어로 설명 (LLM)
        """
        prompt = f"""
다음 양도소득세 계산 결과를 일반인이 이해하기 쉽게 설명하세요.

사실관계:
- 취득일: {ledger.acquisition_date.value}
- 취득가액: {ledger.acquisition_price.value:,}원
- 양도일: {ledger.disposal_date.value}
- 양도가액: {ledger.disposal_price.value:,}원

계산 결과:
- 양도차익: {result.capital_gain:,}원
- 장기보유공제: {result.long_term_deduction:,}원
- 과세표준: {result.taxable_income:,}원
- 산출세액: {result.calculated_tax:,}원
- 지방소득세: {result.local_tax:,}원
- 총 납부세액: {result.total_tax:,}원
- 적용 세율: {result.applied_tax_rate * 100:.1f}%

요구사항:
1. 친근하고 이해하기 쉬운 언어 사용
2. 중요한 숫자는 천단위 쉼표 포함
3. 왜 이런 세금이 나왔는지 간단히 설명
4. 3-4 문단으로 구성

응답:
"""

        explanation = await self.llm.generate(prompt)
        return explanation
```

### 2.2 API 라우터

**파일**: `src/api/routers/chat.py`

```python
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from src.agents.chat_agent import ChatAgent

router = APIRouter(prefix="/chat", tags=["chat"])

# 전역 ChatAgent 인스턴스 (실제로는 Dependency Injection)
chat_agent: Optional[ChatAgent] = None

def get_chat_agent() -> ChatAgent:
    global chat_agent
    if chat_agent is None:
        raise HTTPException(status_code=500, detail="ChatAgent not initialized")
    return chat_agent


class ChatMessageRequest(BaseModel):
    """채팅 메시지 요청"""
    message: str
    session_id: str
    user_id: Optional[str] = "anonymous"
    transaction_id: Optional[int] = None  # 기존 거래 연결


class ChatMessageResponse(BaseModel):
    """채팅 메시지 응답"""
    content: str
    intent_type: str
    requires_info: bool = False
    metadata: Optional[dict] = None
    session_id: str
    timestamp: str


@router.post("/message", response_model=ChatMessageResponse)
async def send_message(
    request: ChatMessageRequest,
    agent: ChatAgent = Depends(get_chat_agent)
):
    """
    사용자 메시지 전송 및 AI 응답 받기

    Args:
        request: 메시지 요청

    Returns:
        ChatMessageResponse: AI 응답
    """
    try:
        # 기존 거래 ID가 있으면 컨텍스트에 로드
        context = None
        if request.transaction_id:
            context = await agent.load_context_from_transaction(
                request.session_id,
                request.transaction_id
            )

        # ChatAgent 실행
        response = await agent.chat(
            message=request.message,
            session_id=request.session_id,
            context=context
        )

        return ChatMessageResponse(
            content=response.content,
            intent_type=response.intent_type,
            requires_info=response.requires_info,
            metadata=response.metadata,
            session_id=request.session_id,
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{session_id}")
async def get_chat_history(
    session_id: str,
    agent: ChatAgent = Depends(get_chat_agent)
):
    """
    대화 이력 조회

    Args:
        session_id: 세션 ID

    Returns:
        List[ChatMessage]: 대화 이력
    """
    context = agent.get_context(session_id)
    if not context:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session_id,
        "messages": [msg.to_dict() for msg in context.messages],
        "created_at": context.created_at.isoformat()
    }


@router.delete("/session/{session_id}")
async def clear_session(
    session_id: str,
    agent: ChatAgent = Depends(get_chat_agent)
):
    """
    세션 삭제

    Args:
        session_id: 세션 ID

    Returns:
        dict: 성공 메시지
    """
    agent.delete_context(session_id)
    return {"message": "Session cleared", "session_id": session_id}
```

---

## 3. 프론트엔드 구현

### 3.1 ChatComponent.tsx

**파일**: `frontend/src/components/ChatComponent.tsx`

```tsx
import React, { useState, useEffect, useRef } from 'react';
import { Input, Button, Card, List, Avatar, Spin, Tag } from 'antd';
import { SendOutlined, RobotOutlined, UserOutlined } from '@ant-design/icons';
import axios from 'axios';

const { TextArea } = Input;

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  metadata?: any;
}

interface ChatComponentProps {
  sessionId: string;
  transactionId?: number;
}

const ChatComponent: React.FC<ChatComponentProps> = ({ sessionId, transactionId }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 자동 스크롤
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // 대화 이력 로드
  useEffect(() => {
    loadChatHistory();
  }, [sessionId]);

  const loadChatHistory = async () => {
    try {
      const response = await axios.get(`/api/v1/chat/history/${sessionId}`);
      setMessages(response.data.messages);
    } catch (error) {
      console.error('Failed to load chat history:', error);
    }
  };

  const sendMessage = async () => {
    if (!inputValue.trim()) return;

    const userMessage: ChatMessage = {
      role: 'user',
      content: inputValue,
      timestamp: new Date().toISOString(),
    };

    // 사용자 메시지 즉시 표시
    setMessages([...messages, userMessage]);
    setInputValue('');
    setLoading(true);

    try {
      const response = await axios.post('/api/v1/chat/message', {
        message: inputValue,
        session_id: sessionId,
        transaction_id: transactionId,
      });

      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: response.data.content,
        timestamp: response.data.timestamp,
        metadata: response.data.metadata,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Failed to send message:', error);

      // 에러 메시지 표시
      const errorMessage: ChatMessage = {
        role: 'assistant',
        content: '죄송합니다. 오류가 발생했습니다. 다시 시도해주세요.',
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <Card
      title={
        <span>
          <RobotOutlined /> AI 세무 상담
        </span>
      }
      style={{ height: '600px', display: 'flex', flexDirection: 'column' }}
    >
      {/* 메시지 리스트 */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '16px',
          backgroundColor: '#f5f5f5',
        }}
      >
        <List
          dataSource={messages}
          renderItem={(message) => (
            <List.Item
              style={{
                justifyContent: message.role === 'user' ? 'flex-end' : 'flex-start',
                border: 'none',
              }}
            >
              <div
                style={{
                  maxWidth: '70%',
                  display: 'flex',
                  flexDirection: message.role === 'user' ? 'row-reverse' : 'row',
                  alignItems: 'flex-start',
                  gap: '8px',
                }}
              >
                <Avatar
                  icon={message.role === 'user' ? <UserOutlined /> : <RobotOutlined />}
                  style={{
                    backgroundColor: message.role === 'user' ? '#1890ff' : '#52c41a',
                  }}
                />
                <div
                  style={{
                    padding: '12px 16px',
                    borderRadius: '12px',
                    backgroundColor: message.role === 'user' ? '#e6f7ff' : '#fff',
                    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
                  }}
                >
                  <div style={{ whiteSpace: 'pre-wrap' }}>{message.content}</div>

                  {/* 메타데이터 표시 */}
                  {message.metadata && message.metadata.total_tax && (
                    <div style={{ marginTop: '8px' }}>
                      <Tag color="green">
                        예상 납부세액: {message.metadata.total_tax.toLocaleString()}원
                      </Tag>
                    </div>
                  )}

                  <div style={{ fontSize: '12px', color: '#999', marginTop: '4px' }}>
                    {new Date(message.timestamp).toLocaleTimeString()}
                  </div>
                </div>
              </div>
            </List.Item>
          )}
        />
        <div ref={messagesEndRef} />

        {loading && (
          <div style={{ textAlign: 'center', padding: '16px' }}>
            <Spin tip="AI가 답변을 생성하고 있습니다..." />
          </div>
        )}
      </div>

      {/* 입력 영역 */}
      <div style={{ padding: '16px', borderTop: '1px solid #f0f0f0' }}>
        <Input.Group compact style={{ display: 'flex' }}>
          <TextArea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="양도소득세에 대해 궁금한 점을 물어보세요..."
            autoSize={{ minRows: 1, maxRows: 4 }}
            style={{ flex: 1 }}
            disabled={loading}
          />
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={sendMessage}
            loading={loading}
            style={{ marginLeft: '8px' }}
          >
            전송
          </Button>
        </Input.Group>
      </div>
    </Card>
  );
};

export default ChatComponent;
```

### 3.2 App.tsx 통합

**파일**: `frontend/src/App.tsx`

기존 App.tsx에 ChatComponent를 추가합니다:

```tsx
import ChatComponent from './components/ChatComponent';

// ... 기존 코드 ...

function App() {
  // ... 기존 상태 ...

  const [sessionId] = useState(() => `session_${Date.now()}`);

  return (
    <div className="App">
      {/* 기존 컴포넌트들 */}

      {/* 채팅 컴포넌트 추가 */}
      <div style={{ marginTop: '24px' }}>
        <ChatComponent
          sessionId={sessionId}
          transactionId={transactionId}
        />
      </div>
    </div>
  );
}
```

---

## 4. 대화 시나리오 예시

### 시나리오 1: 일반 질문

**사용자**: "1주택자인데 비과세 되나요?"

**AI**: "네, 1세대 1주택자의 경우 다음 조건을 충족하면 양도소득세가 비과세됩니다:

1. **보유기간**: 2년 이상
2. **거주기간**: 2년 이상 (조정대상지역의 경우 추가 요건)
3. **양도가액**: 12억원 이하

현재 상황을 확인하려면 취득일, 양도일, 양도가액 등을 알려주세요!"

### 시나리오 2: 계산 요청

**사용자**: "2020년에 5억에 산 집을 지금 10억에 팔면 세금이 얼마죠?"

**AI**: "계산을 위해 몇 가지 추가 정보가 필요합니다:

1. 정확한 취득일과 양도일을 알려주세요
2. 1세대 1주택인가요?
3. 조정대상지역인가요?

이 정보를 주시면 정확한 세금을 계산해드리겠습니다."

*(정보 입력 후)*

**AI**: "계산 결과를 알려드립니다!

**총 납부세액: 약 1억 2,300만원**

상세 내역:
- 양도차익: 5억원
- 장기보유공제: 8,000만원 (3년 보유 기준)
- 과세표준: 4억 1,750만원
- 산출세액: 1억 1,200만원 (누진세율 적용)
- 지방소득세: 1,120만원

3년 이상 보유하셨기 때문에 장기보유특별공제 혜택을 받으셨습니다. 혹시 1세대 1주택이시라면 비과세 가능성도 있으니 자세한 상황을 알려주세요!"

### 시나리오 3: 전략 상담

**사용자**: "지금 팔까요, 내년에 팔까요?"

**AI (StrategyAgent 실행)**: "입력하신 정보를 바탕으로 시나리오를 분석했습니다.

**케이스 분류**: 1세대 1주택 (비과세 가능)

**시나리오 비교**:

1. **지금 바로 양도** (추천)
   - 예상 세액: 0원 (비과세)
   - 순 편익: +10억원
   - 리스크: 낮음

2. **1년 후 양도**
   - 예상 세액: 0원 (비과세)
   - 순 편익: +9억 8천만원 (기회비용 고려)
   - 리스크: 중간 (세법 변경 가능성)

**추천**: 지금 바로 양도하시는 것을 권장합니다. 비과세 요건을 충족하셨고, 1년 뒤에도 비과세 혜택은 동일하지만 부동산 시장 변동성과 세법 개정 리스크를 고려하면 조기 양도가 유리합니다.

자세한 내용은 세무사와 상담하시는 것을 추천드립니다!"

---

## 5. 구현 우선순위

### Phase 1: 최소 기능 (MVP)
- [x] ChatAgent 기본 구조
- [ ] Intent Classification (LLM)
- [ ] 일반 질문 처리
- [ ] ChatComponent.tsx (프론트엔드)
- [ ] /api/v1/chat/message 엔드포인트

### Phase 2: 계산 통합
- [ ] TaxCalculator 연동
- [ ] 사실관계 입력 유도
- [ ] 계산 결과 설명 생성

### Phase 3: 전략 통합
- [ ] StrategyAgent 연동
- [ ] 시나리오 비교 대화
- [ ] 추천 제시

### Phase 4: 고도화
- [ ] 대화 컨텍스트 저장 (Redis/DB)
- [ ] 스트리밍 응답
- [ ] 음성 입력/출력
- [ ] 대화 이력 내보내기

---

## 6. 기술 스택

| 구분 | 기술 |
|-----|------|
| **LLM** | Claude 3.5 Sonnet (Anthropic) |
| **Backend** | FastAPI, Python 3.11+ |
| **Frontend** | React, TypeScript, Ant Design |
| **Storage** | Redis (세션), PostgreSQL (이력) |
| **API** | REST (기본), WebSocket (스트리밍) |

---

## 7. 보안 및 제약사항

### 7.1 LLM 제약
- LLM은 **설명만** 생성 (계산/판단 X)
- 모든 계산은 **TaxCalculator**가 수행
- 모든 전략은 **StrategyAgent**가 수행

### 7.2 법적 고지
모든 응답에 다음 고지 포함:
```
※ 본 상담은 일반적인 정보 제공 목적이며,
  실제 신고 시에는 세무사와 상담하시기 바랍니다.
```

### 7.3 개인정보 보호
- 대화 이력 암호화
- 세션 만료 시간: 24시간
- 민감 정보 마스킹

---

**문서 버전**: v1.0
**작성일**: 2025-11-22
**다음 단계**: Phase 1 MVP 구현
