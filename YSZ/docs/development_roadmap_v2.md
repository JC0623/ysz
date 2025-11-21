# YSZ 프로젝트 개발 로드맵 v2.0 (2025)

## 프로젝트 비전

YSZ는 **4대 핵심 축**으로 고도화됩니다:

1. **구조 설계** (계산 엔진) ✅ 완료
2. **실제 사례 학습** (케이스 데이터베이스) 🔄 진행 예정
3. **관리자 친화** (유지보수성) 🎯 목표
4. **사용자 친화** (극도로 심플한 UX/UI) 🎯 목표

---

## 프로젝트 현황 (2025-11-22 기준)

### ✅ 완료된 항목 (Phase 1 & 2)

- **Phase 1: 핵심 계산 엔진** (100% 완료)
  - [x] TaxCalculator: 양도소득세 계산 로직
  - [x] RuleEngine: 세법 규칙 관리 (YAML 기반)
  - [x] Fact/FactLedger: 불변 데이터 구조
  - [x] CalculationTrace: 계산 과정 추적

- **Phase 2: AI 에이전트 시스템** (100% 완료)
  - [x] BaseAgent & AgentProtocol
  - [x] RuleVersion & RuleRegistry
  - [x] StrategyAgent (케이스 분류, 시나리오 생성, 리스크 분석)
  - [x] Claude 3.5 Sonnet 통합 (선택적 설명 생성)
  - [x] 17+8 테스트, 7 예제, 4 문서

- **백엔드 API** (70% 완료)
  - [x] FastAPI 기반 REST API
  - [x] /api/v1/facts - 사실관계 수집/확인
  - [x] /api/v1/calculate - 세금 계산
  - [ ] /api/v1/strategy - 전략 분석 (Phase 2.5)

- **프론트엔드** (60% 완료)
  - [x] 4단계 마법사 UI (React + Ant Design)
  - [x] 데이터 입력 폼
  - [x] 사실관계 확인 페이지
  - [x] 계산 진행 표시
  - [x] 결과 표시 페이지
  - [ ] 전략 분석 패널 (Phase 2.5)

---

## 🎯 Phase 2.5: 프론트엔드 통합 & Orchestrator (즉시 시작)

**목표**: StrategyAgent를 프론트엔드에 노출하고 전체 워크플로우 통합

**기간**: 1-2주

### 2.5.1 StrategyAgent API 노출

**파일**: `src/api/routers/strategy.py` (신규)

**엔드포인트**:

```python
POST /api/v1/strategy/analyze
  - Request: { facts: {...}, enable_explanation: bool }
  - Response: { category, scenarios, recommended_scenario_id, llm_explanation }

GET /api/v1/strategy/categories
  - Response: 케이스 카테고리 목록

POST /api/v1/strategy/compare
  - Request: { ledger, scenarios }
  - Response: 시나리오 비교표
```

**작업 항목**:
- [ ] strategy.py 라우터 생성
- [ ] StrategyAgent 의존성 주입
- [ ] Request/Response 스키마 정의
- [ ] 에러 처리
- [ ] API 문서 (Swagger)

**예상 소요 시간**: 1-2일

---

### 2.5.2 프론트엔드 전략 분석 UI

**파일**: `frontend/src/components/StrategyPanel.tsx` (신규)

**UI 구성**:

```
┌─────────────────────────────────────────┐
│  전략 분석                               │
├─────────────────────────────────────────┤
│  📊 케이스 분류                          │
│  [1세대 1주택 - 비과세]                  │
│                                         │
│  💡 AI 설명                              │
│  보유 2년, 거주 2년 충족으로 비과세      │
│  대상입니다. 지금 양도하시면...          │
│                                         │
│  📈 시나리오 비교                        │
│  ┌─────────┬─────────┬─────────┐       │
│  │시나리오  │예상세액  │순편익   │       │
│  ├─────────┼─────────┼─────────┤       │
│  │지금 양도 │0원      │10억     │ ⭐    │
│  │1년후양도 │0원      │9.8억    │       │
│  └─────────┴─────────┴─────────┘       │
│                                         │
│  ✅ 추천: 지금 바로 양도                 │
│                                         │
│  [상세 보기] [다시 분석]                │
└─────────────────────────────────────────┘
```

**작업 항목**:
- [ ] StrategyPanel.tsx 컴포넌트 생성
- [ ] API 연동 (axios)
- [ ] 케이스 분류 뱃지
- [ ] LLM 설명 표시 (Alert)
- [ ] 시나리오 비교 테이블
- [ ] 추천 시나리오 하이라이트
- [ ] App.tsx에 통합 (Step 4 이후)

**예상 소요 시간**: 2-3일

---

### 2.5.3 OrchestratorAgent 강화

**파일**: `src/agents/orchestrator_agent.py` (기존 파일 수정)

**목표**: StrategyAgent를 워크플로우에 통합

**현재 워크플로우**:
```
Step 1: AssetCollectorAgent (정보 수집)
    ↓
Step 2: TaxCalculationAgent (세금 계산)
    ↓
Step 3: VerificationAgent (검증)
    ↓
Step 4: FilingAgent (신고서)
```

**개선된 워크플로우**:
```
Step 1: AssetCollectorAgent (정보 수집)
    ↓
Step 2: StrategyAgent (전략 분석) ← 추가
    ↓
Step 3: TaxCalculationAgent (세금 계산)
    ↓
Step 4: VerificationAgent (검증)
    ↓
Step 5: FilingAgent (신고서)
```

**작업 항목**:
- [ ] OrchestratorAgent에 StrategyAgent 추가
- [ ] Stage 2 추가 (전략 분석)
- [ ] Agent 간 데이터 전달 표준화
- [ ] AgentPlan/AgentResult 활용
- [ ] 에러 핸들링 및 Rollback

**예상 소요 시간**: 2-3일

---

### 2.5.4 VerificationAgent 구현

**파일**: `src/agents/verification_agent.py` (신규)

**목표**: 계산 결과 및 전략 검증

**검증 항목**:

1. **로직 검증**
   - StrategyAgent 결과 검증 (카테고리 분류 정확성)
   - TaxCalculator 결과 검증 (계산식 체크)
   - 시나리오 간 일관성 체크

2. **세법 버전 체크**
   - 최신 RuleVersion 적용 확인
   - 세법 개정 영향 분석

3. **착오류 체크**
   - 통계 기반 이상치 탐지
   - 과거 착오 사례와 비교

4. **리스크 플래그**
   - 고액 양도차익 (5억 이상)
   - 조정대상지역 중과세
   - 단기 보유 (2년 미만)
   - 다주택자

**출력**:
```python
{
  "status": "verified" | "warning" | "error",
  "checks": [
    {"name": "로직 검증", "status": "pass", "message": "OK"},
    {"name": "세법 버전", "status": "pass", "message": "2024.1.0 적용"}
  ],
  "risk_flags": [
    {
      "level": "high",
      "title": "고액 양도차익",
      "description": "양도차익 5억원 이상으로...",
      "recommendation": "세무사 상담 권장"
    }
  ],
  "confidence_score": 0.95
}
```

**작업 항목**:
- [ ] VerificationAgent 클래스
- [ ] 로직 검증 함수
- [ ] 세법 버전 체크
- [ ] 착오류 통계 DB (SQLite/PostgreSQL)
- [ ] 리스크 플래그 규칙 정의
- [ ] 단위 테스트

**예상 소요 시간**: 3-4일

---

## 🗂️ Phase 3: 케이스 학습 시스템 (핵심 2축)

**목표**: 실제 사례를 데이터베이스화하여 시스템 학습 및 검증

**입력 데이터 형식** (스프레드시트):

| 컬럼 | 설명 | 예시 |
|------|------|------|
| **case_id** | 케이스 고유 ID | CASE_2024_001 |
| **사실관계_취득일** | 취득일 | 2020-01-15 |
| **사실관계_취득가액** | 취득가액 | 500,000,000 |
| **사실관계_양도일** | 양도일 | 2024-12-01 |
| **사실관계_양도가액** | 양도가액 | 1,000,000,000 |
| **사실관계_주택수** | 보유 주택 수 | 1 |
| **사실관계_거주기간** | 거주 기간 (년) | 3 |
| **사실관계_조정지역** | 조정대상지역 여부 | FALSE |
| **비교보고서_시나리오1** | 시나리오 1 설명 | 지금 양도 |
| **비교보고서_시나리오1_세액** | 시나리오 1 세액 | 0 |
| **비교보고서_시나리오2** | 시나리오 2 설명 | 1년 후 양도 |
| **비교보고서_시나리오2_세액** | 시나리오 2 세액 | 0 |
| **비교보고서_추천** | 추천 시나리오 | 시나리오1 |
| **계산근거_양도차익** | 양도차익 | 500,000,000 |
| **계산근거_장기보유공제** | 장기보유공제 | 80,000,000 |
| **계산근거_과세표준** | 과세표준 | 417,500,000 |
| **계산근거_산출세액** | 산출세액 | 0 |
| **신고서_신고일** | 실제 신고일 | 2025-02-15 |
| **신고서_납부세액** | 실제 납부세액 | 0 |
| **신고서_비고** | 비고 | 비과세 신고 |
| **리뷰_전략분류** | 전략 카테고리 | 1주택_비과세 |
| **리뷰_리스크** | 리스크 플래그 | 없음 |
| **리뷰_착오가능성** | 착오 가능성 | 낮음 |
| **리뷰_세무사코멘트** | 세무사 의견 | 비과세 요건 완벽 충족 |

### 3.1 케이스 데이터베이스 스키마

**파일**: `src/database/models.py` (확장)

**테이블 설계**:

```sql
-- 케이스 메타데이터
CREATE TABLE cases (
    case_id VARCHAR(50) PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    status VARCHAR(20), -- 'active', 'archived'
    source VARCHAR(50), -- '실제_사례', '테스트', '시뮬레이션'
    tax_year INT
);

-- 사실관계
CREATE TABLE case_facts (
    id SERIAL PRIMARY KEY,
    case_id VARCHAR(50) REFERENCES cases(case_id),
    field_name VARCHAR(100),
    field_value TEXT,
    value_type VARCHAR(20), -- 'date', 'decimal', 'boolean', 'string'
    source VARCHAR(50),
    confidence FLOAT
);

-- 비교 보고서
CREATE TABLE case_scenarios (
    id SERIAL PRIMARY KEY,
    case_id VARCHAR(50) REFERENCES cases(case_id),
    scenario_id VARCHAR(50),
    scenario_name VARCHAR(200),
    expected_tax DECIMAL(15, 2),
    net_benefit DECIMAL(15, 2),
    is_recommended BOOLEAN
);

-- 계산 근거
CREATE TABLE case_calculations (
    id SERIAL PRIMARY KEY,
    case_id VARCHAR(50) REFERENCES cases(case_id),
    calculation_step VARCHAR(100),
    calculated_value DECIMAL(15, 2),
    formula TEXT,
    rule_version VARCHAR(20)
);

-- 실제 신고서
CREATE TABLE case_filings (
    id SERIAL PRIMARY KEY,
    case_id VARCHAR(50) REFERENCES cases(case_id),
    filing_date DATE,
    filed_tax DECIMAL(15, 2),
    filing_status VARCHAR(50),
    notes TEXT
);

-- 리뷰 (전략 분해 및 로직화)
CREATE TABLE case_reviews (
    id SERIAL PRIMARY KEY,
    case_id VARCHAR(50) REFERENCES cases(case_id),
    strategy_category VARCHAR(50),
    risk_flags TEXT[], -- 배열
    error_probability VARCHAR(20),
    tax_advisor_comment TEXT,
    lessons_learned TEXT,
    reviewed_by VARCHAR(100),
    reviewed_at TIMESTAMP DEFAULT NOW()
);

-- 검증 결과 (시스템 vs 실제)
CREATE TABLE case_validations (
    id SERIAL PRIMARY KEY,
    case_id VARCHAR(50) REFERENCES cases(case_id),
    system_tax DECIMAL(15, 2),
    actual_tax DECIMAL(15, 2),
    difference DECIMAL(15, 2),
    difference_percent FLOAT,
    match_status VARCHAR(20), -- 'exact', 'close', 'mismatch'
    mismatch_reason TEXT,
    validated_at TIMESTAMP DEFAULT NOW()
);
```

### 3.2 케이스 임포트 API

**파일**: `src/api/routers/cases.py` (신규)

**엔드포인트**:

```python
POST /api/v1/cases/import
  - Request: { file: MultipartFile (Excel/CSV), format: "excel" | "csv" }
  - Response: { imported_count, errors: [...] }

GET /api/v1/cases
  - Request: { page, per_page, filter: {...} }
  - Response: { cases: [...], total, page }

GET /api/v1/cases/{case_id}
  - Response: 케이스 상세 정보

POST /api/v1/cases/{case_id}/validate
  - Response: 시스템 계산 vs 실제 결과 비교

GET /api/v1/cases/statistics
  - Response: 케이스 통계 (카테고리별, 세액별, 정확도)
```

**작업 항목**:
- [ ] cases.py 라우터 생성
- [ ] Excel/CSV 파싱 (pandas)
- [ ] 데이터 검증 및 정규화
- [ ] DB 저장 (SQLAlchemy)
- [ ] 케이스 조회 API
- [ ] 검증 API (시스템 vs 실제)
- [ ] 통계 API

**예상 소요 시간**: 4-5일

---

### 3.3 케이스 검증 및 학습

**목표**: 시스템 계산 결과와 실제 신고 결과 비교

**프로세스**:

```
스프레드시트 케이스 임포트
    ↓
1. 사실관계 추출 → FactLedger 생성
    ↓
2. 시스템 계산 (TaxCalculator + StrategyAgent)
    ↓
3. 실제 결과와 비교
    ├─ 일치: 정확도 향상 ✅
    └─ 불일치: 원인 분석 및 로직 개선 🔧
    ↓
4. 검증 결과 DB 저장
    ↓
5. 대시보드 표시 (정확도, 오차율)
```

**작업 항목**:
- [ ] 케이스 검증 함수
- [ ] 오차 분석 로직
- [ ] 불일치 원인 분류
- [ ] 학습 피드백 루프
- [ ] 관리자 대시보드 (통계)

**예상 소요 시간**: 3-4일

---

### 3.4 프론트엔드 케이스 관리 UI

**파일**: `frontend/src/pages/CaseManagement.tsx` (신규)

**UI 구성**:

```
┌─────────────────────────────────────────┐
│  케이스 관리                             │
├─────────────────────────────────────────┤
│  [파일 업로드] [템플릿 다운로드]          │
│                                         │
│  📊 통계                                 │
│  - 총 케이스: 127개                      │
│  - 정확도: 94.5%                         │
│  - 평균 오차: 2.3%                       │
│                                         │
│  📋 케이스 목록                          │
│  ┌────────┬──────┬────────┬──────┐     │
│  │케이스ID│카테고리│시스템세액│실제세액│     │
│  ├────────┼──────┼────────┼──────┤     │
│  │C001    │1주택 │0원     │0원  │✅   │
│  │C002    │다주택│1.2억   │1.25억│⚠️  │
│  │C003    │...   │...     │...  │     │
│  └────────┴──────┴────────┴──────┘     │
│                                         │
│  [필터] [내보내기] [통계 보기]           │
└─────────────────────────────────────────┘
```

**작업 항목**:
- [ ] CaseManagement.tsx 페이지
- [ ] 파일 업로드 컴포넌트
- [ ] 케이스 목록 테이블
- [ ] 통계 대시보드
- [ ] 케이스 상세 모달
- [ ] 검증 결과 시각화 (차트)

**예상 소요 시간**: 3-4일

---

## 📅 전체 개발 일정

### Phase 2.5: 프론트엔드 통합 (1-2주)

| 주차 | 작업 | 상태 |
|------|------|------|
| Week 1 | StrategyAgent API + 프론트엔드 UI | 🟡 예정 |
| Week 2 | OrchestratorAgent 강화 + VerificationAgent | 🟡 예정 |

**마일스톤**: Phase 2.5 완료 (전략 분석 프론트엔드 노출)

### Phase 3: 케이스 학습 시스템 (2-3주)

| 주차 | 작업 | 상태 |
|------|------|------|
| Week 3 | 데이터베이스 스키마 + 케이스 임포트 API | 🟡 예정 |
| Week 4 | 케이스 검증 로직 + 관리자 UI | 🟡 예정 |
| Week 5 | 통계 대시보드 + 피드백 루프 | 🟡 예정 |

**마일스톤**: Phase 3 완료 (케이스 학습 시스템 가동)

### Phase 4: 관리자 친화 & 사용자 친화 (1-2개월)

| 항목 | 세부 작업 |
|------|----------|
| **관리자 친화** | - 세법 규칙 YAML 편집 UI<br>- 케이스 수동 추가/수정<br>- 시스템 모니터링 대시보드<br>- 로그 조회 및 분석 |
| **사용자 친화** | - 1페이지 입력 폼 (마법사 → 단일)<br>- 자동 저장 및 복구<br>- 모바일 최적화<br>- 음성 입력 (선택)<br>- 극도로 단순한 UI |

---

## 🎯 즉시 시작할 작업 (Phase 2.5)

### Step 1: StrategyAgent API 구현 (1일)

```bash
# 파일 생성
touch src/api/routers/strategy.py

# 기본 구조
POST /api/v1/strategy/analyze
  - FactLedger 생성
  - StrategyAgent 실행
  - 결과 반환
```

### Step 2: 프론트엔드 StrategyPanel (2일)

```bash
# 파일 생성
touch frontend/src/components/StrategyPanel.tsx

# 컴포넌트 구조
- API 호출 (axios)
- 로딩 상태
- 결과 표시 (카테고리, 시나리오, 추천)
```

### Step 3: OrchestratorAgent 통합 (2일)

```bash
# 파일 수정
vim src/agents/orchestrator_agent.py

# Stage 2 추가
Stage 2: StrategyAgent 실행
  - 케이스 분류
  - 시나리오 생성
  - 추천 제시
```

### Step 4: VerificationAgent 구현 (3-4일)

```bash
# 파일 생성
touch src/agents/verification_agent.py

# 검증 로직
- 로직 검증
- 세법 버전 체크
- 리스크 플래그
```

---

## 📊 케이스 학습 시스템 준비 사항

### 스프레드시트 템플릿

**파일명**: `case_template.xlsx`

**시트 구성**:

1. **Sheet 1: 사실관계**
   - case_id, 취득일, 취득가액, 양도일, 양도가액, 주택수, 거주기간, 조정지역

2. **Sheet 2: 비교보고서**
   - case_id, 시나리오1, 시나리오1_세액, 시나리오2, 시나리오2_세액, 추천

3. **Sheet 3: 계산근거**
   - case_id, 양도차익, 장기보유공제, 과세표준, 산출세액

4. **Sheet 4: 신고서**
   - case_id, 신고일, 납부세액, 비고

5. **Sheet 5: 리뷰**
   - case_id, 전략분류, 리스크, 착오가능성, 세무사코멘트

**작업 항목**:
- [ ] 템플릿 Excel 파일 생성
- [ ] 예제 케이스 3개 작성
- [ ] 데이터 검증 규칙 추가
- [ ] 문서화

---

## 💾 영속성 보장 (클로드 코드 재시작 대비)

### 다음 세션에서 기억해야 할 핵심 정보

**파일**: `docs/session_memory.md` (신규)

```markdown
# 세션 메모리 (다음 클로드 코드 세션 참조)

## 프로젝트 현황
- Phase 2 완료 (StrategyAgent 100%)
- Phase 2.5 진행 중 (프론트엔드 통합)
- Phase 3 준비 중 (케이스 학습 시스템)

## 핵심 결정사항
1. ❌ ChatAgent 제외 (StrategyAgent로 충분)
2. ✅ StrategyAgent를 프론트엔드에 직접 노출
3. ✅ 케이스 학습 시스템이 두 번째 큰 축

## 4대 핵심 축
1. 구조 설계 (계산 엔진) ✅
2. 실제 사례 학습 (케이스 DB) 🔄
3. 관리자 친화 (유지보수) 🎯
4. 사용자 친화 (극단적 심플) 🎯

## 다음 작업
1. StrategyAgent API (/api/v1/strategy)
2. StrategyPanel.tsx (프론트엔드)
3. OrchestratorAgent 강화
4. VerificationAgent 구현
5. 케이스 DB 스키마 설계
6. 스프레드시트 임포트 시스템

## 케이스 데이터 형식
스프레드시트 5개 시트:
1. 사실관계 (취득일, 취득가액, ...)
2. 비교보고서 (시나리오1, 시나리오2, ...)
3. 계산근거 (양도차익, 장기보유공제, ...)
4. 신고서 (신고일, 납부세액, ...)
5. 리뷰 (전략분류, 리스크, 세무사코멘트)

## 중요한 파일
- docs/development_roadmap_v2.md (최신 로드맵)
- docs/session_memory.md (이 파일)
- docs/case_learning_spec.md (케이스 학습 명세)
```

---

## 결론

### Phase 2.5 목표 (1-2주)
✅ StrategyAgent를 프론트엔드에 노출
✅ OrchestratorAgent 강화
✅ VerificationAgent 구현

### Phase 3 목표 (2-3주)
✅ 케이스 학습 시스템 구축
✅ 스프레드시트 임포트
✅ 시스템 vs 실제 결과 검증
✅ 관리자 대시보드

### 최종 비전
**세무사가 실제 사례를 입력하면 시스템이 학습하고 정확도가 향상되는 Self-improving Tax System**

---

**문서 버전**: v2.0
**작성일**: 2025-11-22
**다음 리뷰**: Phase 2.5 완료 후
