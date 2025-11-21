"""AI 에이전트 엔드포인트"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from datetime import datetime

from ...agents import TaxAdvisorAgent, OrchestratorAgent

router = APIRouter(prefix="/agent", tags=["agent"])

# 전역 에이전트 인스턴스 (싱글톤)
agent = None
orchestrator = None


def get_agent() -> TaxAdvisorAgent:
    """에이전트 인스턴스 가져오기 (레거시 호환성)"""
    global agent
    if agent is None:
        # TODO: 환경변수에서 API 키 가져오기
        # openai_api_key = os.getenv('OPENAI_API_KEY')
        agent = TaxAdvisorAgent(openai_api_key=None)  # Mock 모드로 시작
    return agent


def get_orchestrator() -> OrchestratorAgent:
    """Orchestrator 에이전트 인스턴스 가져오기"""
    global orchestrator
    if orchestrator is None:
        # TODO: 환경변수에서 API 키 가져오기
        # openai_api_key = os.getenv('OPENAI_API_KEY')
        orchestrator = OrchestratorAgent(openai_api_key=None, mock_mode=True)
    return orchestrator


class AgentRequest(BaseModel):
    """에이전트 요청 모델"""
    mode: str = "full"  # "intake" | "tax_only" | "full"
    case_id: Optional[str] = None
    form_answers: Dict[str, Any] = {}
    raw_messages: List[Dict[str, Any]] = []

    # Optional direct calculation fields (for testing/direct API use)
    acquisition_date: Optional[str] = None
    acquisition_price: Optional[float] = None
    disposal_date: Optional[str] = None
    disposal_price: Optional[float] = None
    asset_type: Optional[str] = None
    is_primary_residence: Optional[bool] = None
    necessary_expenses: Optional[float] = None
    house_count: Optional[int] = None
    is_adjusted_area: Optional[bool] = None

    class Config:
        json_schema_extra = {
            "example": {
                "mode": "full",
                "case_id": "C2025-0001",
                "form_answers": {
                    "q_asset_type": "residential",
                    "q_is_primary_residence": "예",
                    "q_region": "서울특별시 강남구"
                },
                "raw_messages": [
                    {
                        "sender": "user",
                        "text": "2020년 1월에 5억에 샀고, 2024년 12월에 10억에 팔았어요"
                    }
                ]
            }
        }


class SimpleCalculationRequest(BaseModel):
    """간단한 계산 요청 (기존 사용자를 위한 호환성)"""
    acquisition_date: str
    acquisition_price: float
    disposal_date: str
    disposal_price: float
    asset_type: str = "residential"
    is_primary_residence: bool = False
    necessary_expenses: float = 0
    house_count: int = 1
    is_adjusted_area: bool = False

    class Config:
        json_schema_extra = {
            "example": {
                "acquisition_date": "2020-01-15",
                "acquisition_price": 500000000,
                "disposal_date": "2024-12-20",
                "disposal_price": 1000000000,
                "asset_type": "residential",
                "is_primary_residence": True,
                "necessary_expenses": 5000000,
                "house_count": 1,
                "is_adjusted_area": False
            }
        }


@router.post("/process")
async def process_case(request: AgentRequest):
    """케이스 처리 (풀 에이전트 모드)

    양도소득세 계산을 위한 정보 수집, 계산, 분석, 리포트 생성을 수행합니다.

    이제 5개 에이전트 시스템 사용:
    - 총괄 에이전트 (Orchestrator)
    - 에이전트 #1: 자산정보 수집
    - 에이전트 #2: 세액 산출
    - 에이전트 #3: 계산 검증
    - 에이전트 #4: 신고 준비

    Args:
        request: 에이전트 요청 (폼 답변, 메시지 등)

    Returns:
        {
            "status": "success",
            "case_id": "...",
            "collected_facts": {...},
            "tax_result": {...},
            "verification": {...},
            "filing_package": {...},
            "quality_check": {...},
            "report": "..."
        }
    """
    try:
        # 새로운 Orchestrator 에이전트 사용
        orchestrator_instance = get_orchestrator()
        result = await orchestrator_instance.process_case(request.dict())

        # 레거시 필드 매핑 (기존 API 호환성)
        if result.get('status') == 'success':
            result['risk_flags'] = result.get('verification', {}).get('risk_flags', [])

        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"에이전트 처리 중 오류: {str(e)}"
        )


@router.post("/calculate-simple")
async def calculate_simple(request: SimpleCalculationRequest):
    """Simple calculation mode (bypass fact confirmation)

    Directly calculates tax without fact confirmation system.
    """
    try:
        from ...core import TaxCalculator, FactLedger
        from datetime import datetime as dt
        from decimal import Decimal

        # Create fact ledger with confirmed facts
        facts_dict = {
            'acquisition_date': dt.strptime(request.acquisition_date, "%Y-%m-%d").date(),
            'acquisition_price': Decimal(str(request.acquisition_price)),
            'disposal_date': dt.strptime(request.disposal_date, "%Y-%m-%d").date(),
            'disposal_price': Decimal(str(request.disposal_price)),
            'asset_type': request.asset_type,
            'is_primary_residence': request.is_primary_residence,
            'necessary_expenses': Decimal(str(request.necessary_expenses)),
            'house_count': request.house_count,
            'is_adjusted_area': request.is_adjusted_area,
        }

        # Create ledger
        ledger = FactLedger.create(facts_dict, created_by="api")

        # Bypass fact confirmation system for simple API
        # (directly mark all facts as confirmed and freeze)
        from ...core.fact import Fact
        for attr_name in vars(ledger):
            attr = getattr(ledger, attr_name)
            if isinstance(attr, Fact) and not attr.is_confirmed:
                # Directly set confirmation without validation (frozen dataclass workaround)
                object.__setattr__(attr, 'is_confirmed', True)
                object.__setattr__(attr, 'confidence', 1.0)
                object.__setattr__(attr, 'entered_by', "api")
                object.__setattr__(attr, 'entered_at', datetime.now())

        # Now freeze (will pass since all facts are confirmed)
        ledger.is_frozen = True

        # Calculate
        calculator = TaxCalculator()
        result = calculator.calculate(ledger)

        # Convert to dict (use ledger values for disposal/acquisition prices)
        disposal_price_val = float(ledger.disposal_price.value)
        acquisition_price_val = float(ledger.acquisition_price.value)
        necessary_exp_val = float(ledger.necessary_expenses.value) if ledger.necessary_expenses else 0

        return {
            "status": "success",
            "tax_result": {
                'disposal_price': disposal_price_val,
                'acquisition_price': acquisition_price_val,
                'capital_gain': disposal_price_val - acquisition_price_val,
                'necessary_expenses': necessary_exp_val,
                'long_term_deduction': float(getattr(result, 'long_term_deduction', 0)),
                'basic_deduction': float(getattr(result, 'basic_deduction', 0)),
                'taxable_income': float(getattr(result, 'taxable_income', 0)),
                'calculated_tax': float(getattr(result, 'calculated_tax', 0)),
                'local_tax': float(getattr(result, 'local_tax', 0)),
                'total_tax': float(getattr(result, 'total_tax', 0)),
                'applied_tax_rate': float(getattr(result, 'applied_tax_rate', 0)),
                'warnings': getattr(result, 'warnings', [])
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Calculation error: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Agent health check"""
    try:
        orchestrator_instance = get_orchestrator()
        result = {
            "status": "healthy",
            "agent_mode": "mock" if orchestrator_instance.mock_mode else "llm",
            "agent_system": "5-agent (Orchestrator + 4 workers)",
            "agents": {
                "orchestrator": "OrchestratorAgent",
                "asset_collector": "AssetCollectorAgent",
                "tax_calculator": "TaxCalculationAgent",
                "verifier": "CalculationVerificationAgent",
                "filing": "FilingAgent"
            },
            "timestamp": datetime.now().isoformat()
        }
        print(f"Health check result: {result}")
        return result
    except Exception as e:
        print(f"Health check ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise
