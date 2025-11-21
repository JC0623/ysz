"""계산 검증 에이전트 (Calculation Verification Agent)

세액 계산 결과를 검증하고 리스크를 분석합니다.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, date
from decimal import Decimal


class CalculationVerificationAgent:
    """계산 검증 에이전트

    역할:
    - 계산 로직 검증
    - 착오류 통계 분석
    - 유사 사례 비교
    - 리스크 플래그 식별
    """

    def __init__(self, mock_mode: bool = True):
        """
        Args:
            mock_mode: True면 mock 모드
        """
        self.mock_mode = mock_mode

    async def verify(
        self,
        facts: Dict[str, Any],
        tax_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """계산 검증

        검증 항목:
        1. 기본 논리 검증 (양도차익 = 양도가액 - 취득가액)
        2. 세율 적용 검증
        3. 공제 한도 검증
        4. 착오류 체크 (통계 기반)
        5. 유사 사례 비교
        6. 리스크 플래그

        Args:
            facts: 사실관계 정보
            tax_result: 계산 결과

        Returns:
            {
                "status": "verified" | "warning" | "error",
                "message": "검증 완료",
                "checks": [
                    {"name": "기본 논리", "status": "pass", "message": "OK"},
                    ...
                ],
                "risk_flags": [
                    {
                        "level": "high" | "medium" | "low",
                        "title": "고액 양도차익",
                        "description": "양도차익이 5억 이상입니다...",
                        "recommendation": "세무사 상담 권장"
                    },
                    ...
                ],
                "similar_cases": [
                    {"case_id": "C123", "similarity": 0.95, "tax_difference": 5000000},
                    ...
                ]
            }
        """
        print(f"[Verification] Verifying calculation...")

        checks = []
        risk_flags = []

        # 1. 기본 논리 검증
        logic_check = self._verify_basic_logic(facts, tax_result)
        checks.append(logic_check)

        # 2. 세율 적용 검증
        tax_rate_check = self._verify_tax_rate(tax_result)
        checks.append(tax_rate_check)

        # 3. 공제 한도 검증
        deduction_check = self._verify_deductions(tax_result)
        checks.append(deduction_check)

        # 4. 리스크 플래그 식별
        risk_flags.extend(self._identify_risk_flags(facts, tax_result))

        # 5. 유사 사례 비교
        similar_cases = await self._compare_similar_cases(facts, tax_result)

        # 전체 상태 판단
        fail_count = sum(1 for c in checks if c['status'] == 'fail')
        warning_count = sum(1 for c in checks if c['status'] == 'warning')

        if fail_count > 0:
            status = "error"
            message = f"검증 실패: {fail_count}개 항목"
        elif warning_count > 0:
            status = "warning"
            message = f"경고: {warning_count}개 항목"
        else:
            status = "verified"
            message = "검증 완료"

        print(f"[Verification] Status: {status}, Risk flags: {len(risk_flags)}")

        return {
            "status": status,
            "message": message,
            "checks": checks,
            "risk_flags": risk_flags,
            "similar_cases": similar_cases,
            "verified_at": datetime.now().isoformat()
        }

    def _verify_basic_logic(
        self,
        facts: Dict[str, Any],
        tax_result: Dict[str, Any]
    ) -> Dict[str, str]:
        """기본 논리 검증

        - 양도차익 = 양도가액 - 취득가액
        - 과세표준 <= 양도차익
        - 산출세액 <= 과세표준
        """
        disposal_price = tax_result.get('disposal_price', 0)
        acquisition_price = tax_result.get('acquisition_price', 0)
        capital_gain = tax_result.get('capital_gain', 0)
        taxable_income = tax_result.get('taxable_income', 0)
        calculated_tax = tax_result.get('calculated_tax', 0)

        # 양도차익 검증
        expected_gain = disposal_price - acquisition_price
        if abs(capital_gain - expected_gain) > 1:  # 1원 이내 오차 허용
            return {
                "name": "기본 논리 검증",
                "status": "fail",
                "message": f"양도차익 계산 오류: {capital_gain:,} != {expected_gain:,}"
            }

        # 과세표준 검증
        if taxable_income > capital_gain:
            return {
                "name": "기본 논리 검증",
                "status": "fail",
                "message": f"과세표준이 양도차익보다 큼: {taxable_income:,} > {capital_gain:,}"
            }

        # 산출세액 검증
        if calculated_tax > taxable_income:
            return {
                "name": "기본 논리 검증",
                "status": "fail",
                "message": f"산출세액이 과세표준보다 큼: {calculated_tax:,} > {taxable_income:,}"
            }

        return {
            "name": "기본 논리 검증",
            "status": "pass",
            "message": "양도차익, 과세표준, 산출세액 계산 정상"
        }

    def _verify_tax_rate(self, tax_result: Dict[str, Any]) -> Dict[str, str]:
        """세율 적용 검증

        양도소득세 누진세율:
        - 1,200만원 이하: 6%
        - 4,600만원 이하: 15%
        - 8,800만원 이하: 24%
        - 1.5억원 이하: 35%
        - 3억원 이하: 38%
        - 5억원 이하: 40%
        - 10억원 이하: 42%
        - 10억원 초과: 45%
        """
        taxable_income = tax_result.get('taxable_income', 0)
        applied_rate = tax_result.get('applied_tax_rate', 0)

        # 예상 세율 범위 확인
        if taxable_income <= 12_000_000:
            expected_rate_range = (0.06, 0.06)
        elif taxable_income <= 46_000_000:
            expected_rate_range = (0.06, 0.15)
        elif taxable_income <= 88_000_000:
            expected_rate_range = (0.06, 0.24)
        elif taxable_income <= 150_000_000:
            expected_rate_range = (0.06, 0.35)
        elif taxable_income <= 300_000_000:
            expected_rate_range = (0.06, 0.38)
        elif taxable_income <= 500_000_000:
            expected_rate_range = (0.06, 0.40)
        elif taxable_income <= 1_000_000_000:
            expected_rate_range = (0.06, 0.42)
        else:
            expected_rate_range = (0.06, 0.45)

        min_rate, max_rate = expected_rate_range

        if applied_rate < min_rate or applied_rate > max_rate:
            return {
                "name": "세율 적용 검증",
                "status": "warning",
                "message": f"적용 세율 {applied_rate*100:.1f}%가 예상 범위({min_rate*100:.1f}~{max_rate*100:.1f}%)를 벗어남"
            }

        return {
            "name": "세율 적용 검증",
            "status": "pass",
            "message": f"적용 세율 {applied_rate*100:.1f}% 정상"
        }

    def _verify_deductions(self, tax_result: Dict[str, Any]) -> Dict[str, str]:
        """공제 한도 검증

        - 장기보유특별공제: 최대 30%
        - 기본공제: 250만원
        """
        capital_gain = tax_result.get('capital_gain', 0)
        long_term_deduction = tax_result.get('long_term_deduction', 0)
        basic_deduction = tax_result.get('basic_deduction', 0)

        # 장기보유특별공제 한도 (최대 30%)
        if capital_gain > 0:
            long_term_ratio = long_term_deduction / capital_gain
            if long_term_ratio > 0.30:
                return {
                    "name": "공제 한도 검증",
                    "status": "warning",
                    "message": f"장기보유특별공제 비율 {long_term_ratio*100:.1f}%가 한도(30%)를 초과"
                }

        # 기본공제 한도 (250만원)
        if basic_deduction > 2_500_000:
            return {
                "name": "공제 한도 검증",
                "status": "warning",
                "message": f"기본공제 {basic_deduction:,}원이 한도(2,500,000원)를 초과"
            }

        return {
            "name": "공제 한도 검증",
            "status": "pass",
            "message": "공제 한도 정상"
        }

    def _identify_risk_flags(
        self,
        facts: Dict[str, Any],
        tax_result: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """리스크 플래그 식별

        Returns:
            [
                {
                    "level": "high" | "medium" | "low",
                    "title": "리스크 제목",
                    "description": "상세 설명",
                    "recommendation": "권장 사항"
                },
                ...
            ]
        """
        flags = []

        capital_gain = tax_result.get('capital_gain', 0)
        total_tax = tax_result.get('total_tax', 0)
        disposal_price = tax_result.get('disposal_price', 0)
        is_primary = facts.get('is_primary_residence', False)

        # 1. 고액 양도차익
        if capital_gain >= 500_000_000:
            flags.append({
                "level": "high",
                "title": "고액 양도차익",
                "description": f"양도차익이 {capital_gain:,}원으로 5억 이상입니다. 세무조사 대상이 될 가능성이 있습니다.",
                "recommendation": "세무사 상담을 권장합니다."
            })

        # 2. 높은 세율
        applied_rate = tax_result.get('applied_tax_rate', 0)
        if applied_rate >= 0.40:
            flags.append({
                "level": "medium",
                "title": "높은 세율 적용",
                "description": f"최고세율({applied_rate*100:.1f}%)이 적용되었습니다.",
                "recommendation": "절세 전략 검토를 권장합니다."
            })

        # 3. 1세대1주택 비해당
        if not is_primary and disposal_price >= 900_000_000:
            flags.append({
                "level": "medium",
                "title": "1세대1주택 비과세 미적용",
                "description": "9억 이상 고가 주택이지만 1세대1주택 비과세가 적용되지 않았습니다.",
                "recommendation": "1세대1주택 요건 충족 여부를 재확인하세요."
            })

        # 4. 조정대상지역
        if facts.get('is_adjusted_area', False):
            flags.append({
                "level": "low",
                "title": "조정대상지역",
                "description": "조정대상지역의 주택입니다. 중과세율이 적용될 수 있습니다.",
                "recommendation": "중과세율 적용 여부를 확인하세요."
            })

        # 5. 신고 기한 임박 (예시)
        # TODO: 실제 신고 기한 계산
        disposal_date_str = facts.get('disposal_date', '')
        if disposal_date_str:
            # 양도일로부터 2개월 이내 신고
            pass

        return flags

    async def _compare_similar_cases(
        self,
        facts: Dict[str, Any],
        tax_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """유사 사례 비교

        데이터베이스에서 유사한 케이스를 검색하여 비교합니다.

        Returns:
            [
                {
                    "case_id": "C2024-0123",
                    "similarity": 0.95,
                    "tax_difference": 5000000,
                    "summary": "서울 강남구, 10억 양도, 5년 보유"
                },
                ...
            ]
        """
        if self.mock_mode:
            # Mock: 유사 사례 없음
            return []

        # TODO: 실제 데이터베이스 검색
        # - 벡터 유사도 검색
        # - 양도가액, 보유기간, 지역 등 유사도 계산
        return []
