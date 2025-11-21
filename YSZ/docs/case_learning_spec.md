# 케이스 학습 시스템 명세서 v1.0

**목적**: 실제 세무 사례를 시스템에 입력하여 학습 및 검증

**핵심 가치**: Self-improving Tax System (자가 개선 세금 시스템)

---

## 1. 시스템 개요

### 1.1 핵심 아이디어

```
실제 세무사례 입력 (스프레드시트)
    ↓
시스템 자동 계산 (TaxCalculator + StrategyAgent)
    ↓
실제 결과와 비교
    ├─ 일치 → 정확도 ✅
    └─ 불일치 → 원인 분석 및 로직 개선 🔧
    ↓
케이스 DB 축적
    ↓
유사 사례 검색 및 참조
    ↓
착오율 감소, 정확도 향상
```

### 1.2 케이스의 5가지 구성 요소

1. **사실관계** - 취득일, 취득가액, 양도일, 양도가액 등
2. **비교보고서** - 시나리오1 vs 시나리오2, 추천
3. **계산근거** - 양도차익, 장기보유공제, 과세표준, 산출세액
4. **실제 신고서** - 신고일, 납부세액, 비고
5. **리뷰** - 전략 분류, 리스크, 착오가능성, 세무사 코멘트

---

## 2. 스프레드시트 형식

### 2.1 파일 구조

**파일명**: `case_template.xlsx`

**시트 구성**:
- Sheet 1: 사실관계
- Sheet 2: 비교보고서
- Sheet 3: 계산근거
- Sheet 4: 신고서
- Sheet 5: 리뷰

### 2.2 Sheet 1: 사실관계

| 컬럼명 | 데이터 타입 | 필수 | 설명 | 예시 |
|--------|------------|------|------|------|
| case_id | VARCHAR(50) | ✅ | 케이스 고유 ID | CASE_2024_001 |
| 취득일 | DATE | ✅ | 자산 취득일 | 2020-01-15 |
| 취득가액 | DECIMAL | ✅ | 취득 가격 (원) | 500,000,000 |
| 양도일 | DATE | ✅ | 자산 양도일 | 2024-12-01 |
| 양도가액 | DECIMAL | ✅ | 양도 가격 (원) | 1,000,000,000 |
| 자산유형 | VARCHAR(20) | ✅ | residential, commercial, land | residential |
| 주택수 | INT | | 보유 주택 수 | 1 |
| 거주기간_년 | INT | | 거주 기간 (년) | 3 |
| 조정대상지역 | BOOLEAN | | 조정대상지역 여부 | FALSE |
| 취득비용 | DECIMAL | | 취득세, 중개수수료 등 | 5,000,000 |
| 처분비용 | DECIMAL | | 양도 관련 비용 | 3,000,000 |
| 개선비용 | DECIMAL | | 자본적 지출 | 0 |
| 필요경비 | DECIMAL | | 기타 필요경비 | 0 |
| 비고 | TEXT | | 특이사항 | 1세대 1주택, 실거주 |

**예시 데이터**:
```csv
case_id,취득일,취득가액,양도일,양도가액,자산유형,주택수,거주기간_년,조정대상지역,취득비용,처분비용,개선비용,필요경비,비고
CASE_2024_001,2020-01-15,500000000,2024-12-01,1000000000,residential,1,3,FALSE,5000000,3000000,0,0,1세대 1주택
```

### 2.3 Sheet 2: 비교보고서

| 컬럼명 | 데이터 타입 | 필수 | 설명 | 예시 |
|--------|------------|------|------|------|
| case_id | VARCHAR(50) | ✅ | 케이스 ID (FK) | CASE_2024_001 |
| 시나리오1_설명 | TEXT | ✅ | 시나리오 1 설명 | 지금 바로 양도 |
| 시나리오1_양도일 | DATE | | 시나리오 1 양도일 | 2024-12-01 |
| 시나리오1_예상세액 | DECIMAL | ✅ | 시나리오 1 세액 | 0 |
| 시나리오1_순편익 | DECIMAL | | 시나리오 1 순편익 | 1,000,000,000 |
| 시나리오2_설명 | TEXT | | 시나리오 2 설명 | 1년 후 양도 |
| 시나리오2_양도일 | DATE | | 시나리오 2 양도일 | 2025-12-01 |
| 시나리오2_예상세액 | DECIMAL | | 시나리오 2 세액 | 0 |
| 시나리오2_순편익 | DECIMAL | | 시나리오 2 순편익 | 980,000,000 |
| 추천시나리오 | VARCHAR(20) | ✅ | 추천 (시나리오1 or 시나리오2) | 시나리오1 |
| 추천근거 | TEXT | | 추천 근거 | 비과세 요건 충족, 조기 양도 유리 |

**예시 데이터**:
```csv
case_id,시나리오1_설명,시나리오1_양도일,시나리오1_예상세액,시나리오1_순편익,시나리오2_설명,시나리오2_양도일,시나리오2_예상세액,시나리오2_순편익,추천시나리오,추천근거
CASE_2024_001,지금 바로 양도,2024-12-01,0,1000000000,1년 후 양도,2025-12-01,0,980000000,시나리오1,비과세 요건 충족
```

### 2.4 Sheet 3: 계산근거

| 컬럼명 | 데이터 타입 | 필수 | 설명 | 예시 |
|--------|------------|------|------|------|
| case_id | VARCHAR(50) | ✅ | 케이스 ID (FK) | CASE_2024_001 |
| 양도가액 | DECIMAL | ✅ | 양도 가격 | 1,000,000,000 |
| 취득가액 | DECIMAL | ✅ | 취득 가격 | 500,000,000 |
| 양도차익 | DECIMAL | ✅ | 양도가액 - 취득가액 | 500,000,000 |
| 필요경비_합계 | DECIMAL | | 총 필요경비 | 8,000,000 |
| 장기보유공제 | DECIMAL | ✅ | 장기보유특별공제 | 80,000,000 |
| 장기보유공제율 | FLOAT | | 공제율 (%) | 16.0 |
| 기본공제 | DECIMAL | | 기본공제 (연 250만원) | 2,500,000 |
| 과세표준 | DECIMAL | ✅ | 양도소득 - 공제 | 409,500,000 |
| 적용세율 | FLOAT | ✅ | 세율 (%) | 0.0 |
| 산출세액 | DECIMAL | ✅ | 과세표준 × 세율 | 0 |
| 지방소득세 | DECIMAL | | 산출세액 × 10% | 0 |
| 총납부세액 | DECIMAL | ✅ | 산출세액 + 지방소득세 | 0 |
| 비과세사유 | TEXT | | 비과세 사유 | 1세대 1주택, 보유 2년 이상 |

**예시 데이터**:
```csv
case_id,양도가액,취득가액,양도차익,필요경비_합계,장기보유공제,장기보유공제율,기본공제,과세표준,적용세율,산출세액,지방소득세,총납부세액,비과세사유
CASE_2024_001,1000000000,500000000,500000000,8000000,80000000,16.0,2500000,409500000,0.0,0,0,0,1세대 1주택
```

### 2.5 Sheet 4: 신고서

| 컬럼명 | 데이터 타입 | 필수 | 설명 | 예시 |
|--------|------------|------|------|------|
| case_id | VARCHAR(50) | ✅ | 케이스 ID (FK) | CASE_2024_001 |
| 신고일 | DATE | ✅ | 실제 신고일 | 2025-02-15 |
| 신고유형 | VARCHAR(50) | | 예정신고, 확정신고 | 예정신고 |
| 신고세액 | DECIMAL | ✅ | 신고한 세액 | 0 |
| 납부세액 | DECIMAL | ✅ | 실제 납부한 세액 | 0 |
| 신고방법 | VARCHAR(50) | | 전자신고, 서면신고 | 전자신고 |
| 신고결과 | VARCHAR(50) | | 정상, 수정, 경정 | 정상 |
| 비고 | TEXT | | 특이사항 | 비과세 신고 완료 |

**예시 데이터**:
```csv
case_id,신고일,신고유형,신고세액,납부세액,신고방법,신고결과,비고
CASE_2024_001,2025-02-15,예정신고,0,0,전자신고,정상,비과세 신고 완료
```

### 2.6 Sheet 5: 리뷰 (전략 분해 및 로직화)

| 컬럼명 | 데이터 타입 | 필수 | 설명 | 예시 |
|--------|------------|------|------|------|
| case_id | VARCHAR(50) | ✅ | 케이스 ID (FK) | CASE_2024_001 |
| 전략분류 | VARCHAR(50) | ✅ | 케이스 카테고리 | 1주택_비과세 |
| 리스크수준 | VARCHAR(20) | ✅ | 없음, 낮음, 중간, 높음 | 없음 |
| 리스크플래그 | TEXT | | 리스크 플래그 (쉼표 구분) | - |
| 착오가능성 | VARCHAR(20) | ✅ | 낮음, 중간, 높음 | 낮음 |
| 착오예상항목 | TEXT | | 착오 가능 항목 | - |
| 세무사코멘트 | TEXT | ✅ | 세무사 의견 | 비과세 요건 완벽 충족 |
| 학습포인트 | TEXT | | 이 케이스에서 배울 점 | 거주기간 확인 중요 |
| 유사케이스 | TEXT | | 유사 케이스 ID | CASE_2023_045 |
| 작성자 | VARCHAR(100) | | 리뷰 작성자 | 김세무사 |
| 작성일 | DATE | | 리뷰 작성일 | 2025-02-20 |

**예시 데이터**:
```csv
case_id,전략분류,리스크수준,리스크플래그,착오가능성,착오예상항목,세무사코멘트,학습포인트,유사케이스,작성자,작성일
CASE_2024_001,1주택_비과세,없음,-,낮음,-,비과세 요건 완벽 충족,거주기간 확인 중요,CASE_2023_045,김세무사,2025-02-20
```

---

## 3. 데이터베이스 스키마

### 3.1 ERD

```
cases (케이스 메타)
  ├─ case_facts (사실관계)
  ├─ case_scenarios (비교보고서)
  ├─ case_calculations (계산근거)
  ├─ case_filings (신고서)
  ├─ case_reviews (리뷰)
  └─ case_validations (검증 결과)
```

### 3.2 테이블 정의

#### Table: cases
```sql
CREATE TABLE cases (
    case_id VARCHAR(50) PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'active', -- 'active', 'archived'
    source VARCHAR(50), -- '실제_사례', '테스트', '시뮬레이션'
    tax_year INT,
    description TEXT
);
```

#### Table: case_facts
```sql
CREATE TABLE case_facts (
    id SERIAL PRIMARY KEY,
    case_id VARCHAR(50) REFERENCES cases(case_id) ON DELETE CASCADE,
    field_name VARCHAR(100) NOT NULL,
    field_value TEXT,
    value_type VARCHAR(20), -- 'date', 'decimal', 'boolean', 'string', 'int'
    source VARCHAR(50) DEFAULT 'spreadsheet',
    confidence FLOAT DEFAULT 1.0,
    is_confirmed BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_case_facts_case_id ON case_facts(case_id);
CREATE INDEX idx_case_facts_field_name ON case_facts(field_name);
```

#### Table: case_scenarios
```sql
CREATE TABLE case_scenarios (
    id SERIAL PRIMARY KEY,
    case_id VARCHAR(50) REFERENCES cases(case_id) ON DELETE CASCADE,
    scenario_id VARCHAR(50) NOT NULL, -- 'SC1', 'SC2'
    scenario_name VARCHAR(200),
    disposal_date DATE,
    expected_tax DECIMAL(15, 2),
    net_benefit DECIMAL(15, 2),
    is_recommended BOOLEAN DEFAULT FALSE,
    reasoning TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_case_scenarios_case_id ON case_scenarios(case_id);
```

#### Table: case_calculations
```sql
CREATE TABLE case_calculations (
    id SERIAL PRIMARY KEY,
    case_id VARCHAR(50) REFERENCES cases(case_id) ON DELETE CASCADE,
    calculation_step VARCHAR(100), -- '양도차익', '장기보유공제', '과세표준', '산출세액'
    calculated_value DECIMAL(15, 2),
    formula TEXT,
    rule_version VARCHAR(20),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_case_calculations_case_id ON case_calculations(case_id);
```

#### Table: case_filings
```sql
CREATE TABLE case_filings (
    id SERIAL PRIMARY KEY,
    case_id VARCHAR(50) REFERENCES cases(case_id) ON DELETE CASCADE,
    filing_date DATE NOT NULL,
    filing_type VARCHAR(50), -- '예정신고', '확정신고'
    filed_tax DECIMAL(15, 2),
    paid_tax DECIMAL(15, 2),
    filing_method VARCHAR(50), -- '전자신고', '서면신고'
    filing_status VARCHAR(50), -- '정상', '수정', '경정'
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_case_filings_case_id ON case_filings(case_id);
```

#### Table: case_reviews
```sql
CREATE TABLE case_reviews (
    id SERIAL PRIMARY KEY,
    case_id VARCHAR(50) REFERENCES cases(case_id) ON DELETE CASCADE,
    strategy_category VARCHAR(50), -- '1주택_비과세', '다주택_중과세' 등
    risk_level VARCHAR(20), -- '없음', '낮음', '중간', '높음'
    risk_flags TEXT[], -- PostgreSQL 배열
    error_probability VARCHAR(20), -- '낮음', '중간', '높음'
    error_items TEXT,
    tax_advisor_comment TEXT,
    lessons_learned TEXT,
    similar_cases TEXT[], -- 유사 케이스 ID 배열
    reviewed_by VARCHAR(100),
    reviewed_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_case_reviews_case_id ON case_reviews(case_id);
CREATE INDEX idx_case_reviews_strategy_category ON case_reviews(strategy_category);
```

#### Table: case_validations
```sql
CREATE TABLE case_validations (
    id SERIAL PRIMARY KEY,
    case_id VARCHAR(50) REFERENCES cases(case_id) ON DELETE CASCADE,

    -- 시스템 계산 결과
    system_category VARCHAR(50),
    system_tax DECIMAL(15, 2),
    system_recommended_scenario VARCHAR(50),

    -- 실제 결과
    actual_tax DECIMAL(15, 2),
    actual_scenario VARCHAR(50),

    -- 비교
    tax_difference DECIMAL(15, 2),
    tax_difference_percent FLOAT,
    category_match BOOLEAN,
    scenario_match BOOLEAN,

    -- 전체 평가
    match_status VARCHAR(20), -- 'exact', 'close', 'mismatch'
    mismatch_reason TEXT,

    -- 메타
    validated_at TIMESTAMP DEFAULT NOW(),
    validation_notes TEXT
);

CREATE INDEX idx_case_validations_case_id ON case_validations(case_id);
CREATE INDEX idx_case_validations_match_status ON case_validations(match_status);
```

---

## 4. API 명세

### 4.1 케이스 임포트

**엔드포인트**: `POST /api/v1/cases/import`

**Request**:
```json
{
  "file": "multipart/form-data",
  "format": "excel" | "csv",
  "validate_only": false,
  "source": "실제_사례"
}
```

**Response**:
```json
{
  "success": true,
  "imported_count": 10,
  "skipped_count": 2,
  "errors": [
    {
      "row": 3,
      "case_id": "CASE_2024_003",
      "error": "취득가액 누락"
    }
  ],
  "summary": {
    "total_rows": 12,
    "processed": 10,
    "failed": 2
  }
}
```

### 4.2 케이스 조회

**엔드포인트**: `GET /api/v1/cases`

**Query Parameters**:
- `page`: 페이지 번호 (기본 1)
- `per_page`: 페이지 크기 (기본 20)
- `status`: active | archived
- `category`: 전략 카테고리 필터
- `tax_year`: 세무 연도 필터
- `sort_by`: created_at | case_id | tax_amount
- `sort_order`: asc | desc

**Response**:
```json
{
  "cases": [
    {
      "case_id": "CASE_2024_001",
      "status": "active",
      "source": "실제_사례",
      "tax_year": 2024,
      "created_at": "2025-02-20T10:00:00Z",
      "summary": {
        "category": "1주택_비과세",
        "system_tax": 0,
        "actual_tax": 0,
        "match_status": "exact"
      }
    }
  ],
  "total": 127,
  "page": 1,
  "per_page": 20,
  "total_pages": 7
}
```

### 4.3 케이스 상세 조회

**엔드포인트**: `GET /api/v1/cases/{case_id}`

**Response**:
```json
{
  "case_id": "CASE_2024_001",
  "status": "active",
  "facts": {
    "취득일": "2020-01-15",
    "취득가액": 500000000,
    "양도일": "2024-12-01",
    "양도가액": 1000000000
  },
  "scenarios": [
    {
      "scenario_id": "SC1",
      "scenario_name": "지금 바로 양도",
      "expected_tax": 0,
      "is_recommended": true
    }
  ],
  "calculations": {
    "양도차익": 500000000,
    "장기보유공제": 80000000,
    "산출세액": 0
  },
  "filing": {
    "filing_date": "2025-02-15",
    "filed_tax": 0,
    "filing_status": "정상"
  },
  "review": {
    "strategy_category": "1주택_비과세",
    "risk_level": "없음",
    "tax_advisor_comment": "비과세 요건 완벽 충족"
  },
  "validation": {
    "system_tax": 0,
    "actual_tax": 0,
    "match_status": "exact"
  }
}
```

### 4.4 케이스 검증

**엔드포인트**: `POST /api/v1/cases/{case_id}/validate`

**Request**: (없음)

**Response**:
```json
{
  "case_id": "CASE_2024_001",
  "validation": {
    "system_calculation": {
      "category": "1주택_비과세",
      "tax": 0,
      "recommended_scenario": "SC_NOW",
      "calculated_at": "2025-02-20T11:00:00Z"
    },
    "actual_result": {
      "filed_tax": 0,
      "filing_status": "정상"
    },
    "comparison": {
      "tax_difference": 0,
      "tax_difference_percent": 0.0,
      "category_match": true,
      "match_status": "exact"
    },
    "confidence": 1.0
  }
}
```

### 4.5 케이스 통계

**엔드포인트**: `GET /api/v1/cases/statistics`

**Response**:
```json
{
  "total_cases": 127,
  "by_category": {
    "1주택_비과세": 45,
    "다주택_중과세": 32,
    "1주택_과세": 28,
    "기타": 22
  },
  "by_match_status": {
    "exact": 120,
    "close": 5,
    "mismatch": 2
  },
  "accuracy": {
    "overall": 0.945,
    "by_category": {
      "1주택_비과세": 0.98,
      "다주택_중과세": 0.91
    }
  },
  "avg_difference": {
    "amount": 1250000,
    "percent": 2.3
  }
}
```

---

## 5. 케이스 검증 로직

### 5.1 검증 프로세스

```python
async def validate_case(case_id: str) -> ValidationResult:
    """
    케이스 검증 프로세스

    1. 사실관계 로드 → FactLedger 생성
    2. 시스템 계산 (TaxCalculator + StrategyAgent)
    3. 실제 결과와 비교
    4. 오차 분석
    5. 검증 결과 저장
    """

    # 1. 사실관계 로드
    facts = await load_case_facts(case_id)
    ledger = FactLedger.create(facts, created_by="system")
    ledger.freeze()

    # 2. 시스템 계산
    strategy_agent = StrategyAgent(enable_llm=False)
    strategy = await strategy_agent.analyze(ledger)

    tax_result = TaxCalculator.calculate(ledger)

    # 3. 실제 결과 로드
    actual_filing = await load_case_filing(case_id)

    # 4. 비교
    tax_diff = tax_result.total_tax - actual_filing.filed_tax
    tax_diff_pct = (tax_diff / actual_filing.filed_tax * 100) if actual_filing.filed_tax > 0 else 0

    category_match = (strategy.category == actual_filing.strategy_category)

    # 5. 매치 상태 결정
    if abs(tax_diff) == 0:
        match_status = "exact"
    elif abs(tax_diff_pct) < 5.0:  # 5% 이내
        match_status = "close"
    else:
        match_status = "mismatch"

    # 6. 불일치 원인 분석
    mismatch_reason = None
    if match_status == "mismatch":
        mismatch_reason = await analyze_mismatch(
            ledger, strategy, tax_result, actual_filing
        )

    # 7. 검증 결과 저장
    validation = ValidationResult(
        case_id=case_id,
        system_tax=tax_result.total_tax,
        actual_tax=actual_filing.filed_tax,
        tax_difference=tax_diff,
        tax_difference_percent=tax_diff_pct,
        category_match=category_match,
        match_status=match_status,
        mismatch_reason=mismatch_reason
    )

    await save_validation(validation)

    return validation
```

### 5.2 불일치 원인 분석

```python
async def analyze_mismatch(
    ledger: FactLedger,
    strategy: Strategy,
    tax_result: CalculationResult,
    actual_filing: Filing
) -> str:
    """
    불일치 원인 분석

    가능한 원인:
    1. 세법 규칙 버전 차이
    2. 입력 데이터 오류
    3. 계산 로직 오류
    4. 특례 적용 누락
    5. 신고 오류 (실제 신고가 틀렸을 수 있음)
    """

    reasons = []

    # 1. 세법 규칙 체크
    if tax_result.rule_version != actual_filing.rule_version:
        reasons.append(f"세법 버전 차이: 시스템 {tax_result.rule_version} vs 실제 {actual_filing.rule_version}")

    # 2. 양도차익 차이
    if abs(tax_result.capital_gain - actual_filing.capital_gain) > 1000:
        reasons.append("양도차익 계산 차이 (취득가액 또는 필요경비)")

    # 3. 장기보유공제 차이
    if abs(tax_result.long_term_deduction - actual_filing.long_term_deduction) > 1000:
        reasons.append("장기보유공제 차이 (보유기간 또는 공제율)")

    # 4. 세율 차이
    if abs(tax_result.applied_tax_rate - actual_filing.applied_tax_rate) > 0.01:
        reasons.append("적용 세율 차이 (중과세율 또는 누진세율)")

    # 5. 특례 적용
    if strategy.category == "1주택_비과세" and actual_filing.filed_tax > 0:
        reasons.append("비과세 요건 불충족 (거주기간 또는 양도가액)")

    if not reasons:
        reasons.append("원인 불명 (수동 검토 필요)")

    return " | ".join(reasons)
```

---

## 6. 프론트엔드 UI

### 6.1 케이스 관리 페이지

**파일**: `frontend/src/pages/CaseManagement.tsx`

**레이아웃**:

```
┌─────────────────────────────────────────────────────────┐
│  케이스 관리                                             │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  📤 파일 업로드                                          │
│  [파일 선택] [업로드] [템플릿 다운로드]                  │
│                                                          │
│  📊 통계 대시보드                                        │
│  ┌──────────┬──────────┬──────────┬──────────┐         │
│  │총 케이스  │정확도     │평균 오차  │불일치    │         │
│  │127개     │94.5%     │2.3%      │2개       │         │
│  └──────────┴──────────┴──────────┴──────────┘         │
│                                                          │
│  📈 카테고리별 분포 (파이 차트)                          │
│                                                          │
│  📋 케이스 목록                                          │
│  [필터: 카테고리 ▼] [검색: ________]                     │
│                                                          │
│  ┌──────┬───────┬──────┬──────┬──────┬──────┐          │
│  │케이스│카테고리│시스템│실제  │오차  │상태  │          │
│  ├──────┼───────┼──────┼──────┼──────┼──────┤          │
│  │C001  │1주택  │0원   │0원   │0원   │✅   │[상세]    │
│  │C002  │다주택 │1.2억 │1.25억│0.05억│⚠️  │[상세]    │
│  │C003  │1주택  │5천만 │5천만 │0원   │✅   │[상세]    │
│  └──────┴───────┴──────┴──────┴──────┴──────┘          │
│                                                          │
│  [1] 2 3 4 5 ... 10 >                                   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### 6.2 케이스 상세 모달

```
┌─────────────────────────────────────────┐
│  케이스 상세: CASE_2024_001             │
├─────────────────────────────────────────┤
│                                         │
│  [사실관계] [시나리오] [계산] [신고] [리뷰]│
│                                         │
│  ─── 사실관계 ───                        │
│  취득일: 2020-01-15                     │
│  취득가액: 500,000,000원                │
│  양도일: 2024-12-01                     │
│  양도가액: 1,000,000,000원              │
│                                         │
│  ─── 시스템 계산 ───                     │
│  카테고리: 1주택_비과세                  │
│  예상 세액: 0원                         │
│  추천: 지금 바로 양도                    │
│                                         │
│  ─── 실제 신고 ───                       │
│  신고일: 2025-02-15                     │
│  납부세액: 0원                          │
│  신고 상태: 정상                        │
│                                         │
│  ─── 검증 결과 ───                       │
│  오차: 0원 (0.0%)                       │
│  상태: 정확 일치 ✅                      │
│                                         │
│  [닫기] [재검증] [수정]                  │
└─────────────────────────────────────────┘
```

---

## 7. 구현 우선순위

### Phase 3.1: 데이터 구조 (1주)
- [ ] 데이터베이스 스키마 생성
- [ ] SQLAlchemy 모델 정의
- [ ] 마이그레이션 스크립트

### Phase 3.2: 임포트 시스템 (1주)
- [ ] Excel/CSV 파싱 (pandas)
- [ ] 데이터 검증 및 정규화
- [ ] 케이스 임포트 API
- [ ] 에러 처리

### Phase 3.3: 검증 시스템 (1주)
- [ ] 케이스 검증 로직
- [ ] 불일치 원인 분석
- [ ] 검증 결과 저장
- [ ] 통계 계산

### Phase 3.4: 프론트엔드 (1주)
- [ ] 케이스 관리 페이지
- [ ] 파일 업로드 UI
- [ ] 케이스 목록 테이블
- [ ] 통계 대시보드
- [ ] 케이스 상세 모달

---

## 8. 예상 효과

### 8.1 정확도 향상
- 실제 사례 100개 입력 시 → 정확도 95% 예상
- 실제 사례 500개 입력 시 → 정확도 98% 예상

### 8.2 착오율 감소
- 유사 사례 참조 → 착오율 50% 감소 예상
- 리스크 플래그 → 주의 필요 케이스 사전 파악

### 8.3 세무사 신뢰도
- 실제 사례 기반 → 세무사 신뢰 향상
- 검증 결과 공개 → 투명성 확보

---

**문서 버전**: v1.0
**작성일**: 2025-11-22
**다음 리뷰**: Phase 3 시작 전
