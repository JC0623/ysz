"""FactCollector: 여러 소스에서 사실관계 수집"""

from typing import Dict, List, Any, Optional
from datetime import date
from decimal import Decimal

from ..core import Fact, FactLedger
from .conflict_resolver import ConflictResolver


class FactCollector:
    """여러 소스에서 사실관계를 수집하고 병합하는 클래스

    사용자 입력, API 응답, OCR 결과 등 다양한 소스에서
    사실관계를 수집하고 충돌을 해결하여 FactLedger를 생성합니다.

    Attributes:
        conflict_resolver: 사실관계 충돌 해결기
    """

    def __init__(self):
        """FactCollector 초기화"""
        self.conflict_resolver = ConflictResolver()

    async def collect_from_user_input(
        self,
        user_data: Dict[str, Any],
        entered_by: str = "user"
    ) -> List[Fact]:
        """사용자 직접 입력에서 사실관계 수집

        Args:
            user_data: 사용자가 입력한 데이터 딕셔너리
            entered_by: 입력자 정보

        Returns:
            Fact 객체 리스트

        Example:
            >>> collector = FactCollector()
            >>> user_data = {
            ...     "acquisition_date": "2020-05-01",
            ...     "acquisition_price": 500000000,
            ...     "disposal_date": "2025-10-20",
            ...     "disposal_price": 800000000
            ... }
            >>> facts = await collector.collect_from_user_input(user_data)
        """
        # 계산되는 필드들은 제외 (FactLedger의 @property 메서드로 계산됨)
        computed_fields = {'holding_period_years', 'capital_gain'}

        facts = []

        # 각 필드를 Fact 객체로 변환
        for field_name, value in user_data.items():
            if value is None:
                continue

            # 계산 필드는 건너뛰기
            if field_name in computed_fields:
                continue

            # 타입별 변환
            converted_value = self._convert_value(field_name, value)

            fact = Fact(
                value=converted_value,
                source="user_input",
                confidence=1.0,  # 사용자 입력은 높은 신뢰도
                is_confirmed=False,  # 아직 확정되지 않음
                entered_by=entered_by
            )

            facts.append((field_name, fact))

        return facts

    async def collect_from_api(
        self,
        api_name: str,
        api_data: Dict[str, Any]
    ) -> List[Fact]:
        """정부 API에서 사실관계 수집 (향후 구현)

        Args:
            api_name: API 이름 (예: "molit", "nts")
            api_data: API 응답 데이터

        Returns:
            Fact 객체 리스트
        """
        # TODO: 실제 API 통합 시 구현
        facts = []

        for field_name, value in api_data.items():
            if value is None:
                continue

            converted_value = self._convert_value(field_name, value)

            fact = Fact(
                value=converted_value,
                source=f"api_{api_name}",
                confidence=0.9,  # API 데이터는 사용자 입력보다 약간 낮은 신뢰도
                is_confirmed=False,
                metadata={"api_name": api_name}
            )

            facts.append((field_name, fact))

        return facts

    async def collect_from_ocr(
        self,
        document_type: str,
        ocr_result: Dict[str, Any]
    ) -> List[Fact]:
        """문서 OCR 처리 결과에서 사실관계 수집 (향후 구현)

        Args:
            document_type: 문서 유형 (예: "contract", "registration")
            ocr_result: OCR 처리 결과

        Returns:
            Fact 객체 리스트
        """
        # TODO: OCR 통합 시 구현
        facts = []

        for field_name, value in ocr_result.items():
            if value is None:
                continue

            # OCR 신뢰도가 포함되어 있을 수 있음
            confidence = value.get('confidence', 0.7) if isinstance(value, dict) else 0.7
            actual_value = value.get('value', value) if isinstance(value, dict) else value

            converted_value = self._convert_value(field_name, actual_value)

            fact = Fact(
                value=converted_value,
                source=f"ocr_{document_type}",
                confidence=confidence,
                is_confirmed=False,
                metadata={"document_type": document_type}
            )

            facts.append((field_name, fact))

        return facts

    async def merge_facts(
        self,
        fact_lists: List[List[tuple]],
        created_by: str = "system"
    ) -> FactLedger:
        """수집된 사실들을 병합하고 충돌 해결

        여러 소스에서 수집된 사실들을 병합하고,
        같은 필드에 대해 서로 다른 값이 있는 경우 충돌을 해결합니다.

        Args:
            fact_lists: 각 소스에서 수집된 Fact 리스트들
            created_by: FactLedger 생성자

        Returns:
            병합된 FactLedger

        Example:
            >>> user_facts = await collector.collect_from_user_input(user_data)
            >>> api_facts = await collector.collect_from_api("molit", api_data)
            >>> ledger = await collector.merge_facts([user_facts, api_facts])
        """
        # 필드별로 Fact들을 그룹화
        field_facts: Dict[str, List[Fact]] = {}

        for fact_list in fact_lists:
            for field_name, fact in fact_list:
                if field_name not in field_facts:
                    field_facts[field_name] = []
                field_facts[field_name].append(fact)

        # 각 필드별로 충돌 해결
        resolved_facts = {}
        for field_name, facts in field_facts.items():
            if len(facts) == 1:
                # 충돌 없음
                resolved_facts[field_name] = facts[0]
            else:
                # 충돌 해결
                resolved_fact = self.conflict_resolver.resolve(facts)
                resolved_facts[field_name] = resolved_fact

        # FactLedger 생성
        ledger = FactLedger.create(resolved_facts, created_by=created_by)

        return ledger

    def _convert_value(self, field_name: str, value: Any) -> Any:
        """필드 타입에 맞게 값 변환

        Args:
            field_name: 필드명
            value: 변환할 값

        Returns:
            변환된 값
        """
        # 날짜 필드
        if 'date' in field_name.lower():
            if isinstance(value, str):
                # ISO 형식 날짜 파싱
                parts = value.split('-')
                if len(parts) == 3:
                    return date(int(parts[0]), int(parts[1]), int(parts[2]))
            elif isinstance(value, date):
                return value
            else:
                raise ValueError(f"Invalid date format for {field_name}: {value}")

        # 금액 필드
        if 'price' in field_name.lower() or 'cost' in field_name.lower():
            if isinstance(value, (int, float)):
                return Decimal(str(value))
            elif isinstance(value, str):
                # 쉼표 제거 후 변환
                cleaned = value.replace(',', '').replace('원', '').strip()
                return Decimal(cleaned)
            elif isinstance(value, Decimal):
                return value
            else:
                raise ValueError(f"Invalid price format for {field_name}: {value}")

        # 기간 필드 (년 단위)
        if 'period_years' in field_name.lower():
            return int(value)

        # 주택 수 필드
        if 'house_count' in field_name.lower():
            return int(value)

        # 불린 필드
        if isinstance(value, bool):
            return value
        if field_name in ['is_primary_residence', 'is_adjusted_area']:
            if isinstance(value, str):
                return value.lower() in ('true', 'yes', '1', 'y')
            return bool(value)

        # 문자열 필드
        if isinstance(value, str):
            return value.strip()

        return value

    def get_missing_facts(
        self,
        ledger: FactLedger,
        required_fields: Optional[List[str]] = None
    ) -> List[str]:
        """부족한 사실관계 확인

        Args:
            ledger: 검사할 FactLedger
            required_fields: 필수 필드 리스트 (None이면 기본 필수 필드 사용)

        Returns:
            누락된 필드명 리스트
        """
        if required_fields is None:
            # 기본 필수 필드
            required_fields = [
                'acquisition_date',
                'acquisition_price',
                'disposal_date',
                'disposal_price',
                'asset_type'
            ]

        missing = []
        for field_name in required_fields:
            fact = getattr(ledger, field_name, None)
            if fact is None:
                missing.append(field_name)

        return missing

    def get_unconfirmed_facts(
        self,
        ledger: FactLedger
    ) -> List[str]:
        """확정되지 않은 사실관계 확인

        Args:
            ledger: 검사할 FactLedger

        Returns:
            확정되지 않은 필드명 리스트
        """
        return ledger.get_unconfirmed_fields()
