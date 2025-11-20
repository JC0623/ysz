"""FactLedger: 양도소득세 계산을 위한 불변 사실관계 원장"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import uuid4


@dataclass(frozen=True)
class FactLedger:
    """양도소득세 계산을 위한 불변 사실관계 원장

    한 번 생성되면 수정할 수 없는 불변 객체입니다.
    모든 양도소득세 계산은 이 객체를 기반으로 수행됩니다.

    Attributes:
        transaction_id: 거래 고유 식별자 (자동 생성)
        transaction_date: 거래 발생 일자

        # 자산 정보
        asset_type: 자산 유형 (예: '부동산', '주식', '가상자산')
        asset_description: 자산 상세 설명
        acquisition_date: 취득 일자
        acquisition_price: 취득 가액

        # 처분 정보
        disposal_date: 처분 일자
        disposal_price: 처분 가액

        # 비용 정보
        acquisition_cost: 취득 관련 비용 (취득세, 중개수수료 등)
        disposal_cost: 처분 관련 비용 (중개수수료 등)
        improvement_cost: 자본적 지출 (리모델링 등)

        # 거주 정보 (부동산의 경우)
        is_primary_residence: 1세대 1주택 여부
        residence_period_years: 거주 기간(년)

        # 메타데이터
        created_at: 생성 일시
        created_by: 생성자
        version: 버전 (수정 시 새 객체 생성, 버전 증가)
        notes: 추가 메모
    """

    # 거래 기본 정보
    transaction_id: str = field(default_factory=lambda: str(uuid4()))
    transaction_date: date = field(default_factory=date.today)

    # 자산 정보
    asset_type: str = ""
    asset_description: str = ""
    acquisition_date: date = field(default_factory=date.today)
    acquisition_price: Decimal = Decimal("0")

    # 처분 정보
    disposal_date: date = field(default_factory=date.today)
    disposal_price: Decimal = Decimal("0")

    # 비용 정보
    acquisition_cost: Decimal = Decimal("0")
    disposal_cost: Decimal = Decimal("0")
    improvement_cost: Decimal = Decimal("0")

    # 거주 정보 (부동산의 경우)
    is_primary_residence: bool = False
    residence_period_years: int = 0

    # 메타데이터
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = "system"
    version: int = 1
    notes: Optional[str] = None

    def __post_init__(self):
        """데이터 유효성 검증"""
        # 날짜 검증
        if self.disposal_date < self.acquisition_date:
            raise ValueError("처분일은 취득일보다 이전일 수 없습니다")

        if self.transaction_date < self.acquisition_date:
            raise ValueError("거래일은 취득일보다 이전일 수 없습니다")

        # 금액 검증
        if self.acquisition_price < 0:
            raise ValueError("취득가액은 음수일 수 없습니다")

        if self.disposal_price < 0:
            raise ValueError("처분가액은 음수일 수 없습니다")

        if self.acquisition_cost < 0:
            raise ValueError("취득비용은 음수일 수 없습니다")

        if self.disposal_cost < 0:
            raise ValueError("처분비용은 음수일 수 없습니다")

        if self.improvement_cost < 0:
            raise ValueError("자본적지출은 음수일 수 없습니다")

        # 거주기간 검증
        if self.residence_period_years < 0:
            raise ValueError("거주기간은 음수일 수 없습니다")

    @property
    def capital_gain(self) -> Decimal:
        """양도차익 계산

        양도차익 = 처분가액 - (취득가액 + 취득비용 + 처분비용 + 자본적지출)

        Returns:
            계산된 양도차익
        """
        total_cost = (
            self.acquisition_price +
            self.acquisition_cost +
            self.disposal_cost +
            self.improvement_cost
        )
        return self.disposal_price - total_cost

    @property
    def holding_period_years(self) -> int:
        """보유 기간 계산 (년 단위)

        Returns:
            보유 기간(년)
        """
        days = (self.disposal_date - self.acquisition_date).days
        return days // 365

    def create_new_version(self, **changes) -> "FactLedger":
        """수정이 필요한 경우 새로운 버전의 FactLedger 생성

        불변 객체이므로 수정 대신 새 객체를 생성합니다.
        버전은 자동으로 1 증가합니다.

        Args:
            **changes: 변경할 필드와 값

        Returns:
            새로운 FactLedger 객체

        Example:
            >>> fact = FactLedger(asset_type="부동산")
            >>> new_fact = fact.create_new_version(asset_type="주택")
            >>> new_fact.version  # 2
        """
        # 현재 객체의 모든 필드 가져오기
        current_data = {
            field_name: getattr(self, field_name)
            for field_name in self.__dataclass_fields__
        }

        # 변경사항 적용
        current_data.update(changes)

        # 버전 증가
        current_data['version'] = self.version + 1

        # 생성 시간 업데이트
        current_data['created_at'] = datetime.now()

        return FactLedger(**current_data)

    def to_dict(self) -> dict:
        """딕셔너리로 변환 (직렬화용)

        Returns:
            객체의 모든 필드를 담은 딕셔너리
        """
        return {
            'transaction_id': self.transaction_id,
            'transaction_date': self.transaction_date.isoformat(),
            'asset_type': self.asset_type,
            'asset_description': self.asset_description,
            'acquisition_date': self.acquisition_date.isoformat(),
            'acquisition_price': str(self.acquisition_price),
            'disposal_date': self.disposal_date.isoformat(),
            'disposal_price': str(self.disposal_price),
            'acquisition_cost': str(self.acquisition_cost),
            'disposal_cost': str(self.disposal_cost),
            'improvement_cost': str(self.improvement_cost),
            'is_primary_residence': self.is_primary_residence,
            'residence_period_years': self.residence_period_years,
            'created_at': self.created_at.isoformat(),
            'created_by': self.created_by,
            'version': self.version,
            'notes': self.notes,
        }

    def __str__(self) -> str:
        """사람이 읽기 쉬운 형태로 출력"""
        return (
            f"FactLedger(id={self.transaction_id[:8]}..., "
            f"asset={self.asset_type}, "
            f"acquired={self.acquisition_date}, "
            f"disposed={self.disposal_date}, "
            f"gain={self.capital_gain:,.0f}원)"
        )
