# YSZ 멀티 AI 에이전트 아키텍처
## 5-Agent System for Capital Gains Tax Calculation

---

## 📋 목차
1. [전체 구조](#전체-구조)
2. [핵심 에이전트 5개](#핵심-에이전트-5개)
3. [정보 수집 파트 구분](#정보-수집-파트-구분)
4. [에이전트 간 협업 흐름](#에이전트-간-협업-흐름)
5. [구현 로드맵](#구현-로드맵)
6. [기술 스택](#기술-스택)

---

## 전체 구조

```
사용자 입력 (자연어/문서/API)
           ↓
    ┌──────────────────┐
    │  총괄 에이전트    │ ← Orchestrator (세법 판단 지원)
    │  (Coordinator)   │
    └──────────────────┘
           ↓
    ┌─────┴─────┬─────┬─────┬─────┐
    ↓           ↓     ↓     ↓     ↓
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│에이전트1│ │에이전트2│ │에이전트3│ │에이전트4│
│자산수집 │ │세액산출 │ │계산검증 │ │신고    │
└────────┘ └────────┘ └────────┘ └────────┘
    │          │          │          │
    └──────────┴──────────┴──────────┘
                   ↓
           최종 신고/보고서
```

---

## 핵심 에이전트 5개

### 🎯 **총괄 에이전트 (Orchestrator Agent)**
**역할**: 전체 워크플로우 조율 및 세법 판단 지원

#### 주요 책임
1. **워크플로우 관리**
   - 4개 수행 에이전트 조율
   - 작업 우선순위 결정
   - 병렬 처리 최적화

2. **세법 판단 지원**
   - 세법 조문 검색 (Vector DB)
   - 세법 시행령 해석
   - 조세특례제한법 적용 여부
   - 특수관계인 거래 판단

3. **품질 관리**
   - 각 에이전트 출력 검증
   - 에러 핸들링
   - 재실행 결정

#### 구현 구조
```python
class OrchestratorAgent:
    """총괄 에이전트 - 전체 프로세스 조율"""

    def __init__(self):
        # 수행 에이전트들
        self.asset_collector = AssetCollectorAgent()
        self.tax_calculator = TaxCalculationAgent()
        self.verifier = CalculationVerificationAgent()
        self.filing = FilingAgent()

        # 세법 지원 도구
        self.law_db = VectorDatabase("tax_law")
        self.llm = OpenAI(model="gpt-4")

    async def process_case(self, user_input: dict):
        """케이스 처리 전체 플로우"""

        # 1. 워크플로우 계획
        workflow = await self.plan_workflow(user_input)

        # 2. 에이전트 실행 (병렬 가능한 것은 병렬 처리)
        results = {}

        # Step 1: 자산 정보 수집
        results['assets'] = await self.asset_collector.collect(user_input)

        # Step 2 & 세법 조회 (병렬)
        results['calculation'], results['law_refs'] = await asyncio.gather(
            self.tax_calculator.calculate(results['assets']),
            self.search_applicable_laws(results['assets'])
        )

        # Step 3: 검증
        results['verification'] = await self.verifier.verify(
            results['calculation'],
            results['law_refs']
        )

        # Step 4: 신고 (검증 통과 시)
        if results['verification']['status'] == 'PASS':
            results['filing'] = await self.filing.prepare(results)

        return results

    async def search_applicable_laws(self, facts: dict):
        """적용 가능한 세법 조항 검색"""

        # Vector DB에서 유사 조항 검색
        query_embedding = await self.embed(facts)
        similar_laws = await self.law_db.search(
            query_embedding,
            top_k=5
        )

        # LLM으로 적용 여부 판단
        applicability = await self.llm.analyze_applicability(
            facts=facts,
            laws=similar_laws
        )

        return applicability
```

---

### 🏠 **에이전트 #1: 자산정보 수집 (Asset Collector Agent)**
**역할**: 거래 자산의 사실관계 수집

#### 정보 수집 범위

##### A. 거래가 이미 일어난 경우
1. **거래 기본 정보**
   - 양도가액 (실제 거래 금액)
   - 취득가액 (구매 당시 금액)
   - 거래일자 (취득일, 양도일)

2. **자산 정보**
   - 정확한 주소
   - 면적 (전용/공급)
   - 자산 유형 (주택/토지/상가 등)

3. **거래 세부 사항**
   - 양도 방식별 특성
   - 양도인 정보
   - 필요경비 내역

##### B. 거래가 일어나기 전인 경우
1. **시뮬레이션 시나리오**
   - 예상 양도가액
   - 양도 시기 옵션 (단일/복수)
   - 보유 기간 계산

2. **최적화 분석**
   - 최적 매도 시점
   - 세금 시뮬레이션

#### 데이터 소스

##### 1) 사용자 입력
```python
# 자연어 대화
user_input = "2020년에 5억에 샀고, 2024년에 10억에 팔았어요"

# 구조화된 추출
extracted = {
    'acquisition_date': '2020-01-15',
    'acquisition_price': 500000000,
    'disposal_date': '2024-12-20',
    'disposal_price': 1000000000
}
```

##### 2) 문서 OCR (사진, PDF)
- **등기부등본**: OCR → 소유권 정보 추출
- **매매계약서**: OCR → 거래가액, 날짜 추출
- **취득세 영수증**: OCR → 취득가액 검증

```python
async def extract_from_documents(self, files: List[File]):
    """문서에서 자동 정보 추출"""

    results = []

    for file in files:
        # OCR 처리
        if file.type in ['image/jpeg', 'image/png']:
            text = await self.ocr_service.extract_image(file)
        elif file.type == 'application/pdf':
            text = await self.ocr_service.extract_pdf(file)

        # 정보 파싱
        parsed = await self.parse_document(text, file.name)
        results.append(parsed)

    return self.merge_extracted_data(results)
```

##### 3) 외부 API 조회
- **국토부 실거래가 API**: 시세 검증
- **공시지가 조회**: 기준가격 확인
- **조정대상지역 이력**: 규제 여부

#### 구현 예시
```python
class AssetCollectorAgent:
    """자산 정보 수집 에이전트"""

    async def collect(self, user_input: dict):
        """모든 소스로부터 정보 수집"""

        facts = {}

        # 1. 자연어 입력 처리
        if user_input.get('message'):
            facts.update(
                await self.extract_from_text(user_input['message'])
            )

        # 2. 문서 처리 (사진/PDF OCR)
        if user_input.get('files'):
            facts.update(
                await self.extract_from_documents(user_input['files'])
            )

        # 3. API 자동 조회
        if facts.get('address'):
            external_data = await self.fetch_external_data(
                facts['address'],
                facts.get('disposal_date')
            )
            facts.update(external_data)

        # 4. 검증 및 신뢰도 평가
        validated = await self.validate_facts(facts)

        return validated
```

---

### 🧮 **에이전트 #2: 세액 산출 (Tax Calculation Agent)**
**역할**: 사실관계를 기반으로 세액 계산

#### 주요 기능

1. **기본 세액 계산**
   - 양도차익 산출
   - 장기보유특별공제 계산
   - 과세표준 산정
   - 세율 적용 (누진세율)

2. **다양한 시나리오 계산**
```python
async def calculate_scenarios(self, facts: dict):
    """여러 시나리오 계산"""

    scenarios = []

    # 시나리오 1: 현재 상태
    current = await self.calculate_base(facts)
    scenarios.append({
        'name': '현재 상태',
        'result': current,
        'description': '입력된 정보 기준'
    })

    # 시나리오 2: 보유기간 최적화
    if facts['holding_years'] < 2:
        optimized_facts = facts.copy()
        optimized_facts['disposal_date'] = self.add_years(
            facts['acquisition_date'], 2
        )
        optimized = await self.calculate_base(optimized_facts)

        saving = current['total_tax'] - optimized['total_tax']
        scenarios.append({
            'name': '2년 보유 후 매도',
            'result': optimized,
            'description': f'세금 절감: {saving:,}원',
            'saving': saving
        })

    # 시나리오 3: 필요경비 최적화
    optimized_expenses = await self.optimize_expenses(facts)
    if optimized_expenses['necessary_expenses'] > facts['necessary_expenses']:
        optimized = await self.calculate_base(optimized_expenses)
        saving = current['total_tax'] - optimized['total_tax']
        scenarios.append({
            'name': '비용 최적화',
            'result': optimized,
            'description': f'추가 비용 반영 시: {saving:,}원',
            'saving': saving
        })

    return sorted(scenarios, key=lambda x: x.get('saving', 0), reverse=True)
```

3. **보고서 생성**
   - 계산 과정 추적
   - 적용 세법 명시
   - 경고 메시지

#### 기존 TaxCalculator 연동
```python
class TaxCalculationAgent:
    """세액 산출 에이전트"""

    def __init__(self):
        # 기존 계산 엔진 활용
        from ...core import TaxCalculator, FactLedger
        self.calculator = TaxCalculator()

    async def calculate(self, facts: dict):
        """세액 계산 실행"""

        # FactLedger 생성
        ledger = FactLedger.create(facts, created_by="agent")

        # 계산 실행
        result = self.calculator.calculate(ledger)

        # 추적 정보 추가
        trace = self.generate_trace(result)

        return {
            'result': result,
            'trace': trace,
            'confidence': self.assess_confidence(ledger),
            'warnings': self.check_warnings(ledger, result)
        }
```

---

### ✅ **에이전트 #3: 계산 검증 (Verification Agent)**
**역할**: 계산 결과 및 로직 검증

#### 검증 항목

1. **계산 로직 검증**
   - 세법 조항 적용 정확성
   - 공제/감면 적용 타당성
   - 세율 적용 오류 확인

2. **착오류 통계 분석**
   - 과거 오류 패턴 학습
   - 유사 케이스 비교
   - 이상치 탐지

3. **교차 검증**
```python
class CalculationVerificationAgent:
    """계산 검증 에이전트"""

    async def verify(self, calculation: dict, law_refs: dict):
        """계산 결과 검증"""

        issues = []

        # 1. 범위 검증 (실거래가 vs 계산가액)
        if calculation['disposal_price'] < calculation['acquisition_price']:
            issues.append({
                'level': 'ERROR',
                'message': '양도가액이 취득가액보다 낮습니다',
                'field': 'disposal_price'
            })

        # 2. 세율 적용 검증
        expected_rate = self.calculate_expected_rate(
            calculation['taxable_income']
        )
        if abs(calculation['applied_rate'] - expected_rate) > 0.01:
            issues.append({
                'level': 'WARNING',
                'message': f'세율 불일치 (예상: {expected_rate}, 적용: {calculation["applied_rate"]})',
                'field': 'tax_rate'
            })

        # 3. 유사 케이스 비교
        similar_cases = await self.find_similar_cases(calculation)
        deviation = self.calculate_deviation(calculation, similar_cases)

        if deviation > 0.2:  # 20% 이상 차이
            issues.append({
                'level': 'WARNING',
                'message': f'유사 케이스 대비 {deviation*100:.1f}% 차이',
                'similar_cases': similar_cases[:3]
            })

        # 4. 세법 조항 검증
        law_check = await self.verify_law_application(
            calculation,
            law_refs
        )
        issues.extend(law_check)

        return {
            'status': 'PASS' if not any(i['level'] == 'ERROR' for i in issues) else 'FAIL',
            'issues': issues,
            'confidence': self.calculate_confidence(issues)
        }
```

#### 착오류 방지 시스템
```python
class ErrorPreventionSystem:
    """착오류 통계 기반 검증"""

    def __init__(self):
        self.error_patterns = self.load_error_patterns()

    async def check_common_errors(self, calculation: dict):
        """과거 자주 발생한 오류 체크"""

        alerts = []

        # 패턴 1: 1세대1주택 비과세 누락
        if (calculation['is_primary_residence']
            and calculation['holding_years'] >= 2
            and calculation['total_tax'] > 0):
            alerts.append({
                'pattern': '1세대1주택 비과세 누락 가능성',
                'check': '2년 보유/거주 요건 확인 필요'
            })

        # 패턴 2: 장특공 과다 적용
        max_ltc = self.calculate_max_ltc_rate(calculation['holding_years'])
        if calculation['ltc_rate'] > max_ltc:
            alerts.append({
                'pattern': '장기보유특별공제 과다 적용',
                'check': f'최대 {max_ltc*100}% (현재: {calculation["ltc_rate"]*100}%)'
            })

        return alerts
```

---

### 📄 **에이전트 #4: 신고 (Filing Agent)**
**역할**: 최종 신고 및 문서 작성

#### 주요 기능

1. **신고서 작성**
   - 전자신고 (홈택스 연동)
   - 서면신고 양식 생성

2. **납부 안내**
   - 납부고지서 생성
   - 납부 기한 안내
   - 분할 납부 옵션

3. **증빙 서류 관리**
   - 수수료 안내문
   - 세금계산서/영수증
   - 신고 완료 리포트

#### 구현 예시
```python
class FilingAgent:
    """신고 에이전트"""

    async def prepare(self, calculation_result: dict):
        """신고 준비"""

        filing_package = {}

        # 1. 신고서 작성
        filing_package['tax_return'] = await self.generate_tax_return(
            calculation_result
        )

        # 2. 납부 안내
        filing_package['payment_notice'] = await self.generate_payment_notice(
            calculation_result['total_tax'],
            calculation_result['due_date']
        )

        # 3. 수수료 안내
        filing_package['fee_notice'] = self.calculate_service_fee(
            calculation_result['total_tax']
        )

        # 4. 최종 리포트
        filing_package['report'] = await self.generate_final_report(
            calculation_result
        )

        return filing_package

    async def submit_electronic_filing(self, filing_data: dict):
        """전자신고 제출 (홈택스 API)"""

        # 홈택스 연동 (향후 구현)
        response = await self.hometax_api.submit(filing_data)

        return {
            'status': response['status'],
            'receipt_number': response['receipt_number'],
            'submitted_at': datetime.now()
        }
```

---

## 정보 수집 파트 구분

### 1️⃣ **사실관계 정보** (에이전트 #1, #2 담당)

#### A. 자산 정보 (Asset Information)
- 거래 대상 자산의 물리적 정보
- 소유권 정보
- 거래 조건

#### B. 거래 정보 (Transaction Information)
- 취득/양도 가격
- 거래 일자
- 거래 방식

#### C. 납세자 정보 (Taxpayer Information)
- 보유 주택 수
- 거주 이력
- 세대 구성

### 2️⃣ **세법 정보** (총괄 에이전트 or 에이전트 #3 담당)

#### A. 세법 조문 (Tax Law Articles)
```python
# Vector DB에서 검색
law_search_results = await vector_db.search(
    query="1세대1주택 비과세 요건",
    collection="tax_law",
    top_k=5
)

# 관련 조문
# - 소득세법 제89조 (비과세 양도소득)
# - 소득세법 시행령 제154조 (1세대1주택 범위)
```

#### B. 세법 시행령 (Enforcement Decree)
- 세법 조문의 구체적 해석
- 적용 기준 및 예외 사항

#### C. 조세특례제한법 (Special Tax Treatment)
- 감면 조항
- 특례 적용 조건

#### D. 특수 케이스 판단
- 특수관계인 거래
- 증여 간주 여부
- 건축물 통산/비통산

---

## 에이전트 간 협업 흐름

### 전체 프로세스
```
[사용자 입력]
      ↓
┌─────────────────────────────────┐
│ 총괄 에이전트 (Orchestrator)     │
│ - 입력 분석                      │
│ - 워크플로우 계획                │
└─────────────────────────────────┘
      ↓
┌─────────────────────────────────┐
│ 에이전트 #1: 자산정보 수집        │
│ - 자연어 추출                    │
│ - 문서 OCR (사진/PDF)            │
│ - API 자동 조회                  │
└─────────────────────────────────┘
      ↓
┌─────────────────────────────────┐
│ 총괄 에이전트                    │
│ - 세법 조항 검색 (Vector DB)    │
│ - 적용 가능 법령 필터링          │
└─────────────────────────────────┘
      ↓
┌─────────────────────────────────┐
│ 에이전트 #2: 세액 산출           │
│ - 기본 계산                      │
│ - 시나리오 시뮬레이션            │
│ - 보고서 생성                    │
└─────────────────────────────────┘
      ↓
┌─────────────────────────────────┐
│ 에이전트 #3: 계산 검증           │
│ - 계산 로직 검증                 │
│ - 착오류 패턴 체크               │
│ - 유사 케이스 비교               │
└─────────────────────────────────┘
      ↓
    통과? ──No──> 재계산 or 세무사 검토
      │ Yes
      ↓
┌─────────────────────────────────┐
│ 에이전트 #4: 신고                │
│ - 신고서 작성                    │
│ - 납부 안내                      │
│ - 최종 리포트                    │
└─────────────────────────────────┘
      ↓
  [완료]
```

### 병렬 처리 최적화
```python
async def optimized_workflow(self, user_input: dict):
    """병렬 처리를 활용한 최적화된 워크플로우"""

    # Step 1: 자산 정보 수집
    assets = await self.asset_collector.collect(user_input)

    # Step 2: 병렬 실행 (독립적인 작업)
    calculation, law_refs, similar_cases = await asyncio.gather(
        self.tax_calculator.calculate(assets),        # 계산
        self.search_applicable_laws(assets),          # 세법 검색
        self.find_similar_cases(assets)               # 유사 케이스
    )

    # Step 3: 검증 (위 결과 필요)
    verification = await self.verifier.verify(
        calculation,
        law_refs,
        similar_cases
    )

    # Step 4: 신고 준비
    if verification['status'] == 'PASS':
        filing = await self.filing.prepare(calculation)
        return filing
    else:
        return verification  # 오류 리포트 반환
```

---

## 구현 로드맵

### 📅 Phase 1: 현재 상태 (MVP) - 완료
- ✅ 단일 에이전트 (TaxAdvisorAgent)
- ✅ 기본 정보 수집
- ✅ 세액 계산 (TaxCalculator)
- ✅ 간단한 리포트 생성

### 📅 Phase 2: 멀티 에이전트 전환 (2-3개월)
```
Month 1-2:
□ 총괄 에이전트 구현
  - 워크플로우 매니저
  - 에이전트 조율 로직

□ 에이전트 #1: 자산정보 수집
  - OCR 통합 (Tesseract/Google Vision)
  - API 연동 (국토부 실거래가)

Month 2-3:
□ 에이전트 #3: 계산 검증
  - 착오류 패턴 DB 구축
  - 유사 케이스 검색 (Vector DB)

□ 에이전트 #4: 신고
  - 신고서 양식 생성
  - 납부 안내 자동화
```

### 📅 Phase 3: 고도화 (4-6개월)
```
Month 4-5:
□ 세법 Vector DB 구축
  - 소득세법 임베딩
  - 세법 시행령 임베딩
  - 조세특례제한법 임베딩

□ 총괄 에이전트 고도화
  - 세법 적용 자동 판단
  - 특수 케이스 처리

Month 5-6:
□ 학습 시스템
  - 과거 케이스 학습
  - 정확도 지속 개선

□ 세무사 검토 대시보드
  - 검토 대기 큐
  - 승인/수정 워크플로우
```

---

## 기술 스택

### 1. LLM (Large Language Model)
```python
# OpenAI GPT-4 (추천)
from openai import OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 또는 Anthropic Claude
from anthropic import Anthropic
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
```

### 2. 에이전트 프레임워크
```python
# LangChain - 에이전트 구축
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.tools import Tool

# LangGraph - 복잡한 워크플로우
from langgraph.graph import StateGraph, END
```

### 3. Vector Database (세법 검색)
```python
# Pinecone (관리형)
from pinecone import Pinecone
pc = Pinecone(api_key="...")
index = pc.Index("tax-law")

# 또는 Qdrant (오픈소스)
from qdrant_client import QdrantClient
client = QdrantClient(url="http://localhost:6333")
```

### 4. OCR (문서 인식)
```python
# Google Cloud Vision API
from google.cloud import vision
client = vision.ImageAnnotatorClient()

# 또는 Tesseract (오픈소스)
import pytesseract
from PIL import Image
text = pytesseract.image_to_string(Image.open('document.jpg'), lang='kor')

# 또는 AWS Textract
import boto3
textract = boto3.client('textract')
```

### 5. API 연동
```python
# 국토부 실거래가 API
import httpx

async def fetch_real_price(address: str, date: str):
    url = "http://openapi.molit.go.kr/..."
    params = {
        'serviceKey': os.getenv('MOLIT_API_KEY'),
        'address': address,
        'dealDate': date
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        return response.json()
```

### 6. 데이터베이스
```python
# PostgreSQL - 메인 DB
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine("postgresql://user:pass@localhost/ysz")
Session = sessionmaker(bind=engine)

# Vector DB - 세법/케이스 검색
# (Pinecone 또는 Qdrant 사용)
```

---

## 예상 성능

### 처리 속도
- **정보 수집**: 10-30초 (OCR 포함)
- **세액 계산**: 2-5초
- **검증**: 5-10초
- **전체 프로세스**: 1-2분

### 정확도 목표
- **계산 정확도**: 99.5% 이상
- **세법 적용**: 95% 이상 (복잡한 케이스 제외)
- **착오류 감지**: 90% 이상

### 확장성
- **동시 처리**: 100+ 케이스
- **일일 처리량**: 1,000+ 건
- **응답 시간**: 95 percentile < 3분

---

## 향후 확장 계획

### 추가 기능
1. **다국어 지원** (영어, 중국어)
2. **음성 인터페이스** (음성 → 텍스트 → 처리)
3. **실시간 상담** (챗봇 형태)
4. **모바일 앱** (사진 촬영 → 즉시 계산)

### 추가 에이전트
- **상담 에이전트**: 실시간 Q&A
- **학습 에이전트**: 지속적 성능 개선
- **감사 에이전트**: 신고 후 사후 관리

---

## 참고 자료

### 프레임워크 문서
- **LangChain**: https://python.langchain.com/
- **LangGraph**: https://github.com/langchain-ai/langgraph
- **AutoGen**: https://microsoft.github.io/autogen/

### OCR 솔루션
- **Google Cloud Vision**: https://cloud.google.com/vision
- **Tesseract OCR**: https://github.com/tesseract-ocr/tesseract
- **AWS Textract**: https://aws.amazon.com/textract/

### Vector Database
- **Pinecone**: https://www.pinecone.io/
- **Qdrant**: https://qdrant.tech/
- **Weaviate**: https://weaviate.io/

### API
- **국토교통부 실거래가**: https://www.data.go.kr/
- **홈택스 API**: https://www.hometax.go.kr/
