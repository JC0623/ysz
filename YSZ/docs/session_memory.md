# 세션 메모리 (Session Memory)

**목적**: 클로드 코드 재시작 시 프로젝트 컨텍스트 빠른 복구

**최종 업데이트**: 2025-11-22

---

## 🎯 프로젝트 비전

YSZ는 **4대 핵심 축**으로 고도화:

1. **구조 설계** (계산 엔진) ✅ 완료
2. **실제 사례 학습** (케이스 DB) 🔄 다음 단계
3. **관리자 친화** (유지보수성) 🎯 목표
4. **사용자 친화** (극도로 심플한 UX) 🎯 목표

---

## 📍 현재 상태

### Phase 1: 핵심 계산 엔진 ✅ 100% 완료
- TaxCalculator (양도소득세 계산)
- RuleEngine (세법 규칙 YAML)
- Fact/FactLedger (불변 데이터)
- CalculationTrace (추적)

### Phase 2: AI 에이전트 ✅ 100% 완료
- StrategyAgent (케이스 분류, 시나리오, 추천)
- BaseAgent, RuleVersion, RuleRegistry
- Claude 3.5 Sonnet 통합
- 25개 테스트, 7개 예제

### Phase 2.5: 프론트엔드 통합 🔄 진행 중 (50% 완료)
- [x] StrategyAgent API 노출 ✅
- [x] 프론트엔드 StrategyPanel ✅
- [ ] OrchestratorAgent 강화
- [ ] VerificationAgent 구현

### Phase 3: 케이스 학습 시스템 🟡 설계 완료, 구현 대기
- [ ] 케이스 데이터베이스 스키마
- [ ] 스프레드시트 임포트 API
- [ ] 시스템 vs 실제 결과 검증
- [ ] 관리자 대시보드

---

## ⚠️ 중요한 결정사항

### ❌ ChatAgent 제외됨
**이유**: StrategyAgent가 이미 LLM 설명 생성 기능 보유
- `StrategyAgent(enable_llm=True)` → Claude로 자연어 설명 생성
- 중복 기능 방지, 복잡도 감소
- 프론트엔드에서 StrategyAgent 직접 호출

### ✅ 케이스 학습 시스템이 두 번째 큰 축
**목적**: 실제 사례로 시스템 학습 및 검증
- 세무사가 실제 케이스 입력 (스프레드시트)
- 시스템 계산 vs 실제 결과 비교
- 불일치 시 원인 분석 및 로직 개선
- Self-improving Tax System

---

## 📋 다음 작업 (우선순위)

### 완료된 작업 (2025-11-22)

1. **StrategyAgent API 노출** ✅ (완료)
   - 파일: `src/api/routers/strategy.py`
   - 엔드포인트: `POST /api/v1/strategy/analyze`
   - Request/Response 스키마 정의
   - StrategyAgent 싱글톤 패턴

2. **프론트엔드 StrategyPanel** ✅ (완료)
   - 파일: `frontend/src/components/StrategyPanel.tsx`
   - 기능: 케이스 분류, 시나리오 비교, 추천, 리스크 표시
   - App.tsx 통합 (Step 4 이후)

### 다음 작업 (Phase 2.5 계속)

3. **OrchestratorAgent 강화** (2일)
   - 파일: `src/agents/orchestrator_agent.py` (수정)
   - Stage 2 추가: StrategyAgent 실행

4. **VerificationAgent 구현** (3-4일)
   - 파일: `src/agents/verification_agent.py`
   - 기능: 로직 검증, 세법 버전 체크, 리스크 플래그

### 이후 진행 (Phase 3)

5. **케이스 DB 스키마** (1일)
   - 파일: `src/database/models.py` (확장)
   - 테이블: cases, case_facts, case_scenarios, case_calculations, case_filings, case_reviews, case_validations

6. **케이스 임포트 API** (2-3일)
   - 파일: `src/api/routers/cases.py`
   - 엔드포인트: `POST /api/v1/cases/import`
   - 기능: Excel/CSV 파싱, DB 저장

7. **케이스 검증 시스템** (2-3일)
   - 시스템 계산 vs 실제 결과 비교
   - 정확도 측정, 오차 분석

8. **관리자 대시보드** (3-4일)
   - 파일: `frontend/src/pages/CaseManagement.tsx`
   - 기능: 케이스 목록, 통계, 검증 결과

---

## 📊 케이스 데이터 형식 (중요!)

### 스프레드시트 구조 (5개 시트)

#### Sheet 1: 사실관계
```
case_id | 취득일 | 취득가액 | 양도일 | 양도가액 | 주택수 | 거주기간 | 조정지역
CASE_2024_001 | 2020-01-15 | 500,000,000 | 2024-12-01 | 1,000,000,000 | 1 | 3 | FALSE
```

#### Sheet 2: 비교보고서
```
case_id | 시나리오1 | 시나리오1_세액 | 시나리오2 | 시나리오2_세액 | 추천
CASE_2024_001 | 지금 양도 | 0 | 1년후 양도 | 0 | 시나리오1
```

#### Sheet 3: 계산근거
```
case_id | 양도차익 | 장기보유공제 | 과세표준 | 산출세액
CASE_2024_001 | 500,000,000 | 80,000,000 | 417,500,000 | 0
```

#### Sheet 4: 신고서
```
case_id | 신고일 | 납부세액 | 비고
CASE_2024_001 | 2025-02-15 | 0 | 비과세 신고
```

#### Sheet 5: 리뷰 (전략 분해 및 로직화)
```
case_id | 전략분류 | 리스크 | 착오가능성 | 세무사코멘트
CASE_2024_001 | 1주택_비과세 | 없음 | 낮음 | 비과세 요건 완벽 충족
```

---

## 🗂️ 핵심 파일 위치

### 문서
- `docs/development_roadmap_v2.md` - 최신 로드맵
- `docs/session_memory.md` - 이 파일 (세션 메모리)
- `docs/case_learning_spec.md` - 케이스 학습 명세서
- `docs/project_architecture_review_2024-11-21.md` - 아키텍처 리뷰

### 백엔드
- `src/agents/strategy_agent.py` - StrategyAgent (완성)
- `src/agents/orchestrator_agent.py` - Orchestrator (개선 필요)
- `src/agents/verification_agent.py` - 구현 예정
- `src/api/routers/strategy.py` - 구현 예정
- `src/api/routers/cases.py` - 구현 예정
- `src/database/models.py` - 케이스 테이블 추가 예정

### 프론트엔드
- `frontend/src/components/StrategyPanel.tsx` - 구현 예정
- `frontend/src/pages/CaseManagement.tsx` - 구현 예정
- `frontend/src/App.tsx` - StrategyPanel 통합 예정

### 데이터
- `case_template.xlsx` - 케이스 입력 템플릿 (생성 예정)

---

## 🔧 기술 스택

| 구분 | 기술 |
|------|------|
| **Backend** | FastAPI, Python 3.11+ |
| **Frontend** | React, TypeScript, Ant Design, Vite |
| **Database** | PostgreSQL (또는 SQLite) |
| **LLM** | Claude 3.5 Sonnet (Anthropic) |
| **Data Processing** | pandas (Excel/CSV 파싱) |
| **ORM** | SQLAlchemy |
| **Testing** | pytest, pytest-asyncio |

---

## 💡 핵심 철학 (절대 변경 금지)

1. **계산은 100% 코드**
   - LLM은 설명만 생성
   - 모든 계산은 결정론적 (TaxCalculator)
   - 세법 규칙은 YAML에 선언적 관리

2. **추적 가능성**
   - 모든 Fact는 출처 기록
   - 모든 계산은 Rule Version 태깅
   - 감사 로그 완전 보존

3. **불변성**
   - Fact, FactLedger는 불변 객체
   - 수정 시 새 버전 생성

---

## 📞 다음 세션 시작 시 확인 사항

1. **Phase 2.5 진행 상황**
   - [ ] StrategyAgent API 완료?
   - [ ] StrategyPanel 완료?
   - [ ] OrchestratorAgent 통합 완료?
   - [ ] VerificationAgent 완료?

2. **Phase 3 준비**
   - [ ] 케이스 템플릿 Excel 생성?
   - [ ] 예제 케이스 3개 작성?
   - [ ] 데이터베이스 스키마 확정?

3. **새로운 요구사항**
   - 사용자가 추가 요청한 사항 있는지 확인

---

## 🚨 주의사항

### 하지 말아야 할 것
- ❌ ChatAgent 구현 (불필요)
- ❌ LLM으로 계산 수행 (결정론적 코드만)
- ❌ Fact 직접 수정 (새 버전 생성)
- ❌ 세법 규칙 하드코딩 (YAML만)

### 반드시 해야 할 것
- ✅ 모든 계산에 Rule Version 태깅
- ✅ 케이스 학습 시스템 준비
- ✅ 스프레드시트 템플릿 생성
- ✅ 시스템 vs 실제 결과 검증

---

## 📝 TODO 리스트 (영속적)

### Phase 2.5 (즉시)
- [ ] `src/api/routers/strategy.py` 구현
- [ ] `frontend/src/components/StrategyPanel.tsx` 구현
- [ ] `src/agents/orchestrator_agent.py` Stage 2 추가
- [ ] `src/agents/verification_agent.py` 구현
- [ ] API 문서 업데이트 (Swagger)
- [ ] 단위 테스트 작성

### Phase 3 (이후)
- [ ] `src/database/models.py` 케이스 테이블 추가
- [ ] `case_template.xlsx` 템플릿 생성
- [ ] 예제 케이스 3개 작성
- [ ] `src/api/routers/cases.py` 구현
- [ ] 케이스 임포트 로직 (pandas)
- [ ] 케이스 검증 로직
- [ ] `frontend/src/pages/CaseManagement.tsx` 구현
- [ ] 통계 대시보드

### Phase 4 (향후)
- [ ] 관리자 친화: 세법 규칙 편집 UI
- [ ] 사용자 친화: 1페이지 입력 폼
- [ ] 모바일 최적화
- [ ] 성능 최적화 (캐싱)

---

**이 파일은 모든 세션에서 가장 먼저 참조할 것!**
