"""FactLedger: 양도소득세 계산을 위한 불변 사실관계 원장"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Dict, Any, Union
from uuid import uuid4

from .fact import Fact


@dataclass
class FactLedger:
    """양도소득세 계산을 위한 사실관계 원장

    모든 필드는 Fact 객체로 래핑되어 추적 가능성을 보장합니다.
    freeze() 메서드로 확정하기 전까지는 수정 가능합니다.

    Attributes:
        transaction_id: 거래 고유 식별자
        transaction_date: 거래 발생 일자

        # 자산 정보
        asset_type: 자산 유형
        asset_description: 자산 상세 설명
        acquisition_date: 취득 일자
        acquisition_price: 취득 가액

        # 처분 정보
        disposal_date: 처분 일자
        disposal_price: 처분 가액

        # 비용 정보
        acquisition_cost: 취득 관련 비용
        disposal_cost: 처분 관련 비용
        improvement_cost: 자본적 지출

        # 거주 정보
        is_primary_residence: 1세대 1주택 여부
        residence_period_years: 거주 기간

        # 메타데이터
        created_at: 생성 일시
        created_by: 생성자
        version: 버전
        notes: 추가 메모
        is_frozen: 확정 여부
    """

    # 거래 기본 정보
    transaction_id: str = field(default_factory=lambda: str(uuid4()))
    transaction_date: Optional[Fact[date]] = None

    # 자산 정보
    asset_type: Optional[Fact[str]] = None
    asset_description: Optional[Fact[str]] = None
    acquisition_date: Optional[Fact[date]] = None
    acquisition_price: Optional[Fact[Decimal]] = None

    # 처분 정보
    disposal_date: Optional[Fact[date]] = None
    disposal_price: Optional[Fact[Decimal]] = None

    # 비용 정보
    acquisition_cost: Optional[Fact[Decimal]] = None
    disposal_cost: Optional[Fact[Decimal]] = None
    improvement_cost: Optional[Fact[Decimal]] = None

    # 거주 정보
    is_primary_residence: Optional[Fact[bool]] = None
    residence_period_years: Optional[Fact[int]] = None

    # 다주택 정보
    house_count: Optional[Fact[int]] = None  # 보유 주택 수 (중과세 판단용)

    # 메타데이터
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = "system"
    version: int = 1
    notes: Optional[str] = None
    is_frozen: bool = False

    @classmethod
    def create(cls, facts: Dict[str, Union[Fact, Any]], created_by: str = "system") -> "FactLedger":
        """FactLedger 생성

        딕셔너리에서 FactLedger를 생성합니다.
        Fact 객체가 아닌 값은 자동으로 Fact로 래핑됩니다.

        Args:
            facts: 필드명과 값(또는 Fact 객체)의 딕셔너리
            created_by: 생성자

        Returns:
            생성된 FactLedger 객체

        Example:
            >>> ledger = FactLedger.create({
            ...     "acquisition_date": Fact(
            ...         value=date(2020, 1, 1),
            ...         source="user_input",
            ...         is_confirmed=True
            ...     ),
            ...     "disposal_price": Decimal("700000000")  # 자동으로 Fact 래핑
            ... }, created_by="김세무사")
        """
        wrapped_facts = {}

        for key, value in facts.items():
            if isinstance(value, Fact):
                wrapped_facts[key] = value
            else:
                # 자동으로 Fact 래핑 (사용자 입력으로 간주)
                wrapped_facts[key] = Fact(
                    value=value,
                    source="user_input",
                    confidence=0.9,
                    is_confirmed=False,
                    entered_by=created_by
                )

        return cls(**wrapped_facts, created_by=created_by)

    def freeze(self) -> "FactLedger":
        """사실관계 확정

        모든 필드가 확정되었는지 검증하고, 원장을 불변 상태로 만듭니다.
        확정 후에는 수정할 수 없습니다.

        Returns:
            self (메서드 체이닝용)

        Raises:
            ValueError: 필수 필드가 확정되지 않았거나, 이미 확정된 경우
        """
        if self.is_frozen:
            raise ValueError("이미 확정된 FactLedger입니다")

        # 필수 필드 확정 여부 확인
        required_fields = [
            'acquisition_date', 'acquisition_price',
            'disposal_date', 'disposal_price'
        ]

        for field_name in required_fields:
            fact = getattr(self, field_name)
            if fact is None:
                raise ValueError(f"필수 필드 '{field_name}'가 설정되지 않았습니다")
            if not fact.is_confirmed:
                raise ValueError(
                    f"필드 '{field_name}'가 확정되지 않았습니다 "
                    f"(confidence={fact.confidence}, is_confirmed={fact.is_confirmed})"
                )

        # 데이터 유효성 검증
        self._validate()

        # 확정 처리
        object.__setattr__(self, 'is_frozen', True)
        return self

    def _validate(self):
        """데이터 유효성 검증"""
        # 날짜 검증
        if self.disposal_date and self.acquisition_date:
            if self.disposal_date.value < self.acquisition_date.value:
                raise ValueError("처분일은 취득일보다 이전일 수 없습니다")

        # 금액 검증
        if self.acquisition_price and self.acquisition_price.value < 0:
            raise ValueError("취득가액은 음수일 수 없습니다")

        if self.disposal_price and self.disposal_price.value < 0:
            raise ValueError("처분가액은 음수일 수 없습니다")

        # 비용 검증
        for field_name in ['acquisition_cost', 'disposal_cost', 'improvement_cost']:
            fact = getattr(self, field_name)
            if fact and fact.value < 0:
                raise ValueError(f"{field_name}는 음수일 수 없습니다")

        # 거주기간 검증
        if self.residence_period_years and self.residence_period_years.value < 0:
            raise ValueError("거주기간은 음수일 수 없습니다")

    def update_field(self, field_name: str, fact: Fact) -> None:
        """필드 업데이트

        Args:
            field_name: 필드명
            fact: 새로운 Fact 객체

        Raises:
            ValueError: 이미 확정된 경우
            AttributeError: 존재하지 않는 필드
        """
        if self.is_frozen:
            raise ValueError("확정된 FactLedger는 수정할 수 없습니다")

        if not hasattr(self, field_name):
            raise AttributeError(f"'{field_name}' 필드가 존재하지 않습니다")

        setattr(self, field_name, fact)

    @property
    def capital_gain(self) -> Optional[Decimal]:
        """양도차익 계산

        양도차익 = 처분가액 - (취득가액 + 취득비용 + 처분비용 + 자본적지출)

        Returns:
            계산된 양도차익 (필수 필드가 없으면 None)
        """
        if not self.disposal_price or not self.acquisition_price:
            return None

        total_cost = self.acquisition_price.value

        if self.acquisition_cost:
            total_cost += self.acquisition_cost.value
        if self.disposal_cost:
            total_cost += self.disposal_cost.value
        if self.improvement_cost:
            total_cost += self.improvement_cost.value

        return self.disposal_price.value - total_cost

    @property
    def holding_period_years(self) -> Optional[int]:
        """보유 기간 계산 (년 단위)

        Returns:
            보유 기간(년), 필수 필드가 없으면 None
        """
        if not self.acquisition_date or not self.disposal_date:
            return None

        days = (self.disposal_date.value - self.acquisition_date.value).days
        return days // 365

    def get_confidence_summary(self) -> Dict[str, float]:
        """모든 필드의 신뢰도 요약

        Returns:
            필드명: 신뢰도 딕셔너리
        """
        summary = {}
        for field_name in self.__dataclass_fields__:
            if field_name.startswith('_') or field_name in ['transaction_id', 'created_at', 'created_by', 'version', 'notes', 'is_frozen']:
                continue

            fact = getattr(self, field_name)
            if isinstance(fact, Fact):
                summary[field_name] = fact.confidence

        return summary

    def get_unconfirmed_fields(self) -> list[str]:
        """확정되지 않은 필드 목록

        Returns:
            확정되지 않은 필드명 리스트
        """
        unconfirmed = []
        for field_name in self.__dataclass_fields__:
            if field_name.startswith('_') or field_name in ['transaction_id', 'created_at', 'created_by', 'version', 'notes', 'is_frozen']:
                continue

            fact = getattr(self, field_name)
            if isinstance(fact, Fact) and not fact.is_confirmed:
                unconfirmed.append(field_name)

        return unconfirmed

    def create_new_version(self, **changes) -> "FactLedger":
        """새 버전 생성

        확정되지 않은 FactLedger만 새 버전을 생성할 수 있습니다.

        Args:
            **changes: 변경할 필드와 Fact 객체

        Returns:
            새로운 버전의 FactLedger

        Raises:
            ValueError: 이미 확정된 경우
        """
        if self.is_frozen:
            raise ValueError("확정된 FactLedger는 새 버전을 만들 수 없습니다")

        # 현재 객체의 모든 필드 복사
        current_data = {}
        for field_name in self.__dataclass_fields__:
            current_data[field_name] = getattr(self, field_name)

        # 변경사항 적용
        current_data.update(changes)

        # 버전 증가
        current_data['version'] = self.version + 1
        current_data['created_at'] = datetime.now()

        return FactLedger(**current_data)

    def to_dict(self) -> dict:
        """딕셔너리로 변환

        Returns:
            모든 필드를 담은 딕셔너리
        """
        result = {
            'transaction_id': self.transaction_id,
            'created_at': self.created_at.isoformat(),
            'created_by': self.created_by,
            'version': self.version,
            'notes': self.notes,
            'is_frozen': self.is_frozen,
        }

        # Fact 필드들 직렬화
        for field_name in self.__dataclass_fields__:
            if field_name in ['transaction_id', 'created_at', 'created_by', 'version', 'notes', 'is_frozen']:
                continue

            fact = getattr(self, field_name)
            if isinstance(fact, Fact):
                result[field_name] = fact.to_dict()
            else:
                result[field_name] = None

        return result

    def __str__(self) -> str:
        """사람이 읽기 쉬운 형태로 출력"""
        status = "확정" if self.is_frozen else "작성중"
        gain = self.capital_gain
        gain_str = f"{gain:,.0f}원" if gain is not None else "미계산"

        return (
            f"FactLedger(id={self.transaction_id[:8]}..., "
            f"status={status}, "
            f"gain={gain_str})"
        )
