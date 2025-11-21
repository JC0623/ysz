"""Strategy API Router

StrategyAgent를 프론트엔드에 노출하는 REST API
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import date, datetime
from decimal import Decimal

from ...agents.strategy_agent import StrategyAgent
from ...core import FactLedger, Fact

router = APIRouter(prefix="/strategy", tags=["strategy"])

# StrategyAgent 인스턴스 (전역, 싱글톤 패턴)
_strategy_agent: Optional[StrategyAgent] = None


def get_strategy_agent() -> StrategyAgent:
    """StrategyAgent 인스턴스 가져오기 (지연 초기화)"""
    global _strategy_agent
    if _strategy_agent is None:
        _strategy_agent = StrategyAgent(
            
            enable_llm=True  # LLM 설명 생성 활성화
        )
    return _strategy_agent


# ========== Request/Response 스키마 ==========

class AnalyzeRequest(BaseModel):
    """전략 분석 요청"""

    # 사실관계 정보
    acquisition_date: date = Field(..., description="취득일")
    acquisition_price: Decimal = Field(..., description="취득가액 (원)")
    disposal_date: date = Field(..., description="양도일")
    disposal_price: Decimal = Field(..., description="양도가액 (원)")

    # 선택 정보
    asset_type: Optional[str] = Field("residential", description="자산 유형 (residential, commercial, land)")
    house_count: Optional[int] = Field(1, description="보유 주택 수")
    residence_period_years: Optional[int] = Field(None, description="거주 기간 (년)")
    is_adjusted_area: Optional[bool] = Field(False, description="조정대상지역 여부")
    necessary_expenses: Optional[Decimal] = Field(Decimal(0), description="필요경비")

    # 옵션
    enable_explanation: bool = Field(True, description="LLM 설명 생성 여부")

    class Config:
        json_schema_extra = {
            "example": {
                "acquisition_date": "2020-01-15",
                "acquisition_price": 500000000,
                "disposal_date": "2024-12-01",
                "disposal_price": 1000000000,
                "asset_type": "residential",
                "house_count": 1,
                "residence_period_years": 3,
                "is_adjusted_area": False,
                "necessary_expenses": 0,
                "enable_explanation": True
            }
        }


class ScenarioResponse(BaseModel):
    """시나리오 응답"""
    scenario_id: str
    scenario_name: str
    disposal_date: str
    expected_tax: float
    net_benefit: float
    is_recommended: bool
    pros: List[str]
    cons: List[str]


class RiskResponse(BaseModel):
    """리스크 응답"""
    level: str  # "none", "low", "medium", "high"
    title: str
    description: str
    mitigation: Optional[str] = None


class AnalyzeResponse(BaseModel):
    """전략 분석 응답"""

    # 케이스 분류
    category: str
    category_description: str
    classification_reasoning: str

    # 시나리오
    scenarios: List[ScenarioResponse]
    recommended_scenario_id: str

    # 리스크
    risks: List[RiskResponse]

    # LLM 설명
    llm_explanation: Optional[str] = None

    # 메타데이터
    analyzed_at: str
    agent_version: str

    class Config:
        json_schema_extra = {
            "example": {
                "category": "1주택_비과세",
                "category_description": "1세대 1주택, 비과세 요건 충족",
                "classification_reasoning": "보유 주택 수: 1채, 보유 기간: 4.9년",
                "scenarios": [
                    {
                        "scenario_id": "SC_NOW",
                        "scenario_name": "지금 바로 양도",
                        "disposal_date": "2024-12-01",
                        "expected_tax": 0,
                        "net_benefit": 1000000000,
                        "is_recommended": True,
                        "pros": ["비과세 혜택", "즉시 현금화"],
                        "cons": []
                    }
                ],
                "recommended_scenario_id": "SC_NOW",
                "risks": [],
                "llm_explanation": "보유 2년 이상, 거주 2년 이상 조건을 충족하여...",
                "analyzed_at": "2024-11-22T10:00:00Z",
                "agent_version": "1.0.0"
            }
        }


class CategoryListResponse(BaseModel):
    """카테고리 목록 응답"""
    categories: List[Dict[str, str]]

    class Config:
        json_schema_extra = {
            "example": {
                "categories": [
                    {"code": "1주택_비과세", "name": "1세대 1주택 비과세"},
                    {"code": "1주택_과세", "name": "1세대 1주택 과세"},
                    {"code": "다주택_일반", "name": "다주택 일반 과세"}
                ]
            }
        }


# ========== API 엔드포인트 ==========

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_strategy(request: AnalyzeRequest):
    """
    전략 분석 (StrategyAgent 실행)

    사실관계 정보를 받아 케이스를 분류하고 시나리오를 생성합니다.

    **처리 과정**:
    1. FactLedger 생성
    2. StrategyAgent 실행
    3. 케이스 분류
    4. 시나리오 생성
    5. 추천 제시
    6. (선택) LLM 설명 생성

    **Returns**:
        AnalyzeResponse: 분석 결과
    """
    try:
        # 1. FactLedger 생성
        facts_dict = {
            "acquisition_date": request.acquisition_date,
            "acquisition_price": request.acquisition_price,
            "disposal_date": request.disposal_date,
            "disposal_price": request.disposal_price,
            "asset_type": request.asset_type,
            "house_count": request.house_count,
            "residence_period_years": request.residence_period_years,
            "is_adjusted_area": request.is_adjusted_area,
            "necessary_expenses": request.necessary_expenses
        }

        # Fact 생성 시 confidence=1.0으로 설정 (API 데이터는 신뢰함)
        facts_dict_confirmed = {}
        for key, value in facts_dict.items():
            if isinstance(value, dict):
                value['confidence'] = 1.0
                value['is_confirmed'] = True
                facts_dict_confirmed[key] = value
            else:
                facts_dict_confirmed[key] = {
                    'value': value,
                    'confidence': 1.0,
                    'is_confirmed': True
                }
        
        # Fact 객체로 직접 생성 (confirmed=True)
        from ...core import Fact
        fact_objects = {}
        for key, value in facts_dict.items():
            fact_objects[key] = Fact(
                value=value,
                source="api",
                confidence=1.0,
                is_confirmed=True
            )
        
        ledger = FactLedger.create(fact_objects, created_by="api_user")

        # 3. 응답 변환
        scenarios = [
            ScenarioResponse(
                scenario_id=s.scenario_id,
                scenario_name=s.scenario_name,
                disposal_date=s.disposal_date.isoformat(),
                expected_tax=float(s.expected_tax),
                net_benefit=float(s.net_benefit),
                is_recommended=(s.scenario_id == strategy.recommended_scenario_id),
                pros=s.pros,
                cons=s.cons
            )
            for s in strategy.scenarios
        ]

        risks = [
            RiskResponse(
                level=r.level.value,
                title=r.title,
                description=r.description,
                mitigation=r.mitigation
            )
            for r in strategy.risks
        ]

        return AnalyzeResponse(
            category=strategy.category.value,
            category_description=strategy.category.value.replace("_", " "),
            classification_reasoning=strategy.classification_reasoning,
            scenarios=scenarios,
            recommended_scenario_id=strategy.recommended_scenario_id,
            risks=risks,
            llm_explanation=strategy.llm_explanation,
            analyzed_at=datetime.now().isoformat(),
            agent_version="1.0.0"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"전략 분석 중 오류 발생: {str(e)}"
        )


@router.get("/categories", response_model=CategoryListResponse)
def get_categories():
    """
    케이스 카테고리 목록 조회

    **Returns**:
        CategoryListResponse: 카테고리 목록
    """
    from ...agents.strategy_models import CaseCategory

    categories = [
        {"code": cat.value, "name": cat.value.replace("_", " ")}
        for cat in CaseCategory
    ]

    return CategoryListResponse(categories=categories)


@router.get("/health")
def health_check():
    """
    헬스 체크

    **Returns**:
        dict: 상태 정보
    """
    agent = get_strategy_agent()
    return {
        "status": "healthy",
        "llm_enabled": agent.enable_llm,
        "rule_registry": "loaded"
    }
