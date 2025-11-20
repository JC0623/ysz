"""사실관계 수집 및 확인 API 라우터"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from datetime import datetime, date
from decimal import Decimal

from ...database import get_db, TransactionDB, FactDB
from ...collectors import FactCollector
from ...core import FactLedger, Fact
from ..schemas import (
    CollectFactsRequest,
    CollectFactsResponse,
    FactResponse,
    ConfirmFactRequest,
    ConfirmFactsRequest,
    ConfirmFactResponse,
    TransactionResponse,
    TransactionListResponse,
    ErrorResponse
)

router = APIRouter()


def _fact_to_response(field_name: str, fact: Fact) -> FactResponse:
    """Fact 객체를 FactResponse로 변환"""
    return FactResponse(
        field_name=field_name,
        value=fact.value,
        value_type=type(fact.value).__name__,
        source=fact.source,
        confidence=float(fact.confidence),
        is_confirmed=fact.is_confirmed,
        created_at=fact.entered_at,  # Fact uses entered_at not created_at
        entered_by=fact.entered_by
    )


def _save_fact_to_db(
    db: Session,
    transaction_id: int,
    field_name: str,
    fact: Fact
) -> FactDB:
    """Fact 객체를 데이터베이스에 저장"""
    # 값의 타입에 따라 적절한 컬럼에 저장
    value_type = None
    value_string = None
    value_numeric = None
    value_date = None
    value_boolean = None

    if isinstance(fact.value, str):
        value_type = "string"
        value_string = fact.value
    elif isinstance(fact.value, (int, float, Decimal)):
        value_type = "numeric"
        value_numeric = Decimal(str(fact.value))
    elif isinstance(fact.value, date):
        value_type = "date"
        value_date = fact.value
    elif isinstance(fact.value, bool):
        value_type = "boolean"
        value_boolean = fact.value
    else:
        value_type = "string"
        value_string = str(fact.value)

    fact_db = FactDB(
        transaction_id=transaction_id,
        field_name=field_name,
        value_type=value_type,
        value_string=value_string,
        value_numeric=value_numeric,
        value_date=value_date,
        value_boolean=value_boolean,
        source=fact.source,
        confidence=Decimal(str(fact.confidence)),
        is_confirmed=fact.is_confirmed,
        created_at=fact.entered_at,  # Fact uses entered_at not created_at
        entered_by=fact.entered_by,
        confirmed_at=None,  # Fact doesn't have confirmed_at attribute
        confirmed_by=None,  # Fact doesn't have confirmed_by attribute
        extra_metadata=None  # Fact doesn't have metadata attribute
    )

    db.add(fact_db)
    return fact_db


def _load_fact_from_db(fact_db: FactDB) -> tuple[str, Fact]:
    """데이터베이스에서 Fact 객체 로드"""
    # 타입에 맞는 값 추출
    if fact_db.value_type == "string":
        value = fact_db.value_string
    elif fact_db.value_type == "numeric":
        value = fact_db.value_numeric
    elif fact_db.value_type == "date":
        value = fact_db.value_date
    elif fact_db.value_type == "boolean":
        value = fact_db.value_boolean
    else:
        value = fact_db.value_string

    fact = Fact(
        value=value,
        source=fact_db.source,
        confidence=float(fact_db.confidence),
        is_confirmed=fact_db.is_confirmed,
        entered_by=fact_db.entered_by,
        entered_at=fact_db.created_at  # Map DB's created_at to Fact's entered_at
    )

    return (fact_db.field_name, fact)


@router.post("/collect", response_model=CollectFactsResponse)
async def collect_facts(
    request: CollectFactsRequest,
    db: Session = Depends(get_db)
):
    """사용자 입력에서 사실관계 수집

    사용자가 입력한 데이터를 수집하여 새로운 거래 세션을 생성합니다.
    """
    try:
        collector = FactCollector()

        # 사용자 입력을 딕셔너리로 변환
        user_data = request.user_data.model_dump(exclude_none=True)

        # 사실관계 수집
        user_facts = await collector.collect_from_user_input(
            user_data,
            entered_by=request.created_by
        )

        # FactLedger 생성
        ledger = await collector.merge_facts(
            [user_facts],
            created_by=request.created_by
        )

        # 거래 생성
        transaction = TransactionDB(
            created_by=request.created_by,
            status="draft",
            notes=request.notes
        )
        db.add(transaction)
        db.flush()  # ID 생성

        # Facts 저장
        for field_name in dir(ledger):
            if field_name.startswith('_'):
                continue
            fact = getattr(ledger, field_name, None)
            if isinstance(fact, Fact):
                _save_fact_to_db(db, transaction.id, field_name, fact)

        db.commit()
        db.refresh(transaction)

        # 응답 생성
        fact_responses = []
        for field_name in dir(ledger):
            if field_name.startswith('_'):
                continue
            fact = getattr(ledger, field_name, None)
            if isinstance(fact, Fact):
                fact_responses.append(_fact_to_response(field_name, fact))

        missing_fields = collector.get_missing_facts(ledger)
        unconfirmed_fields = collector.get_unconfirmed_facts(ledger)

        return CollectFactsResponse(
            transaction_id=transaction.id,
            status=transaction.status,
            facts=fact_responses,
            missing_fields=missing_fields,
            unconfirmed_fields=unconfirmed_fields,
            message=f"사실관계 수집 완료. 총 {len(fact_responses)}개 항목 수집됨."
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"사실관계 수집 실패: {str(e)}"
        )


@router.post("/{transaction_id}/confirm", response_model=ConfirmFactResponse)
async def confirm_facts(
    transaction_id: int,
    request: ConfirmFactsRequest,
    db: Session = Depends(get_db)
):
    """사실관계 확인

    사용자가 확인한 사실관계를 저장합니다.
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

        # 확인할 Fact들 조회
        confirmed_count = 0
        for field_name in request.field_names:
            fact_db = db.query(FactDB).filter(
                FactDB.transaction_id == transaction_id,
                FactDB.field_name == field_name
            ).first()

            if fact_db:
                fact_db.is_confirmed = True
                fact_db.confirmed_at = datetime.utcnow()
                fact_db.confirmed_by = request.confirmed_by
                confirmed_count += 1

        # 모든 필수 Fact가 확인되었는지 체크
        all_facts = db.query(FactDB).filter(
            FactDB.transaction_id == transaction_id
        ).all()

        unconfirmed = [
            f.field_name for f in all_facts
            if not f.is_confirmed
        ]

        # 상태 업데이트
        if not unconfirmed:
            transaction.status = "confirmed"

        db.commit()

        return ConfirmFactResponse(
            transaction_id=transaction_id,
            confirmed_fields=request.field_names,
            remaining_unconfirmed=unconfirmed,
            message=f"{confirmed_count}개 항목이 확인되었습니다."
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"사실관계 확인 실패: {str(e)}"
        )


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: int,
    db: Session = Depends(get_db)
):
    """거래 정보 조회"""
    transaction = db.query(TransactionDB).filter(
        TransactionDB.id == transaction_id
    ).first()

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"거래 ID {transaction_id}를 찾을 수 없습니다."
        )

    facts_count = db.query(FactDB).filter(
        FactDB.transaction_id == transaction_id
    ).count()

    has_calculation = db.query(TransactionDB).filter(
        TransactionDB.id == transaction_id
    ).join(TransactionDB.calculation_results).first() is not None

    return TransactionResponse(
        id=transaction.id,
        created_at=transaction.created_at,
        created_by=transaction.created_by,
        updated_at=transaction.updated_at,
        status=transaction.status,
        notes=transaction.notes,
        facts_count=facts_count,
        has_calculation=has_calculation
    )


@router.get("/", response_model=TransactionListResponse)
async def list_transactions(
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db)
):
    """거래 목록 조회"""
    offset = (page - 1) * page_size

    # 총 개수
    total = db.query(TransactionDB).count()

    # 페이지 데이터
    transactions = db.query(TransactionDB).order_by(
        TransactionDB.created_at.desc()
    ).offset(offset).limit(page_size).all()

    # 응답 생성
    transaction_responses = []
    for t in transactions:
        facts_count = db.query(FactDB).filter(
            FactDB.transaction_id == t.id
        ).count()

        has_calculation = db.query(TransactionDB).filter(
            TransactionDB.id == t.id
        ).join(TransactionDB.calculation_results).first() is not None

        transaction_responses.append(TransactionResponse(
            id=t.id,
            created_at=t.created_at,
            created_by=t.created_by,
            updated_at=t.updated_at,
            status=t.status,
            notes=t.notes,
            facts_count=facts_count,
            has_calculation=has_calculation
        ))

    return TransactionListResponse(
        transactions=transaction_responses,
        total=total,
        page=page,
        page_size=page_size
    )
