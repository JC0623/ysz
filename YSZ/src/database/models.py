"""데이터베이스 모델 정의"""

from sqlalchemy import (
    Column, Integer, String, DateTime, Numeric, Boolean,
    Text, ForeignKey, Date, JSON
)
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()


class TransactionDB(Base):
    """거래 정보 테이블

    하나의 양도소득세 계산 세션을 나타냅니다.
    여러 Fact들과 계산 결과를 포함합니다.
    """
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)

    # 생성 정보
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(String(100), nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 상태 정보
    status = Column(
        String(50),
        default="draft",
        nullable=False,
        comment="draft, confirmed, calculated"
    )

    # 메타데이터
    notes = Column(Text, nullable=True, comment="사용자 메모")
    extra_metadata = Column(JSON, nullable=True, comment="추가 메타데이터")

    # 관계
    facts = relationship(
        "FactDB",
        back_populates="transaction",
        cascade="all, delete-orphan"
    )
    calculation_results = relationship(
        "CalculationResultDB",
        back_populates="transaction",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Transaction(id={self.id}, status={self.status}, created_at={self.created_at})>"


class FactDB(Base):
    """사실관계 테이블

    FactLedger의 각 필드를 저장합니다.
    """
    __tablename__ = "facts"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(
        Integer,
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # 필드 정보
    field_name = Column(String(100), nullable=False, index=True)

    # 값 (타입별로 저장)
    value_string = Column(Text, nullable=True)
    value_numeric = Column(Numeric(20, 2), nullable=True)
    value_date = Column(Date, nullable=True)
    value_boolean = Column(Boolean, nullable=True)
    value_type = Column(
        String(20),
        nullable=False,
        comment="string, numeric, date, boolean"
    )

    # Fact 메타데이터
    source = Column(String(100), nullable=False, comment="데이터 출처")
    confidence = Column(Numeric(3, 2), nullable=False, default=1.0)
    is_confirmed = Column(Boolean, default=False, nullable=False)

    # 추적 정보
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    entered_by = Column(String(100), nullable=True)
    confirmed_at = Column(DateTime, nullable=True)
    confirmed_by = Column(String(100), nullable=True)

    # 추가 메타데이터
    extra_metadata = Column(JSON, nullable=True)

    # 관계
    transaction = relationship("TransactionDB", back_populates="facts")

    def __repr__(self):
        return (
            f"<Fact(id={self.id}, field={self.field_name}, "
            f"source={self.source}, confirmed={self.is_confirmed})>"
        )


class CalculationResultDB(Base):
    """세금 계산 결과 테이블

    양도소득세 계산 결과를 저장합니다.
    """
    __tablename__ = "calculation_results"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(
        Integer,
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # 계산 시점
    calculated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 기본 금액
    disposal_price = Column(Numeric(20, 2), nullable=False, comment="양도가액")
    acquisition_price = Column(Numeric(20, 2), nullable=False, comment="취득가액")
    necessary_expenses = Column(Numeric(20, 2), nullable=False, comment="필요경비")

    # 공제액
    long_term_deduction = Column(Numeric(20, 2), nullable=False, comment="장기보유특별공제")
    basic_deduction = Column(Numeric(20, 2), nullable=False, comment="기본공제")

    # 과세표준 및 세액
    taxable_income = Column(Numeric(20, 2), nullable=False, comment="과세표준")
    calculated_tax = Column(Numeric(20, 2), nullable=False, comment="산출세액")
    local_tax = Column(Numeric(20, 2), nullable=False, comment="지방소득세")
    total_tax = Column(Numeric(20, 2), nullable=False, comment="총 세액")

    # 세율 정보
    applied_tax_rate = Column(Numeric(5, 4), nullable=True, comment="적용 세율")

    # 상세 계산 과정 (JSON)
    calculation_details = Column(JSON, nullable=True, comment="상세 계산 내역")

    # 적용된 규칙들
    applied_rules = Column(JSON, nullable=True, comment="적용된 세법 규칙")

    # 관계
    transaction = relationship("TransactionDB", back_populates="calculation_results")

    def __repr__(self):
        return (
            f"<CalculationResult(id={self.id}, transaction_id={self.transaction_id}, "
            f"total_tax={self.total_tax})>"
        )
