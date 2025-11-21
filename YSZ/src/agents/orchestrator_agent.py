"""총괄 에이전트 (Orchestrator Agent)

전체 워크플로우를 관리하고 4개의 수행 에이전트를 조율합니다.
"""

from typing import Dict, Any, Optional, List
import asyncio
from datetime import datetime

from .asset_collector_agent import AssetCollectorAgent
from .calculation_agent import TaxCalculationAgent
from .verification_agent import CalculationVerificationAgent
from .filing_agent import FilingAgent


class OrchestratorAgent:
    """총괄 에이전트

    역할:
    - 전체 워크플로우 관리
    - 4개 수행 에이전트 조율
    - 세법 판단 지원
    - 품질 관리 및 최종 승인
    """

    def __init__(self, openai_api_key: Optional[str] = None, mock_mode: bool = True):
        """
        Args:
            openai_api_key: OpenAI API 키 (없으면 mock 모드)
            mock_mode: True면 LLM 없이 mock 데이터로 동작
        """
        self.mock_mode = mock_mode or (openai_api_key is None)
        self.openai_api_key = openai_api_key

        # 4개의 수행 에이전트 초기화
        self.asset_collector = AssetCollectorAgent(
            openai_api_key=openai_api_key,
            mock_mode=self.mock_mode
        )
        self.tax_calculator = TaxCalculationAgent(
            openai_api_key=openai_api_key,
            mock_mode=self.mock_mode
        )
        self.verifier = CalculationVerificationAgent(
            mock_mode=self.mock_mode
        )
        self.filing = FilingAgent(
            mock_mode=self.mock_mode
        )

        # 세법 검색용 벡터 DB (추후 구현)
        self.law_db = None

    async def process_case(self, user_input: Dict[str, Any]) -> Dict[str, Any]:
        """전체 케이스 처리

        워크플로우:
        1. 자산정보 수집 (Agent #1)
        2. 세액 산출 (Agent #2)
        3. 계산 검증 (Agent #3)
        4. 신고서 작성 (Agent #4)
        5. 최종 품질 관리

        Args:
            user_input: 사용자 입력 데이터
                - mode: "full" | "intake" | "tax_only"
                - case_id: 케이스 ID
                - form_answers: 폼 답변
                - raw_messages: 사용자 메시지
                - uploaded_files: 업로드된 파일 (OCR 대상)
                - acquisition_date, disposal_date, etc.

        Returns:
            {
                "status": "success" | "error",
                "case_id": str,
                "collected_facts": {...},
                "tax_result": {...},
                "verification": {...},
                "filing_package": {...},
                "report": str
            }
        """
        case_id = user_input.get('case_id', f"C{datetime.now().strftime('%Y%m%d%H%M%S')}")
        mode = user_input.get('mode', 'full')

        try:
            # Stage 1: 자산정보 수집 (Agent #1)
            print(f"[Orchestrator] Stage 1/4: Asset Collection...")
            collected_facts = await self.asset_collector.collect(user_input)

            # Stage 2: 세액 산출 (Agent #2)
            print(f"[Orchestrator] Stage 2/4: Tax Calculation...")
            tax_result = await self.tax_calculator.calculate(collected_facts)

            # Stage 3: 계산 검증 (Agent #3)
            print(f"[Orchestrator] Stage 3/4: Verification...")
            verification = await self.verifier.verify(
                facts=collected_facts,
                tax_result=tax_result
            )

            # Stage 4: 신고서 작성 (Agent #4)
            print(f"[Orchestrator] Stage 4/4: Filing Package...")
            filing_package = await self.filing.prepare_filing(
                facts=collected_facts,
                tax_result=tax_result,
                verification=verification
            )

            # 최종 품질 관리
            quality_check = self._perform_quality_check(
                collected_facts=collected_facts,
                tax_result=tax_result,
                verification=verification,
                filing_package=filing_package
            )

            # 최종 리포트 생성
            report = self._generate_final_report(
                case_id=case_id,
                collected_facts=collected_facts,
                tax_result=tax_result,
                verification=verification,
                filing_package=filing_package,
                quality_check=quality_check
            )

            return {
                "status": "success",
                "case_id": case_id,
                "collected_facts": collected_facts,
                "tax_result": tax_result,
                "verification": verification,
                "filing_package": filing_package,
                "quality_check": quality_check,
                "report": report
            }

        except Exception as e:
            print(f"[Orchestrator] ERROR: {str(e)}")
            import traceback
            traceback.print_exc()

            return {
                "status": "error",
                "case_id": case_id,
                "message": f"처리 중 오류 발생: {str(e)}",
                "error": str(e)
            }

    def _perform_quality_check(
        self,
        collected_facts: Dict[str, Any],
        tax_result: Dict[str, Any],
        verification: Dict[str, Any],
        filing_package: Dict[str, Any]
    ) -> Dict[str, Any]:
        """최종 품질 관리

        Returns:
            {
                "overall_status": "pass" | "review_needed" | "fail",
                "checks": [
                    {"name": "...", "status": "pass", "message": "..."},
                    ...
                ]
            }
        """
        checks = []

        # 1. 필수 정보 완성도 체크
        required_fields = ['acquisition_date', 'acquisition_price', 'disposal_date', 'disposal_price']
        missing_fields = [f for f in required_fields if not collected_facts.get(f)]

        if missing_fields:
            checks.append({
                "name": "필수 정보 완성도",
                "status": "fail",
                "message": f"누락된 정보: {', '.join(missing_fields)}"
            })
        else:
            checks.append({
                "name": "필수 정보 완성도",
                "status": "pass",
                "message": "모든 필수 정보가 수집되었습니다."
            })

        # 2. 계산 검증 상태 체크
        if verification.get('status') == 'verified':
            checks.append({
                "name": "계산 검증",
                "status": "pass",
                "message": "계산이 검증되었습니다."
            })
        else:
            checks.append({
                "name": "계산 검증",
                "status": "review_needed",
                "message": verification.get('message', '검증이 필요합니다.')
            })

        # 3. 신고서 준비 상태 체크
        if filing_package.get('status') == 'ready':
            checks.append({
                "name": "신고서 준비",
                "status": "pass",
                "message": "신고서가 준비되었습니다."
            })
        else:
            checks.append({
                "name": "신고서 준비",
                "status": "review_needed",
                "message": filing_package.get('message', '신고서 준비 중입니다.')
            })

        # 전체 상태 판단
        fail_count = sum(1 for c in checks if c['status'] == 'fail')
        review_count = sum(1 for c in checks if c['status'] == 'review_needed')

        if fail_count > 0:
            overall_status = "fail"
        elif review_count > 0:
            overall_status = "review_needed"
        else:
            overall_status = "pass"

        return {
            "overall_status": overall_status,
            "checks": checks,
            "timestamp": datetime.now().isoformat()
        }

    def _generate_final_report(
        self,
        case_id: str,
        collected_facts: Dict[str, Any],
        tax_result: Dict[str, Any],
        verification: Dict[str, Any],
        filing_package: Dict[str, Any],
        quality_check: Dict[str, Any]
    ) -> str:
        """최종 종합 리포트 생성"""

        report_lines = [
            "=" * 60,
            f"양도소득세 계산 종합 보고서",
            f"케이스 ID: {case_id}",
            f"작성일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 60,
            "",
            "1. 자산 정보",
            "-" * 60
        ]

        # 자산 정보
        if collected_facts:
            report_lines.extend([
                f"취득일: {collected_facts.get('acquisition_date', 'N/A')}",
                f"취득가액: {collected_facts.get('acquisition_price', 0):,} 원",
                f"양도일: {collected_facts.get('disposal_date', 'N/A')}",
                f"양도가액: {collected_facts.get('disposal_price', 0):,} 원",
                f"자산 유형: {collected_facts.get('asset_type', 'N/A')}",
                f"1세대1주택 여부: {collected_facts.get('is_primary_residence', False)}",
                ""
            ])

        # 세액 정보
        report_lines.extend([
            "2. 세액 계산 결과",
            "-" * 60
        ])

        if tax_result:
            report_lines.extend([
                f"양도차익: {tax_result.get('capital_gain', 0):,} 원",
                f"과세표준: {tax_result.get('taxable_income', 0):,} 원",
                f"산출세액: {tax_result.get('calculated_tax', 0):,} 원",
                f"지방소득세: {tax_result.get('local_tax', 0):,} 원",
                f"총 납부세액: {tax_result.get('total_tax', 0):,} 원",
                ""
            ])

        # 검증 결과
        report_lines.extend([
            "3. 검증 결과",
            "-" * 60,
            f"검증 상태: {verification.get('status', 'N/A')}",
            f"검증 메시지: {verification.get('message', 'N/A')}",
            ""
        ])

        # 신고 안내
        report_lines.extend([
            "4. 신고 안내",
            "-" * 60,
            f"신고 상태: {filing_package.get('status', 'N/A')}",
            f"신고 기한: {filing_package.get('deadline', 'N/A')}",
            ""
        ])

        # 품질 체크
        report_lines.extend([
            "5. 품질 체크",
            "-" * 60,
            f"전체 상태: {quality_check.get('overall_status', 'N/A')}",
            ""
        ])

        for check in quality_check.get('checks', []):
            report_lines.append(f"  [{check['status']}] {check['name']}: {check['message']}")

        report_lines.extend([
            "",
            "=" * 60,
            "보고서 끝",
            "=" * 60
        ])

        return "\n".join(report_lines)

    async def search_tax_law(self, query: str) -> List[Dict[str, Any]]:
        """세법 검색 (벡터 DB 사용)

        추후 구현:
        - 세법 조문 벡터화
        - 유사도 기반 검색
        - 판례 검색

        Args:
            query: 검색 쿼리

        Returns:
            [
                {"law_id": "...", "title": "...", "content": "...", "similarity": 0.95},
                ...
            ]
        """
        if self.mock_mode:
            return [
                {
                    "law_id": "소득세법 제95조",
                    "title": "양도소득세 세율",
                    "content": "양도소득세는 과세표준에 따라 6~45%의 누진세율을 적용합니다.",
                    "similarity": 0.95
                }
            ]

        # TODO: 실제 벡터 DB 검색 구현
        return []
