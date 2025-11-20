"""ConflictResolver: 사실관계 충돌 해결"""

from typing import List, Dict, Any
from ..core import Fact


class ConflictResolver:
    """사실관계 충돌을 해결하는 클래스

    같은 필드에 대해 여러 소스에서 서로 다른 값이 들어온 경우,
    우선순위 규칙에 따라 어떤 값을 사용할지 결정합니다.

    우선순위:
    1. user_confirmed (사용자가 확정한 값)
    2. user_input (사용자 직접 입력)
    3. api_* (정부 API 데이터)
    4. ocr_* (문서 OCR 결과)
    5. system_inference (시스템 추론)
    """

    # 소스별 우선순위 (높을수록 우선)
    SOURCE_PRIORITY = {
        'user_confirmed': 100,
        'user_input': 90,
        'api_molit': 80,  # 국토교통부 API
        'api_nts': 80,    # 국세청 API
        'api_': 70,       # 기타 API (prefix 매칭)
        'ocr_contract': 60,
        'ocr_registration': 60,
        'ocr_': 50,       # 기타 OCR (prefix 매칭)
        'system_inference': 10,
    }

    def resolve(self, facts: List[Fact]) -> Fact:
        """여러 Fact 중 하나를 선택

        우선순위 규칙:
        1. is_confirmed=True인 Fact가 있으면 무조건 선택
        2. 소스 우선순위가 높은 것 선택
        3. 같은 우선순위면 confidence가 높은 것 선택
        4. 그래도 같으면 첫 번째 선택

        Args:
            facts: 충돌하는 Fact 리스트

        Returns:
            선택된 Fact

        Raises:
            ValueError: facts가 비어있는 경우
        """
        if not facts:
            raise ValueError("Cannot resolve empty fact list")

        if len(facts) == 1:
            return facts[0]

        # 1. 확정된 Fact가 있으면 선택
        confirmed_facts = [f for f in facts if f.is_confirmed]
        if confirmed_facts:
            # 확정된 것 중 가장 최근 것 선택
            return max(confirmed_facts, key=lambda f: f.created_at)

        # 2. 우선순위와 신뢰도로 정렬
        sorted_facts = sorted(
            facts,
            key=lambda f: (
                self._get_priority(f.source),
                f.confidence,
                f.created_at
            ),
            reverse=True
        )

        return sorted_facts[0]

    def _get_priority(self, source: str) -> int:
        """소스의 우선순위 점수 반환

        Args:
            source: 소스 문자열

        Returns:
            우선순위 점수 (높을수록 우선)
        """
        # 정확히 일치하는 경우
        if source in self.SOURCE_PRIORITY:
            return self.SOURCE_PRIORITY[source]

        # prefix 매칭 (예: api_xxx, ocr_xxx)
        for prefix, priority in self.SOURCE_PRIORITY.items():
            if prefix.endswith('_') and source.startswith(prefix):
                return priority

        # 기본값
        return 0

    def explain_resolution(
        self,
        facts: List[Fact],
        resolved_fact: Fact
    ) -> Dict[str, Any]:
        """충돌 해결 과정 설명

        Args:
            facts: 원본 Fact 리스트
            resolved_fact: 선택된 Fact

        Returns:
            설명 딕셔너리
        """
        return {
            'conflicting_values': [
                {
                    'value': str(f.value),
                    'source': f.source,
                    'confidence': f.confidence,
                    'is_confirmed': f.is_confirmed,
                    'priority': self._get_priority(f.source)
                }
                for f in facts
            ],
            'selected_value': str(resolved_fact.value),
            'selected_source': resolved_fact.source,
            'resolution_reason': self._get_resolution_reason(facts, resolved_fact)
        }

    def _get_resolution_reason(
        self,
        facts: List[Fact],
        resolved_fact: Fact
    ) -> str:
        """해결 이유 설명

        Args:
            facts: 원본 Fact 리스트
            resolved_fact: 선택된 Fact

        Returns:
            이유 설명 문자열
        """
        if resolved_fact.is_confirmed:
            return f"사용자가 확정한 값입니다 (출처: {resolved_fact.source})"

        # 다른 Fact들과 비교
        resolved_priority = self._get_priority(resolved_fact.source)

        has_higher_priority = False
        for f in facts:
            if f is resolved_fact:
                continue
            if self._get_priority(f.source) > resolved_priority:
                has_higher_priority = True
                break

        if not has_higher_priority:
            return f"가장 높은 우선순위 소스입니다 (출처: {resolved_fact.source}, 우선순위: {resolved_priority})"

        # 신뢰도로 선택된 경우
        same_priority_facts = [
            f for f in facts
            if self._get_priority(f.source) == resolved_priority
        ]

        if len(same_priority_facts) > 1:
            max_confidence = max(f.confidence for f in same_priority_facts)
            if resolved_fact.confidence == max_confidence:
                return f"같은 우선순위 중 가장 높은 신뢰도입니다 (출처: {resolved_fact.source}, 신뢰도: {resolved_fact.confidence})"

        return f"선택된 값입니다 (출처: {resolved_fact.source})"

    def detect_conflicts(
        self,
        fact_lists: List[List[tuple]]
    ) -> Dict[str, List[Fact]]:
        """충돌하는 필드 탐지

        Args:
            fact_lists: 각 소스에서 수집된 Fact 리스트들

        Returns:
            필드명: 충돌하는 Fact 리스트 딕셔너리
        """
        # 필드별로 그룹화
        field_facts: Dict[str, List[Fact]] = {}

        for fact_list in fact_lists:
            for field_name, fact in fact_list:
                if field_name not in field_facts:
                    field_facts[field_name] = []
                field_facts[field_name].append(fact)

        # 값이 다른 경우만 충돌로 간주
        conflicts = {}
        for field_name, facts in field_facts.items():
            if len(facts) > 1:
                # 값이 실제로 다른지 확인
                unique_values = set(str(f.value) for f in facts)
                if len(unique_values) > 1:
                    conflicts[field_name] = facts

        return conflicts
