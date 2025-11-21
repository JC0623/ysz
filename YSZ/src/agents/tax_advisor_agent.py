"""양도소득세 총괄 세무사 AI 에이전트

Mono Agent v0.1
- 정보 수집 (Intake)
- 계산 API 호출 (Tax Calculation)
- 위험 분석 및 리포트 생성 (Risk Analysis & Report)
"""

import os
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, date
from decimal import Decimal

# OpenAI 대신 mock으로 시작 (API 키 없어도 테스트 가능)
# 실제 사용 시: pip install openai
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from ..core import TaxCalculator, FactLedger, Fact


class TaxAdvisorAgent:
    """양도소득세 총괄 세무사 AI 에이전트

    역할:
    1. Intake: 고객 정보를 구조화된 데이터로 변환
    2. Calculation: 기존 TaxCalculator API 호출
    3. Analysis: 위험 요소 분석 및 조언
    4. Report: 자연어 리포트 생성
    """

    def __init__(self, openai_api_key: Optional[str] = None):
        """에이전트 초기화

        Args:
            openai_api_key: OpenAI API 키 (없으면 mock 모드)
        """
        self.calculator = TaxCalculator()

        # OpenAI 클라이언트
        if OPENAI_AVAILABLE and openai_api_key:
            self.llm = OpenAI(api_key=openai_api_key)
            self.mock_mode = False
        else:
            self.llm = None
            self.mock_mode = True
            # Unicode encoding issue on Windows - comment out emoji
            # print("⚠️  Mock 모드로 실행 중 (OpenAI API 없음)")

    async def process_case(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """케이스 처리 메인 함수

        Args:
            request: {
                "mode": "full",  # "intake" | "tax_only" | "full"
                "case_id": "C2025-0001",
                "form_answers": {...},
                "raw_messages": [...],
                ...
            }

        Returns:
            {
                "status": "success",
                "case_draft": {...},
                "tax_result": {...},
                "risk_flags": [...],
                "report": "..."
            }
        """
        mode = request.get('mode', 'full')

        try:
            # 1단계: Intake - 정보 구조화
            print("[1/4] Intake: 정보 수집")
            case_draft = await self._intake(request)

            if mode == 'intake':
                return {
                    "status": "draft",
                    "case_draft": case_draft,
                    "message": "정보 수집 완료. 추가 확인이 필요합니다."
                }

            # 2단계: Tax Calculation
            print("[2/4] Calculation: 세금 계산")
            tax_result = await self._calculate_tax(case_draft)

            if mode == 'tax_only':
                return {
                    "status": "calculated",
                    "tax_result": tax_result
                }

            # 3단계: Risk Analysis
            print("[3/4] Risk Analysis: 위험 분석")
            risk_flags = self._analyze_risks(case_draft, tax_result)

            # 4단계: Report Generation
            print("[4/4] Report: 리포트 생성")
            report = await self._generate_report(
                case_draft, tax_result, risk_flags
            )

            return {
                "status": "success",
                "case_id": request.get('case_id'),
                "case_draft": case_draft,
                "tax_result": tax_result,
                "risk_flags": risk_flags,
                "report": report,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": f"처리 중 오류 발생: {str(e)}"
            }

    async def _intake(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """정보 수집 및 구조화

        form_answers + raw_messages를 분석해서
        FactLedger에 필요한 구조화된 데이터로 변환
        """
        form_answers = request.get('form_answers', {})
        raw_messages = request.get('raw_messages', [])

        # 기본 정보 추출
        case_draft = {
            'asset_type': form_answers.get('q_asset_type', 'residential'),
            'is_primary_residence': self._parse_yes_no(
                form_answers.get('q_is_primary_residence')
            ),
            'region': form_answers.get('q_region', ''),
        }

        # request 최상위 레벨에서 계산 필드 추출 (direct API call용)
        direct_fields = [
            'acquisition_date', 'acquisition_price',
            'disposal_date', 'disposal_price',
            'necessary_expenses', 'house_count', 'is_adjusted_area'
        ]
        for field in direct_fields:
            if field in request:
                case_draft[field] = request[field]

        # raw_messages에서 추가 정보 추출 (LLM 사용)
        if raw_messages and not self.mock_mode:
            extracted = await self._extract_from_messages(raw_messages)
            case_draft.update(extracted)

        # 필수 필드 확인
        case_draft['missing_fields'] = self._check_missing_fields(case_draft)
        case_draft['is_complete'] = len(case_draft['missing_fields']) == 0

        return case_draft

    async def _extract_from_messages(
        self, messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """자연어 메시지에서 정보 추출 (LLM 사용)"""

        if self.mock_mode or not self.llm:
            # Mock: 간단한 패턴 매칭
            return {}

        # 메시지 합치기
        combined_text = "\n".join([
            f"{msg.get('sender', 'user')}: {msg.get('text', '')}"
            for msg in messages
        ])

        # LLM에게 정보 추출 요청
        response = await self.llm.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": """
                    당신은 양도소득세 전문 세무사입니다.
                    고객의 메시지에서 다음 정보를 추출하세요:
                    - acquisition_date: 취득일 (YYYY-MM-DD)
                    - acquisition_price: 취득가액 (숫자만)
                    - disposal_date: 양도일 (YYYY-MM-DD)
                    - disposal_price: 양도가액 (숫자만)
                    - residence_years: 거주기간 (년)
                    - house_count: 보유 주택 수

                    JSON 형식으로만 응답하세요.
                    """
                },
                {
                    "role": "user",
                    "content": combined_text
                }
            ],
            response_format={"type": "json_object"}
        )

        extracted = json.loads(response.choices[0].message.content)
        return extracted

    async def _calculate_tax(self, case_draft: Dict[str, Any]) -> Dict[str, Any]:
        """세금 계산 (기존 TaxCalculator API 호출)"""

        # case_draft → FactLedger 변환
        try:
            facts_dict = {
                'acquisition_date': self._parse_date(
                    case_draft.get('acquisition_date')
                ),
                'acquisition_price': self._parse_decimal(
                    case_draft.get('acquisition_price')
                ),
                'disposal_date': self._parse_date(
                    case_draft.get('disposal_date')
                ),
                'disposal_price': self._parse_decimal(
                    case_draft.get('disposal_price')
                ),
                'asset_type': case_draft.get('asset_type', 'residential'),
                'is_primary_residence': case_draft.get('is_primary_residence', False),
                'necessary_expenses': self._parse_decimal(
                    case_draft.get('necessary_expenses', 0)
                ),
                'house_count': case_draft.get('house_count', 1),
                'is_adjusted_area': case_draft.get('is_adjusted_area', False),
            }

            # FactLedger 생성
            ledger = FactLedger.create(facts_dict, created_by="agent")

            # 확정 (모든 Fact 자동 확정)
            from ..core.fact import Fact
            from datetime import datetime
            for attr_name in vars(ledger):
                attr = getattr(ledger, attr_name)
                if isinstance(attr, Fact) and not attr.is_confirmed:
                    # Frozen dataclass 우회하여 확정 설정
                    object.__setattr__(attr, 'is_confirmed', True)
                    object.__setattr__(attr, 'confidence', 1.0)
                    object.__setattr__(attr, 'entered_by', "agent")
                    object.__setattr__(attr, 'entered_at', datetime.now())

            ledger.freeze()

            # 계산
            result = self.calculator.calculate(ledger)

            # 결과 변환 (ledger와 result 모두 사용)
            disposal_price_val = float(ledger.disposal_price.value)
            acquisition_price_val = float(ledger.acquisition_price.value)
            necessary_exp_val = float(ledger.necessary_expenses.value) if ledger.necessary_expenses else 0

            return {
                'disposal_price': disposal_price_val,
                'acquisition_price': acquisition_price_val,
                'capital_gain': disposal_price_val - acquisition_price_val,
                'necessary_expenses': necessary_exp_val,
                'long_term_deduction': float(result.long_term_deduction),
                'basic_deduction': float(result.basic_deduction),
                'taxable_income': float(result.taxable_income),
                'calculated_tax': float(result.calculated_tax),
                'local_tax': float(result.local_tax),
                'total_tax': float(result.final_tax),
                'applied_tax_rate': float(result.base_tax_rate) if result.base_tax_rate else 0,
                'warnings': getattr(result, 'warnings', [])
            }

        except Exception as e:
            raise ValueError(f"세금 계산 실패: {str(e)}")

    def _analyze_risks(
        self,
        case_draft: Dict[str, Any],
        tax_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """위험 요소 분석"""

        risks = []

        # 1. 고액 세금
        if tax_result['total_tax'] > 100_000_000:
            risks.append({
                'level': 'HIGH',
                'category': 'high_amount',
                'title': '고액 세금 (1억 이상)',
                'description': '세무사 직접 검토 필요',
                'action': '세무사 상담 예약'
            })

        # 2. 다주택 중과세
        if case_draft.get('house_count', 1) >= 2:
            risks.append({
                'level': 'MEDIUM',
                'category': 'multi_house',
                'title': '다주택 중과세 대상',
                'description': '추가 세율 적용됨',
                'action': '절세 전략 검토'
            })

        # 3. 단기 보유
        holding_years = self._calculate_holding_years(
            case_draft.get('acquisition_date'),
            case_draft.get('disposal_date')
        )
        if holding_years < 2:
            risks.append({
                'level': 'HIGH',
                'category': 'short_term',
                'title': f'단기 보유 ({holding_years}년)',
                'description': '높은 세율 적용 (50-70%)',
                'action': '매도 시기 재검토 권장'
            })

        # 4. 데이터 불완전
        if not case_draft.get('is_complete'):
            risks.append({
                'level': 'MEDIUM',
                'category': 'incomplete_data',
                'title': '정보 불완전',
                'description': f"누락 필드: {', '.join(case_draft.get('missing_fields', []))}",
                'action': '추가 정보 수집 필요'
            })

        return risks

    async def _generate_report(
        self,
        case_draft: Dict[str, Any],
        tax_result: Dict[str, Any],
        risk_flags: List[Dict[str, Any]]
    ) -> str:
        """최종 리포트 생성 (자연어)"""

        if self.mock_mode or not self.llm:
            # Mock: 간단한 텍스트 리포트
            return self._generate_simple_report(case_draft, tax_result, risk_flags)

        # LLM을 사용한 자연어 리포트
        prompt = f"""
        다음 양도소득세 계산 결과를 고객에게 설명하는 리포트를 작성하세요:

        ## 계산 결과
        - 양도가액: {tax_result['disposal_price']:,.0f}원
        - 취득가액: {tax_result['acquisition_price']:,.0f}원
        - 양도차익: {tax_result['capital_gain']:,.0f}원
        - 과세표준: {tax_result['taxable_income']:,.0f}원
        - 산출세액: {tax_result['calculated_tax']:,.0f}원
        - 지방소득세: {tax_result['local_tax']:,.0f}원
        - 총 납부세액: {tax_result['total_tax']:,.0f}원

        ## 위험 요소
        {self._format_risks(risk_flags)}

        친절하고 전문적인 어조로 작성하세요.
        """

        response = await self.llm.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "당신은 양도소득세 전문 세무사입니다."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        return response.choices[0].message.content

    def _generate_simple_report(
        self,
        case_draft: Dict[str, Any],
        tax_result: Dict[str, Any],
        risk_flags: List[Dict[str, Any]]
    ) -> str:
        """간단한 텍스트 리포트 (Mock용)"""

        report = f"""
# 양도소득세 계산 결과 보고서

## [Calculation Result] 계산 결과

| 항목 | 금액 |
|------|------|
| 양도가액 | {tax_result['disposal_price']:,.0f}원 |
| 취득가액 | {tax_result['acquisition_price']:,.0f}원 |
| 양도차익 | {tax_result['capital_gain']:,.0f}원 |
| 필요경비 | {tax_result['necessary_expenses']:,.0f}원 |
| 장기보유특별공제 | {tax_result['long_term_deduction']:,.0f}원 |
| 기본공제 | {tax_result['basic_deduction']:,.0f}원 |
| 과세표준 | {tax_result['taxable_income']:,.0f}원 |
| 산출세액 | {tax_result['calculated_tax']:,.0f}원 |
| 지방소득세 | {tax_result['local_tax']:,.0f}원 |
| **총 납부세액** | **{tax_result['total_tax']:,.0f}원** |

## [Risk Analysis] 위험 요소

"""
        if risk_flags:
            for risk in risk_flags:
                report += f"- [{risk['level']}] {risk['title']}: {risk['description']}\n"
        else:
            report += "특별한 위험 요소가 발견되지 않았습니다.\n"

        report += "\n---\n생성일시: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return report

    # 유틸리티 함수들

    def _parse_yes_no(self, value: Any) -> bool:
        """예/아니오를 bool로 변환"""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ['예', 'yes', 'y', 'true', '1']
        return False

    def _parse_date(self, value: Any) -> Optional[date]:
        """날짜 파싱"""
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            try:
                return datetime.strptime(value, "%Y-%m-%d").date()
            except:
                return None
        return None

    def _parse_decimal(self, value: Any) -> Decimal:
        """Decimal 파싱"""
        if isinstance(value, Decimal):
            return value
        if isinstance(value, (int, float)):
            return Decimal(str(value))
        if isinstance(value, str):
            # 콤마 제거
            cleaned = value.replace(',', '').replace('원', '')
            try:
                return Decimal(cleaned)
            except:
                return Decimal('0')
        return Decimal('0')

    def _check_missing_fields(self, case_draft: Dict[str, Any]) -> List[str]:
        """필수 필드 누락 확인"""
        required = [
            'acquisition_date',
            'acquisition_price',
            'disposal_date',
            'disposal_price',
            'asset_type'
        ]

        missing = []
        for field in required:
            if not case_draft.get(field):
                missing.append(field)

        return missing

    def _calculate_holding_years(self, acq_date: Any, disp_date: Any) -> int:
        """보유 기간 계산"""
        acq = self._parse_date(acq_date)
        disp = self._parse_date(disp_date)

        if not acq or not disp:
            return 0

        days = (disp - acq).days
        return days // 365

    def _format_risks(self, risks: List[Dict[str, Any]]) -> str:
        """위험 요소 포맷팅"""
        if not risks:
            return "없음"

        return "\n".join([
            f"- [{r['level']}] {r['title']}: {r['description']}"
            for r in risks
        ])
