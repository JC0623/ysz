# YSZ 테스팅 가이드

**목적**: Phase 2.5 Part 1 (StrategyAgent API + 프론트엔드) 테스트

**작성일**: 2025-11-22

---

## 1. 백엔드 서버 실행

### 1.1 환경 설정

```bash
cd c:\Users\next0\claude-test\ysz\YSZ

# 가상환경 활성화 (있는 경우)
# Windows
.\venv\Scripts\activate

# 의존성 확인
pip install -r requirements.txt
```

### 1.2 환경 변수 설정

**`.env` 파일 생성** (프로젝트 루트):

```env
# Claude API Key (선택사항, LLM 설명 생성 시 필요)
ANTHROPIC_API_KEY=sk-ant-...

# Database
DATABASE_URL=sqlite:///./ysz.db

# API 설정
API_HOST=0.0.0.0
API_PORT=8000
```

### 1.3 서버 실행

```bash
# FastAPI 서버 실행
cd src
python -m api.main

# 또는 uvicorn 직접 실행
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

**확인**:
- 서버가 시작되면: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`

---

## 2. StrategyAgent API 테스트

### 2.1 Swagger UI 사용 (추천)

브라우저에서 `http://localhost:8000/docs` 접속

**테스트 순서**:

1. **Health Check**: `GET /api/v1/strategy/health`
   - 예상 응답:
     ```json
     {
       "status": "healthy",
       "llm_enabled": true,
       "rule_registry": "loaded"
     }
     ```

2. **카테고리 목록**: `GET /api/v1/strategy/categories`
   - 예상 응답:
     ```json
     {
       "categories": [
         {"code": "1주택_비과세", "name": "1주택 비과세"},
         {"code": "1주택_과세", "name": "1주택 과세"},
         {"code": "다주택_일반", "name": "다주택 일반"},
         ...
       ]
     }
     ```

3. **전략 분석**: `POST /api/v1/strategy/analyze`

### 2.2 테스트 케이스

#### 테스트 1: 1주택 비과세 (성공 케이스)

**요청**:
```json
{
  "acquisition_date": "2020-01-15",
  "acquisition_price": 500000000,
  "disposal_date": "2024-12-01",
  "disposal_price": 1000000000,
  "asset_type": "residential",
  "house_count": 1,
  "residence_period_years": 3,
  "is_adjusted_area": false,
  "necessary_expenses": 0,
  "enable_explanation": true
}
```

**예상 응답**:
```json
{
  "category": "1주택_비과세",
  "category_description": "1주택 비과세",
  "classification_reasoning": "보유 주택 수: 1채\n보유 기간: 4.9년\n거주 기간: 3년\n조정대상지역: 아니오",
  "scenarios": [
    {
      "scenario_id": "SC_NOW",
      "scenario_name": "지금 바로 양도",
      "disposal_date": "2024-12-01",
      "expected_tax": 0,
      "net_benefit": 1000000000,
      "is_recommended": true,
      "pros": ["비과세 혜택", "즉시 현금화"],
      "cons": []
    }
  ],
  "recommended_scenario_id": "SC_NOW",
  "risks": [],
  "llm_explanation": "1세대 1주택으로 보유기간 2년 이상, 거주기간 2년 이상 조건을 충족하여 비과세 대상입니다...",
  "analyzed_at": "2024-11-22T...",
  "agent_version": "1.0.0"
}
```

#### 테스트 2: 다주택 중과세

**요청**:
```json
{
  "acquisition_date": "2022-06-15",
  "acquisition_price": 800000000,
  "disposal_date": "2024-12-01",
  "disposal_price": 1200000000,
  "asset_type": "residential",
  "house_count": 3,
  "residence_period_years": 0,
  "is_adjusted_area": true,
  "necessary_expenses": 10000000,
  "enable_explanation": true
}
```

**예상 결과**:
- `category`: "다주택_중과세" 또는 "조정지역_중과세"
- `expected_tax`: > 0 (중과세율 적용)
- `risks`: 고액 세금, 단기 보유 등

#### 테스트 3: 1주택 과세 (비과세 요건 미달)

**요청**:
```json
{
  "acquisition_date": "2023-06-15",
  "acquisition_price": 600000000,
  "disposal_date": "2024-12-01",
  "disposal_price": 900000000,
  "asset_type": "residential",
  "house_count": 1,
  "residence_period_years": 1,
  "is_adjusted_area": false,
  "necessary_expenses": 5000000,
  "enable_explanation": true
}
```

**예상 결과**:
- `category`: "1주택_과세"
- `expected_tax`: > 0
- `risks`: 거주 기간 부족

### 2.3 cURL 명령어 테스트

```bash
# Health Check
curl http://localhost:8000/api/v1/strategy/health

# 카테고리 목록
curl http://localhost:8000/api/v1/strategy/categories

# 전략 분석
curl -X POST http://localhost:8000/api/v1/strategy/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "acquisition_date": "2020-01-15",
    "acquisition_price": 500000000,
    "disposal_date": "2024-12-01",
    "disposal_price": 1000000000,
    "asset_type": "residential",
    "house_count": 1,
    "residence_period_years": 3,
    "is_adjusted_area": false,
    "necessary_expenses": 0,
    "enable_explanation": true
  }'
```

---

## 3. 프론트엔드 테스트

### 3.1 프론트엔드 실행

```bash
cd frontend

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev
```

**확인**:
- 브라우저에서 `http://localhost:5173` (또는 Vite가 지정한 포트)

### 3.2 E2E 테스트 시나리오

#### 시나리오 1: 전체 플로우

1. **Step 0: 정보 입력**
   - 취득일: 2020-01-15
   - 취득가액: 500,000,000원
   - 양도일: 2024-12-01
   - 양도가액: 1,000,000,000원
   - 자산 유형: 주거용
   - 주택 수: 1채
   - 거주 기간: 3년
   - 조정대상지역: 아니오
   - [다음] 클릭

2. **Step 1: 사실관계 확인**
   - 타임라인 확인
   - 사실관계 테이블 확인
   - 모든 항목 체크
   - [계산 진행] 클릭

3. **Step 2: 계산**
   - 진행 바 확인 (0% → 100%)
   - 자동으로 Step 3로 이동

4. **Step 3: 결과 표시**
   - 계산 결과 확인
   - 스크롤 다운

5. **전략 분석 패널**
   - [분석 시작] 버튼 클릭
   - 로딩 스피너 확인
   - 결과 표시:
     - ✅ 케이스 분류: "1주택_비과세"
     - ✅ AI 설명 (Claude 생성)
     - ✅ 시나리오 비교 테이블
     - ✅ 추천 시나리오 (별 표시)
     - ✅ 리스크 분석 (없음 또는 낮음)
     - ✅ 법적 고지

### 3.3 UI 확인 사항

#### StrategyPanel 컴포넌트

- [ ] "분석 시작" 버튼이 보이는가?
- [ ] 버튼 클릭 시 로딩 스피너가 나타나는가?
- [ ] 케이스 분류가 파란색 Tag로 표시되는가?
- [ ] AI 설명이 정보 Alert에 표시되는가?
- [ ] 시나리오 테이블이 올바르게 렌더링되는가?
- [ ] 추천 시나리오에 별(⭐) 아이콘이 있는가?
- [ ] 추천 행이 노란색 배경(#fffbe6)으로 하이라이트되는가?
- [ ] 리스크가 있으면 색상별 Alert가 표시되는가?
- [ ] 법적 고지 Alert가 맨 아래 표시되는가?

---

## 4. 통합 테스트

### 4.1 시스템 전체 플로우

```
사용자 입력 (브라우저)
    ↓
[Frontend] DataInputStep
    ↓ POST /api/v1/facts/collect
[Backend] FactCollector
    ↓
[Frontend] FactConfirmationStep
    ↓ POST /api/v1/facts/{id}/confirm
[Backend] FactLedger 확정
    ↓
[Frontend] CalculationStep
    ↓ POST /api/v1/calculate/{id}
[Backend] TaxCalculator
    ↓
[Frontend] ResultDisplayStep
    ↓
[Frontend] StrategyPanel 렌더링
    ↓ (사용자가 "분석 시작" 클릭)
    ↓ POST /api/v1/strategy/analyze
[Backend] StrategyAgent 실행
    ├─ 케이스 분류 (결정론적)
    ├─ 시나리오 생성 (TaxCalculator)
    ├─ 추천 로직
    └─ LLM 설명 생성 (Claude)
    ↓
[Frontend] 전략 분석 결과 표시
```

### 4.2 체크리스트

**백엔드**:
- [ ] 서버가 정상적으로 시작되는가?
- [ ] `/docs`에서 Swagger UI가 보이는가?
- [ ] `/api/v1/strategy/health`가 응답하는가?
- [ ] `/api/v1/strategy/analyze`가 정상 작동하는가?
- [ ] LLM 설명이 생성되는가? (ANTHROPIC_API_KEY 설정 시)
- [ ] 오류 발생 시 적절한 에러 메시지가 반환되는가?

**프론트엔드**:
- [ ] 페이지가 정상적으로 로드되는가?
- [ ] 4단계 마법사가 순차적으로 작동하는가?
- [ ] StrategyPanel이 Step 4 이후에 표시되는가?
- [ ] API 호출이 성공하는가?
- [ ] 로딩 상태가 올바르게 표시되는가?
- [ ] 결과가 올바르게 렌더링되는가?
- [ ] 반응형 디자인이 작동하는가?

**통합**:
- [ ] CORS가 올바르게 설정되어 있는가?
- [ ] API 응답이 프론트엔드 스키마와 일치하는가?
- [ ] 에러 핸들링이 적절한가?
- [ ] 성능이 만족스러운가? (응답 시간 < 3초)

---

## 5. 일반적인 문제 해결

### 5.1 백엔드 오류

#### 오류 1: `ImportError: No module named 'anthropic'`
**해결**:
```bash
pip install anthropic
```

#### 오류 2: `ANTHROPIC_API_KEY not found`
**해결**:
- `.env` 파일에 API 키 추가
- 또는 `enable_llm=false`로 설정 (API 코드 수정)

#### 오류 3: `StrategyAgent not found`
**해결**:
```bash
# 모듈 경로 확인
cd src
python -c "from agents.strategy_agent import StrategyAgent; print('OK')"
```

### 5.2 프론트엔드 오류

#### 오류 1: `Cannot GET /api/v1/strategy/analyze`
**해결**:
- 백엔드 서버가 실행 중인지 확인
- CORS 설정 확인
- 프론트엔드 프록시 설정 확인 (`vite.config.ts`)

#### 오류 2: `TypeError: Cannot read property 'map' of undefined`
**해결**:
- API 응답 구조 확인
- null/undefined 체크 추가

#### 오류 3: 스타일이 깨짐
**해결**:
- Ant Design CSS import 확인
- 브라우저 캐시 삭제

### 5.3 성능 문제

#### 문제: API 응답이 느림 (> 5초)
**원인**:
- LLM 호출 (Claude API)이 느림

**해결**:
1. `enable_explanation=false`로 테스트
2. Claude API 대신 미리 작성된 템플릿 사용
3. 비동기 처리 추가

---

## 6. 테스트 결과 기록

### 6.1 테스트 로그

**날짜**: 2025-11-22

| 테스트 케이스 | 상태 | 비고 |
|-------------|------|------|
| 백엔드 서버 시작 | ⏳ | |
| Health Check | ⏳ | |
| 카테고리 목록 | ⏳ | |
| 전략 분석 (1주택 비과세) | ⏳ | |
| 전략 분석 (다주택 중과세) | ⏳ | |
| 프론트엔드 실행 | ⏳ | |
| E2E 시나리오 1 | ⏳ | |
| StrategyPanel UI | ⏳ | |

### 6.2 발견된 버그

| ID | 설명 | 우선순위 | 상태 |
|----|------|---------|------|
| - | - | - | - |

---

## 7. 다음 단계

테스트 완료 후:

1. **버그 수정**
   - 발견된 오류 수정
   - 단위 테스트 추가

2. **성능 최적화**
   - LLM 호출 캐싱
   - API 응답 시간 단축

3. **Phase 2.5 Part 2**
   - OrchestratorAgent 강화
   - VerificationAgent 구현

---

**문서 버전**: v1.0
**작성자**: Claude Code
**다음 업데이트**: 테스트 완료 후
