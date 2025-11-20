"""API 요청/응답 스키마 (Pydantic)"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import date, datetime
from decimal import Decimal


# ============================================================================
# 사실관계 수집 관련 스키마
# ============================================================================

class UserInputData(BaseModel):
    """사용자 입력 데이터

    사용자가 직접 입력하는 거래 정보입니다.
    """
    # 필수 필드
    acquisition_date: date = Field(..., description="취득일")
    acquisition_price: Decimal = Field(..., description="취득가액", ge=0)
    disposal_date: date = Field(..., description="양도일")
    disposal_price: Decimal = Field(..., description="양도가액", ge=0)
    asset_type: str = Field(..., description="자산 유형 (예: residential, commercial)")

    # 선택 필드
    necessary_expenses: Optional[Decimal] = Field(None, description="필요경비", ge=0)
    holding_period_years: Optional[int] = Field(None, description="보유기간(년)", ge=0)
    acquisition_tax_paid: Optional[Decimal] = Field(None, description="취득세", ge=0)

    # 주택 관련 (주거용인 경우)
    is_primary_residence: Optional[bool] = Field(None, description="1세대 1주택 여부")
    number_of_houses: Optional[int] = Field(None, description="주택 수", ge=0)

    # 조정지역
    is_adjusted_area: Optional[bool] = Field(None, description="조정대상지역 여부")

    class Config:
        json_schema_extra = {
            "example": {
                "acquisition_date": "2020-05-01",
                "acquisition_price": 500000000,
                "disposal_date": "2025-10-20",
                "disposal_price": 800000000,
                "asset_type": "residential",
                "necessary_expenses": 10000000,
                "holding_period_years": 5,
                "is_primary_residence": False,
                "number_of_houses": 2,
                "is_adjusted_area": True
            }
        }


class CollectFactsRequest(BaseModel):
    """사실관계 수집 요청"""
    user_data: UserInputData
    created_by: str = Field(default="user", description="생성자")
    notes: Optional[str] = Field(None, description="메모")


class FactResponse(BaseModel):
    """단일 Fact 응답"""
    field_name: str
    value: Any
    value_type: str
    source: str
    confidence: float
    is_confirmed: bool
    created_at: datetime
    entered_by: Optional[str] = None


class CollectFactsResponse(BaseModel):
    """사실관계 수집 응답"""
    transaction_id: int
    status: str
    facts: List[FactResponse]
    missing_fields: List[str]
    unconfirmed_fields: List[str]
    message: str


# ============================================================================
# 사실관계 확인 관련 스키마
# ============================================================================

class ConfirmFactRequest(BaseModel):
    """사실관계 확인 요청"""
    field_name: str = Field(..., description="확인할 필드명")
    confirmed_by: str = Field(default="user", description="확인자")


class ConfirmFactsRequest(BaseModel):
    """여러 사실관계 일괄 확인 요청"""
    field_names: List[str] = Field(..., description="확인할 필드명 리스트")
    confirmed_by: str = Field(default="user", description="확인자")


class ConfirmFactResponse(BaseModel):
    """사실관계 확인 응답"""
    transaction_id: int
    confirmed_fields: List[str]
    remaining_unconfirmed: List[str]
    message: str


# ============================================================================
# 세금 계산 관련 스키마
# ============================================================================

class TaxBreakdownItem(BaseModel):
    """세금 계산 항목"""
    label: str
    amount: Decimal
    description: Optional[str] = None


class CalculationResponse(BaseModel):
    """세금 계산 응답"""
    transaction_id: int
    calculated_at: datetime

    # 기본 금액
    disposal_price: Decimal
    acquisition_price: Decimal
    capital_gain: Decimal
    necessary_expenses: Decimal

    # 공제
    long_term_deduction: Decimal
    basic_deduction: Decimal

    # 세액
    taxable_income: Decimal
    calculated_tax: Decimal
    local_tax: Decimal
    total_tax: Decimal

    # 세율
    applied_tax_rate: Optional[float] = None

    # 상세 내역
    breakdown: List[TaxBreakdownItem]
    applied_rules: List[str]

    message: str

    class Config:
        json_schema_extra = {
            "example": {
                "transaction_id": 1,
                "calculated_at": "2025-11-20T10:30:00Z",
                "disposal_price": 800000000,
                "acquisition_price": 500000000,
                "capital_gain": 300000000,
                "necessary_expenses": 10000000,
                "long_term_deduction": 0,
                "basic_deduction": 2500000,
                "taxable_income": 287500000,
                "calculated_tax": 135875000,
                "local_tax": 13587500,
                "total_tax": 149462500,
                "applied_tax_rate": 0.58,
                "breakdown": [],
                "applied_rules": ["2024_progressive_tax_rate"],
                "message": "세금 계산이 완료되었습니다."
            }
        }


# ============================================================================
# 거래 조회 관련 스키마
# ============================================================================

class TransactionResponse(BaseModel):
    """거래 정보 응답"""
    id: int
    created_at: datetime
    created_by: str
    updated_at: datetime
    status: str
    notes: Optional[str] = None
    facts_count: int
    has_calculation: bool


class TransactionListResponse(BaseModel):
    """거래 목록 응답"""
    transactions: List[TransactionResponse]
    total: int
    page: int
    page_size: int


# ============================================================================
# 에러 응답
# ============================================================================

class ErrorResponse(BaseModel):
    """에러 응답"""
    error: str
    detail: Optional[str] = None
    field: Optional[str] = None
