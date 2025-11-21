"""신고 에이전트 (Filing Agent)

양도소득세 신고서를 작성하고 납부를 안내합니다.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal


class FilingAgent:
    """신고 에이전트

    역할:
    - 신고서 작성
    - 납부 안내
    - 증빙 서류 관리
    - 신고 기한 계산
    """

    def __init__(self, mock_mode: bool = True):
        """
        Args:
            mock_mode: True면 mock 모드
        """
        self.mock_mode = mock_mode

    async def prepare_filing(
        self,
        facts: Dict[str, Any],
        tax_result: Dict[str, Any],
        verification: Dict[str, Any]
    ) -> Dict[str, Any]:
        """신고 패키지 준비

        Args:
            facts: 사실관계 정보
            tax_result: 세액 계산 결과
            verification: 검증 결과

        Returns:
            {
                "status": "ready" | "incomplete" | "error",
                "message": "신고 준비 완료",
                "filing_form": {...},
                "deadline": "2025-02-28",
                "payment_info": {...},
                "required_documents": [...],
                "filing_instructions": "..."
            }
        """
        print(f"[Filing] Preparing filing package...")

        # 1. 신고서 작성
        filing_form = self._generate_filing_form(facts, tax_result)

        # 2. 신고 기한 계산
        deadline = self._calculate_deadline(facts.get('disposal_date'))

        # 3. 납부 정보
        payment_info = self._generate_payment_info(tax_result, deadline)

        # 4. 필요 서류 목록
        required_docs = self._list_required_documents(facts, tax_result)

        # 5. 신고 안내
        instructions = self._generate_filing_instructions(
            facts=facts,
            tax_result=tax_result,
            deadline=deadline
        )

        # 상태 판단
        if verification.get('status') == 'error':
            status = "incomplete"
            message = "검증 오류로 인해 신고서 작성이 완료되지 않았습니다."
        elif verification.get('status') == 'warning':
            status = "ready"
            message = "신고서가 준비되었으나 경고 사항을 확인하세요."
        else:
            status = "ready"
            message = "신고서 준비가 완료되었습니다."

        print(f"[Filing] Status: {status}, Deadline: {deadline}")

        return {
            "status": status,
            "message": message,
            "filing_form": filing_form,
            "deadline": deadline,
            "payment_info": payment_info,
            "required_documents": required_docs,
            "filing_instructions": instructions,
            "prepared_at": datetime.now().isoformat()
        }

    def _generate_filing_form(
        self,
        facts: Dict[str, Any],
        tax_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """양도소득세 신고서 작성

        국세청 양도소득세 신고서 양식:
        - 일반양도소득세 확정신고서 (별지 제84호 서식)
        """
        return {
            "form_type": "양도소득세 확정신고서",
            "form_code": "별지 제84호 서식",
            "taxpayer": {
                # TODO: 납세자 정보 (사용자 프로필에서 가져오기)
                "name": "",
                "resident_number": "",
                "address": facts.get('address', '')
            },
            "asset_info": {
                "asset_type": facts.get('asset_type', ''),
                "address": facts.get('address', ''),
                "acquisition_date": facts.get('acquisition_date', ''),
                "disposal_date": facts.get('disposal_date', '')
            },
            "calculation": {
                "disposal_price": tax_result.get('disposal_price', 0),
                "acquisition_price": tax_result.get('acquisition_price', 0),
                "necessary_expenses": tax_result.get('necessary_expenses', 0),
                "capital_gain": tax_result.get('capital_gain', 0),
                "long_term_deduction": tax_result.get('long_term_deduction', 0),
                "basic_deduction": tax_result.get('basic_deduction', 0),
                "taxable_income": tax_result.get('taxable_income', 0),
                "calculated_tax": tax_result.get('calculated_tax', 0),
                "local_tax": tax_result.get('local_tax', 0),
                "total_tax": tax_result.get('total_tax', 0)
            },
            "exemptions": {
                "is_primary_residence": facts.get('is_primary_residence', False),
                # TODO: 기타 감면 사항
            }
        }

    def _calculate_deadline(self, disposal_date: Any) -> str:
        """신고 기한 계산

        양도소득세 신고 기한:
        - 양도일이 속하는 달의 말일로부터 2개월 이내

        예:
        - 양도일: 2024-12-20
        - 신고 기한: 2025-02-28 (2024년 12월 말일 + 2개월)
        """
        if isinstance(disposal_date, str):
            from datetime import datetime as dt
            disposal_date = dt.strptime(disposal_date, "%Y-%m-%d").date()

        # 양도월의 말일
        if disposal_date.month == 12:
            month_end = disposal_date.replace(day=31)
        else:
            next_month = disposal_date.replace(month=disposal_date.month + 1, day=1)
            month_end = next_month - timedelta(days=1)

        # 말일로부터 2개월 후
        if month_end.month == 10:
            # 10월 -> 12월
            deadline = month_end.replace(month=12, day=31)
        elif month_end.month == 11:
            # 11월 -> 1월 (다음해)
            deadline = month_end.replace(year=month_end.year + 1, month=1, day=31)
        elif month_end.month == 12:
            # 12월 -> 2월 (다음해)
            # 2월 말일 계산
            year = month_end.year + 1
            if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0):
                deadline = month_end.replace(year=year, month=2, day=29)
            else:
                deadline = month_end.replace(year=year, month=2, day=28)
        else:
            # 일반적인 경우
            deadline_month = month_end.month + 2
            deadline = month_end.replace(month=deadline_month)

            # 해당 월의 말일로 설정
            if deadline_month in [1, 3, 5, 7, 8, 10, 12]:
                deadline = deadline.replace(day=31)
            elif deadline_month in [4, 6, 9, 11]:
                deadline = deadline.replace(day=30)
            elif deadline_month == 2:
                if deadline.year % 4 == 0 and (deadline.year % 100 != 0 or deadline.year % 400 == 0):
                    deadline = deadline.replace(day=29)
                else:
                    deadline = deadline.replace(day=28)

        return deadline.isoformat()

    def _generate_payment_info(
        self,
        tax_result: Dict[str, Any],
        deadline: str
    ) -> Dict[str, Any]:
        """납부 정보 생성

        Returns:
            {
                "total_amount": 136125000,
                "calculated_tax": 123750000,
                "local_tax": 12375000,
                "deadline": "2025-02-28",
                "payment_methods": [
                    "홈택스 전자납부",
                    "은행 방문 납부",
                    "가상계좌 납부"
                ],
                "account_info": {...}
            }
        """
        return {
            "total_amount": tax_result.get('total_tax', 0),
            "calculated_tax": tax_result.get('calculated_tax', 0),
            "local_tax": tax_result.get('local_tax', 0),
            "deadline": deadline,
            "payment_methods": [
                "홈택스 전자납부 (www.hometax.go.kr)",
                "은행 방문 납부 (국세청 고지서 지참)",
                "가상계좌 납부 (홈택스에서 발급)"
            ],
            "installment_available": tax_result.get('total_tax', 0) >= 10_000_000,
            "installment_info": "납부세액 1,000만원 이상 시 분할납부 가능 (최대 6개월)"
        }

    def _list_required_documents(
        self,
        facts: Dict[str, Any],
        tax_result: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """필요 서류 목록

        Returns:
            [
                {
                    "name": "매매계약서",
                    "description": "양도 당시 매매계약서 원본 또는 사본",
                    "required": True
                },
                ...
            ]
        """
        docs = [
            {
                "name": "양도소득세 확정신고서",
                "description": "국세청 별지 제84호 서식",
                "required": True
            },
            {
                "name": "매매계약서",
                "description": "양도 당시 매매계약서 원본 또는 사본",
                "required": True
            },
            {
                "name": "등기부등본",
                "description": "양도 대상 부동산의 등기부등본",
                "required": True
            },
            {
                "name": "취득 당시 계약서",
                "description": "취득 당시 매매계약서 원본 또는 사본",
                "required": True
            },
            {
                "name": "필요경비 증빙",
                "description": "중개수수료, 취득세 영수증 등",
                "required": False
            }
        ]

        # 1세대1주택 비과세 신청 시
        if facts.get('is_primary_residence', False):
            docs.append({
                "name": "주민등록등본",
                "description": "1세대1주택 확인용 주민등록등본",
                "required": True
            })
            docs.append({
                "name": "거주 확인 증빙",
                "description": "2년 이상 실거주 확인 서류 (전입신고 확인서 등)",
                "required": True
            })

        # 장기보유특별공제 신청 시
        if tax_result.get('long_term_deduction', 0) > 0:
            docs.append({
                "name": "보유기간 확인 서류",
                "description": "장기보유특별공제 확인용 등기부등본",
                "required": True
            })

        return docs

    def _generate_filing_instructions(
        self,
        facts: Dict[str, Any],
        tax_result: Dict[str, Any],
        deadline: str
    ) -> str:
        """신고 안내 생성

        Returns:
            Markdown 형식의 신고 안내문
        """
        lines = [
            "## 양도소득세 신고 안내",
            "",
            "### 신고 기한",
            f"- 신고 기한: **{deadline}**",
            f"- 양도일: {facts.get('disposal_date', 'N/A')}",
            "- 신고 기한 내에 반드시 신고 및 납부하시기 바랍니다.",
            "",
            "### 신고 방법",
            "1. **홈택스 전자신고** (권장)",
            "   - 홈택스(www.hometax.go.kr) 접속",
            "   - 신고/납부 > 양도소득세 > 확정신고",
            "   - 신고서 작성 및 제출",
            "",
            "2. **세무서 방문 신고**",
            "   - 관할 세무서 방문",
            "   - 신고서 및 증빙서류 제출",
            "",
            "### 납부 금액",
            f"- 양도소득세: {tax_result.get('calculated_tax', 0):,} 원",
            f"- 지방소득세: {tax_result.get('local_tax', 0):,} 원",
            f"- **총 납부세액: {tax_result.get('total_tax', 0):,} 원**",
            ""
        ]

        # 분할납부 안내
        if tax_result.get('total_tax', 0) >= 10_000_000:
            lines.extend([
                "### 분할납부",
                "- 납부세액이 1,000만원 이상이므로 분할납부가 가능합니다.",
                "- 최대 6개월까지 분할납부 가능",
                "- 홈택스에서 분할납부 신청 가능",
                ""
            ])

        # 미신고 시 가산세 안내
        lines.extend([
            "### 주의사항",
            "- 신고 기한 내 미신고 시: 무신고 가산세 20% 부과",
            "- 신고 기한 내 미납부 시: 납부지연 가산세 부과",
            "- 정확한 신고를 위해 세무사 상담을 권장합니다.",
            ""
        ])

        return "\n".join(lines)
