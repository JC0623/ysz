"""자산정보 수집 에이전트 (Asset Collector Agent)

사용자로부터 양도소득세 계산에 필요한 사실관계 정보를 수집합니다.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from decimal import Decimal


class AssetCollectorAgent:
    """자산정보 수집 에이전트

    역할:
    - 자연어 입력 처리 및 정보 추출
    - 문서 OCR (사진/PDF)
    - 외부 API 연동 (국토부 실거래가 등)
    - 데이터 검증 및 정규화
    """

    def __init__(self, openai_api_key: Optional[str] = None, mock_mode: bool = True):
        """
        Args:
            openai_api_key: OpenAI API 키 (없으면 mock 모드)
            mock_mode: True면 LLM 없이 mock 데이터로 동작
        """
        self.mock_mode = mock_mode or (openai_api_key is None)
        self.openai_api_key = openai_api_key

    async def collect(self, user_input: Dict[str, Any]) -> Dict[str, Any]:
        """사용자 입력으로부터 사실관계 정보 수집

        처리 순서:
        1. 직접 입력된 필드 추출
        2. 자연어 메시지 파싱 (LLM)
        3. 업로드 파일 OCR 처리
        4. 외부 API 조회 (주소 -> 실거래가 등)
        5. 데이터 검증 및 정규화

        Args:
            user_input: 사용자 입력 데이터
                - form_answers: 폼 답변 dict
                - raw_messages: 사용자 메시지 list
                - uploaded_files: 업로드 파일 list
                - acquisition_date, disposal_date, etc. (직접 입력)

        Returns:
            {
                "acquisition_date": "2020-01-15",
                "acquisition_price": 500000000,
                "disposal_date": "2024-12-20",
                "disposal_price": 1000000000,
                "asset_type": "residential",
                "is_primary_residence": True,
                "necessary_expenses": 5000000,
                "house_count": 1,
                "is_adjusted_area": False,
                "address": "서울시 강남구...",
                "extraction_sources": [
                    {"type": "direct_input", "fields": ["acquisition_date", ...]},
                    {"type": "message_parsing", "fields": [...]},
                    {"type": "ocr", "fields": [...]}
                ]
            }
        """
        print(f"[AssetCollector] Collecting facts from user input...")

        collected = {}
        extraction_sources = []

        # 1. 직접 입력 필드 추출
        direct_fields = self._extract_direct_fields(user_input)
        if direct_fields:
            collected.update(direct_fields)
            extraction_sources.append({
                "type": "direct_input",
                "fields": list(direct_fields.keys())
            })

        # 2. 폼 답변 파싱
        form_data = self._parse_form_answers(user_input.get('form_answers', {}))
        if form_data:
            collected.update(form_data)
            extraction_sources.append({
                "type": "form_answers",
                "fields": list(form_data.keys())
            })

        # 3. 자연어 메시지 파싱 (LLM 사용)
        raw_messages = user_input.get('raw_messages', [])
        if raw_messages:
            message_data = await self._parse_messages(raw_messages)
            if message_data:
                collected.update(message_data)
                extraction_sources.append({
                    "type": "message_parsing",
                    "fields": list(message_data.keys())
                })

        # 4. 업로드 파일 OCR 처리
        uploaded_files = user_input.get('uploaded_files', [])
        if uploaded_files:
            ocr_data = await self._extract_from_documents(uploaded_files)
            if ocr_data:
                collected.update(ocr_data)
                extraction_sources.append({
                    "type": "ocr",
                    "fields": list(ocr_data.keys())
                })

        # 5. 외부 API 조회 (주소 기반)
        if 'address' in collected:
            api_data = await self._query_external_apis(collected['address'])
            if api_data:
                collected.update(api_data)
                extraction_sources.append({
                    "type": "external_api",
                    "fields": list(api_data.keys())
                })

        # 6. 데이터 검증 및 정규화
        validated = self._validate_and_normalize(collected)

        validated['extraction_sources'] = extraction_sources
        validated['collected_at'] = datetime.now().isoformat()

        print(f"[AssetCollector] Collected {len(validated)} fields from {len(extraction_sources)} sources")

        return validated

    def _extract_direct_fields(self, user_input: Dict[str, Any]) -> Dict[str, Any]:
        """직접 입력된 필드 추출"""
        fields = {}

        # 직접 입력 가능한 필드 목록
        direct_field_names = [
            'acquisition_date',
            'acquisition_price',
            'disposal_date',
            'disposal_price',
            'asset_type',
            'is_primary_residence',
            'necessary_expenses',
            'house_count',
            'is_adjusted_area',
            'address'
        ]

        for field_name in direct_field_names:
            if field_name in user_input and user_input[field_name] is not None:
                fields[field_name] = user_input[field_name]

        return fields

    def _parse_form_answers(self, form_answers: Dict[str, Any]) -> Dict[str, Any]:
        """폼 답변 파싱

        Example:
            {
                "q_asset_type": "residential" -> asset_type: "residential"
                "q_is_primary_residence": "예" -> is_primary_residence: True
            }
        """
        parsed = {}

        # asset_type
        if 'q_asset_type' in form_answers:
            parsed['asset_type'] = form_answers['q_asset_type']

        # is_primary_residence
        if 'q_is_primary_residence' in form_answers:
            answer = form_answers['q_is_primary_residence']
            parsed['is_primary_residence'] = answer in ['예', 'yes', 'true', True]

        # address/region
        if 'q_region' in form_answers:
            parsed['address'] = form_answers['q_region']

        return parsed

    async def _parse_messages(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """자연어 메시지에서 정보 추출 (LLM 사용)

        Example message:
            "2020년 1월에 5억에 샀고, 2024년 12월에 10억에 팔았어요"
            -> acquisition_date: "2020-01-01", acquisition_price: 500000000, ...
        """
        if self.mock_mode:
            # Mock: 간단한 키워드 기반 파싱
            parsed = {}

            for msg in messages:
                text = msg.get('text', '')

                # 간단한 패턴 매칭 (실제로는 LLM 사용)
                if '샀' in text or '취득' in text:
                    # 취득 정보 추출 시도
                    pass

                if '팔았' in text or '양도' in text:
                    # 양도 정보 추출 시도
                    pass

            return parsed

        # TODO: 실제 LLM을 사용한 정보 추출
        # - OpenAI Function Calling
        # - 구조화된 출력
        return {}

    async def _extract_from_documents(self, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """문서에서 자동 정보 추출 (OCR)

        지원 파일 타입:
        - 이미지: JPEG, PNG
        - 문서: PDF

        OCR 엔진:
        - Tesseract OCR (오픈소스)
        - Google Cloud Vision API
        - AWS Textract

        Args:
            files: [
                {"filename": "계약서.pdf", "content": bytes, "type": "application/pdf"},
                {"filename": "영수증.jpg", "content": bytes, "type": "image/jpeg"},
                ...
            ]

        Returns:
            추출된 정보 dict
        """
        if self.mock_mode:
            print(f"[AssetCollector] OCR: {len(files)} files (mock mode)")
            return {}

        # TODO: 실제 OCR 구현
        # from src.services.ocr_service import OCRService
        # ocr_service = OCRService()
        #
        # results = []
        # for file in files:
        #     if file['type'] in ['image/jpeg', 'image/png']:
        #         text = await ocr_service.extract_image(file['content'])
        #     elif file['type'] == 'application/pdf':
        #         text = await ocr_service.extract_pdf(file['content'])
        #     else:
        #         continue
        #
        #     # 추출된 텍스트에서 정보 파싱
        #     parsed = await self._parse_extracted_text(text, file['filename'])
        #     results.append(parsed)
        #
        # return self._merge_extracted_data(results)

        return {}

    async def _query_external_apis(self, address: str) -> Dict[str, Any]:
        """외부 API 조회

        APIs:
        - 국토부 실거래가 조회
        - 조정대상지역 여부 확인
        - 공시지가 조회

        Args:
            address: 주소 (예: "서울시 강남구 역삼동 123-45")

        Returns:
            {
                "real_transaction_price": 950000000,
                "is_adjusted_area": True,
                "official_land_price": 800000000
            }
        """
        if self.mock_mode:
            print(f"[AssetCollector] External API query for: {address} (mock mode)")
            return {}

        # TODO: 실제 API 연동
        # - 국토교통부 Open API
        # - 조정대상지역 API
        return {}

    def _validate_and_normalize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """데이터 검증 및 정규화

        - 날짜 형식 통일
        - 금액 타입 통일 (int/float)
        - 필수 필드 확인
        - 범위 검증
        """
        validated = {}

        # acquisition_date
        if 'acquisition_date' in data:
            validated['acquisition_date'] = self._normalize_date(data['acquisition_date'])

        # disposal_date
        if 'disposal_date' in data:
            validated['disposal_date'] = self._normalize_date(data['disposal_date'])

        # acquisition_price
        if 'acquisition_price' in data:
            validated['acquisition_price'] = self._normalize_price(data['acquisition_price'])

        # disposal_price
        if 'disposal_price' in data:
            validated['disposal_price'] = self._normalize_price(data['disposal_price'])

        # asset_type
        if 'asset_type' in data:
            validated['asset_type'] = data['asset_type']

        # is_primary_residence
        if 'is_primary_residence' in data:
            validated['is_primary_residence'] = bool(data['is_primary_residence'])

        # necessary_expenses
        if 'necessary_expenses' in data:
            validated['necessary_expenses'] = self._normalize_price(data['necessary_expenses'])
        else:
            validated['necessary_expenses'] = 0

        # house_count
        if 'house_count' in data:
            validated['house_count'] = int(data['house_count'])
        else:
            validated['house_count'] = 1

        # is_adjusted_area
        if 'is_adjusted_area' in data:
            validated['is_adjusted_area'] = bool(data['is_adjusted_area'])
        else:
            validated['is_adjusted_area'] = False

        # address
        if 'address' in data:
            validated['address'] = data['address']

        return validated

    def _normalize_date(self, date_value: Any) -> str:
        """날짜 정규화 -> YYYY-MM-DD"""
        if isinstance(date_value, str):
            return date_value
        elif hasattr(date_value, 'isoformat'):
            return date_value.isoformat()
        else:
            return str(date_value)

    def _normalize_price(self, price_value: Any) -> float:
        """금액 정규화 -> float"""
        if isinstance(price_value, (int, float)):
            return float(price_value)
        elif isinstance(price_value, Decimal):
            return float(price_value)
        elif isinstance(price_value, str):
            # 쉼표 제거 후 변환
            return float(price_value.replace(',', ''))
        else:
            return float(price_value)
