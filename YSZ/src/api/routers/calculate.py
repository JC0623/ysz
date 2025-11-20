"""세금 계산 API 라우터"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from decimal import Decimal

from ...database import get_db, TransactionDB, FactDB, CalculationResultDB
from ...core import FactLedger, Fact, TaxCalculator
from ..schemas import (
    CalculationResponse,
    TaxBreakdownItem,
    ErrorResponse
)
from .facts import _load_fact_from_db

router = APIRouter()


def _load_ledger_from_db(
    db: Session,
    transaction_id: int
) -> FactLedger:
    """데이터베이스에서 FactLedger 로드"""
    # Facts 조회
    fact_dbs = db.query(FactDB).filter(
        FactDB.transaction_id == transaction_id
    ).all()

    if not fact_dbs:
        raise ValueError(f"거래 ID {transaction_id}에 대한 사실관계가 없습니다.")

    # Fact 객체로 변환
    facts_dict = {}
    for fact_db in fact_dbs:
        field_name, fact = _load_fact_from_db(fact_db)
        facts_dict[field_name] = fact

    # FactLedger 생성
    ledger = FactLedger.create(facts_dict)
    return ledger


@router.post("/{transaction_id}", response_model=CalculationResponse)
async def calculate_tax(
    transaction_id: int,
    db: Session = Depends(get_db)
):
    """양도소득세 계산

    수집된 사실관계를 바탕으로 양도소득세를 계산합니다.
    """
    try:
        # 거래 조회
        transaction = db.query(TransactionDB).filter(
            TransactionDB.id == transaction_id
        ).first()

        if not transaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"거래 ID {transaction_id}를 찾을 수 없습니다."
            )

        # FactLedger 로드
        ledger = _load_ledger_from_db(db, transaction_id)

        # 필수 필드 확인
        required_fields = [
            'acquisition_date',
            'acquisition_price',
            'disposal_date',
            'disposal_price',
            'asset_type'
        ]

        missing_fields = []
        for field in required_fields:
            if not hasattr(ledger, field) or getattr(ledger, field) is None:
                missing_fields.append(field)

        if missing_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"필수 필드가 누락되었습니다: {', '.join(missing_fields)}"
            )

        # 세금 계산
        calculator = TaxCalculator()
        result = calculator.calculate(ledger)

        # 계산 결과 저장
        calc_result_db = CalculationResultDB(
            transaction_id=transaction_id,
            calculated_at=datetime.utcnow(),
            disposal_price=result.disposal_price,
            acquisition_price=result.acquisition_price,
            necessary_expenses=result.necessary_expenses,
            long_term_deduction=result.long_term_deduction,
            basic_deduction=result.basic_deduction,
            taxable_income=result.taxable_income,
            calculated_tax=result.calculated_tax,
            local_tax=result.local_tax,
            total_tax=result.total_tax,
            applied_tax_rate=result.applied_tax_rate,
            calculation_details=result.calculation_details,
            applied_rules=[rule['rule_id'] for rule in result.applied_rules]
        )

        db.add(calc_result_db)

        # 거래 상태 업데이트
        transaction.status = "calculated"
        transaction.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(calc_result_db)

        # 상세 내역 생성
        breakdown = [
            TaxBreakdownItem(
                label="양도가액",
                amount=result.disposal_price,
                description="부동산 판매 가격"
            ),
            TaxBreakdownItem(
                label="취득가액",
                amount=result.acquisition_price,
                description="부동산 구매 가격"
            ),
            TaxBreakdownItem(
                label="필요경비",
                amount=result.necessary_expenses,
                description="취득세, 중개수수료 등"
            ),
            TaxBreakdownItem(
                label="양도차익",
                amount=result.disposal_price - result.acquisition_price - result.necessary_expenses,
                description="양도가액 - 취득가액 - 필요경비"
            ),
            TaxBreakdownItem(
                label="장기보유특별공제",
                amount=result.long_term_deduction,
                description="보유 기간에 따른 공제"
            ),
            TaxBreakdownItem(
                label="기본공제",
                amount=result.basic_deduction,
                description="양도소득 기본공제 (연 250만원)"
            ),
            TaxBreakdownItem(
                label="과세표준",
                amount=result.taxable_income,
                description="세금이 부과되는 기준 금액"
            ),
            TaxBreakdownItem(
                label="산출세액",
                amount=result.calculated_tax,
                description=f"과세표준 × 세율 ({result.applied_tax_rate*100:.1f}%)"
            ),
            TaxBreakdownItem(
                label="지방소득세",
                amount=result.local_tax,
                description="산출세액의 10%"
            ),
            TaxBreakdownItem(
                label="총 납부세액",
                amount=result.total_tax,
                description="산출세액 + 지방소득세"
            )
        ]

        return CalculationResponse(
            transaction_id=transaction_id,
            calculated_at=calc_result_db.calculated_at,
            disposal_price=result.disposal_price,
            acquisition_price=result.acquisition_price,
            capital_gain=result.disposal_price - result.acquisition_price,
            necessary_expenses=result.necessary_expenses,
            long_term_deduction=result.long_term_deduction,
            basic_deduction=result.basic_deduction,
            taxable_income=result.taxable_income,
            calculated_tax=result.calculated_tax,
            local_tax=result.local_tax,
            total_tax=result.total_tax,
            applied_tax_rate=float(result.applied_tax_rate) if result.applied_tax_rate else None,
            breakdown=breakdown,
            applied_rules=[rule['rule_id'] for rule in result.applied_rules],
            message="양도소득세 계산이 완료되었습니다."
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"세금 계산 실패: {str(e)}"
        )


@router.get("/{transaction_id}/result", response_model=CalculationResponse)
async def get_calculation_result(
    transaction_id: int,
    db: Session = Depends(get_db)
):
    """저장된 계산 결과 조회"""
    # 거래 조회
    transaction = db.query(TransactionDB).filter(
        TransactionDB.id == transaction_id
    ).first()

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"거래 ID {transaction_id}를 찾을 수 없습니다."
        )

    # 가장 최근 계산 결과 조회
    calc_result = db.query(CalculationResultDB).filter(
        CalculationResultDB.transaction_id == transaction_id
    ).order_by(CalculationResultDB.calculated_at.desc()).first()

    if not calc_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"거래 ID {transaction_id}에 대한 계산 결과가 없습니다."
        )

    # 상세 내역 생성
    capital_gain = calc_result.disposal_price - calc_result.acquisition_price
    breakdown = [
        TaxBreakdownItem(
            label="양도가액",
            amount=calc_result.disposal_price,
            description="부동산 판매 가격"
        ),
        TaxBreakdownItem(
            label="취득가액",
            amount=calc_result.acquisition_price,
            description="부동산 구매 가격"
        ),
        TaxBreakdownItem(
            label="필요경비",
            amount=calc_result.necessary_expenses,
            description="취득세, 중개수수료 등"
        ),
        TaxBreakdownItem(
            label="양도차익",
            amount=capital_gain - calc_result.necessary_expenses,
            description="양도가액 - 취득가액 - 필요경비"
        ),
        TaxBreakdownItem(
            label="장기보유특별공제",
            amount=calc_result.long_term_deduction,
            description="보유 기간에 따른 공제"
        ),
        TaxBreakdownItem(
            label="기본공제",
            amount=calc_result.basic_deduction,
            description="양도소득 기본공제 (연 250만원)"
        ),
        TaxBreakdownItem(
            label="과세표준",
            amount=calc_result.taxable_income,
            description="세금이 부과되는 기준 금액"
        ),
        TaxBreakdownItem(
            label="산출세액",
            amount=calc_result.calculated_tax,
            description=f"과세표준 × 세율"
        ),
        TaxBreakdownItem(
            label="지방소득세",
            amount=calc_result.local_tax,
            description="산출세액의 10%"
        ),
        TaxBreakdownItem(
            label="총 납부세액",
            amount=calc_result.total_tax,
            description="산출세액 + 지방소득세"
        )
    ]

    return CalculationResponse(
        transaction_id=transaction_id,
        calculated_at=calc_result.calculated_at,
        disposal_price=calc_result.disposal_price,
        acquisition_price=calc_result.acquisition_price,
        capital_gain=capital_gain,
        necessary_expenses=calc_result.necessary_expenses,
        long_term_deduction=calc_result.long_term_deduction,
        basic_deduction=calc_result.basic_deduction,
        taxable_income=calc_result.taxable_income,
        calculated_tax=calc_result.calculated_tax,
        local_tax=calc_result.local_tax,
        total_tax=calc_result.total_tax,
        applied_tax_rate=float(calc_result.applied_tax_rate) if calc_result.applied_tax_rate else None,
        breakdown=breakdown,
        applied_rules=calc_result.applied_rules or [],
        message="저장된 계산 결과입니다."
    )
