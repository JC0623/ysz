# 양상증닷컴 아키텍처 문서

## 1. 개요

양도소득세 계산 프로그램은 복잡한 세법을 자동화하여 정확하고 추적 가능한 계산 결과를 제공합니다.

## 2. 핵심 설계 원칙

### 2.1 사실관계 중심 (Fact-Based)

모든 계산은 확정된 사실관계(FactLedger)를 기반으로 수행됩니다.

```
사실관계 확정 → 계산 수행 → 결과 저장 → 감사 추적
```

**장점**:
- 계산의 재현 가능성 보장
- 법률 변경 시 즉각 적용 가능
- 완전한 감사 추적(audit trail)

### 2.2 불변 객체 (Immutability)

사실관계는 한 번 확정되면 절대 변경되지 않습니다.

**구현 방법**:
- Python `@dataclass(frozen=True)` 사용
- 모든 필드를 읽기 전용으로 설정
- 수정이 필요한 경우 새로운 객체 생성

**장점**:
- 데이터 무결성 보장
- 동시성 문제 제거
- 명확한 버전 관리

### 2.3 추적 가능성 (Traceability)

모든 계산 과정과 사용된 데이터를 완전히 기록합니다.

**기록 항목**:
- 입력 데이터 (사실관계)
- 적용된 법률 조항
- 계산 단계별 중간 결과
- 최종 결과
- 타임스탬프 및 사용자 정보

## 3. 시스템 아키텍처

### 3.1 레이어 구조

```
┌─────────────────────────────────────────────┐
│   Presentation Layer (React + Ant Design)   │
│   - 4단계 계산 플로우                        │
│   - 사실관계 확인 UI                         │
│   - 결과 시각화                              │
├─────────────────────────────────────────────┤
│      API Layer (FastAPI)                    │
│   - REST API 엔드포인트                      │
│   - 감사 미들웨어                            │
│   - 요청/응답 검증                           │
├─────────────────────────────────────────────┤
│   Business Logic Layer                      │
│   - FactCollector (사실관계 수집)            │
│   - ConflictResolver (충돌 해소)             │
│   - TaxCalculator (세액 계산)                │
│   - CalculationAuditor (계산 감사)           │
├─────────────────────────────────────────────┤
│   Data Layer (SQLAlchemy)                   │
│   - Transaction (거래 정보)                  │
│   - FactLedger (사실관계)                    │
│   - CalculationResult (계산 결과)            │
│   - AuditLog (감사 로그)                     │
├─────────────────────────────────────────────┤
│   Database (PostgreSQL)                     │
│   - JSONB 타입으로 구조화된 데이터 저장      │
│   - 완전한 감사 추적 (5년 보관)              │
└─────────────────────────────────────────────┘
```

### 3.2 핵심 컴포넌트

#### FactCollector (사실관계 수집기)
- **위치**: `src/core/fact_collector.py`
- **역할**: 사용자 입력으로부터 사실관계 추출
- **특징**:
  - 자동 보유기간 계산
  - 1세대1주택 여부 판단
  - 조정대상지역 검증
  - 타임스탬프 자동 기록

#### ConflictResolver (충돌 해소기)
- **위치**: `src/core/conflict_resolver.py`
- **역할**: 수집된 사실 간의 충돌 탐지 및 해소
- **검증 항목**:
  - 날짜 순서 검증 (취득일 < 양도일)
  - 금액 양수 검증
  - 논리적 일관성 검증

#### TaxCalculator (세액 계산 엔진)
- **위치**: `src/core/tax_calculator.py`
- **역할**: 확정된 사실관계로 양도소득세 계산
- **기능**:
  - 양도차익 계산
  - 장기보유특별공제 적용
  - 누진세율 적용 (6~45%)
  - 중과세율 적용 (조정대상지역)
  - 지방소득세 계산

#### CalculationAuditor (계산 감사기)
- **위치**: `src/audit/calculation_auditor.py`
- **역할**: 모든 계산 과정을 단계별로 기록
- **기록 내용**:
  - 각 단계의 입력/출력 값
  - 적용된 법률 조항
  - 계산 시각 및 소요 시간
  - 최종 결과 및 근거

#### AuditMiddleware (감사 미들웨어)
- **위치**: `src/audit/audit_middleware.py`
- **역할**: 모든 API 요청/응답을 자동으로 기록
- **기록 내용**:
  - HTTP 메서드, URL, 파라미터
  - 요청/응답 본문
  - 처리 시간
  - 에러 발생 시 스택 트레이스

## 4. 데이터 모델

### 4.1 FactLedger 구조

```python
@dataclass(frozen=True)
class FactLedger:
    # 거래 기본 정보
    transaction_id: str
    transaction_date: date

    # 자산 정보
    asset_type: str
    acquisition_date: date
    acquisition_price: Decimal

    # 처분 정보
    disposal_date: date
    disposal_price: Decimal

    # 메타데이터
    created_at: datetime
    created_by: str
    version: int
```

### 4.2 계산 결과 구조

```python
@dataclass
class TaxCalculationResult:
    fact_ledger_id: str
    calculation_steps: List[CalculationStep]
    final_tax_amount: Decimal
    applied_rules: List[str]
    calculated_at: datetime
```

## 5. MVP 범위

### Phase 1: 핵심 도메인 모델 (✅ 완료)
- [x] 프로젝트 구조 설정
- [x] FactLedger 불변 객체 구현
- [x] Fact 래핑 시스템 구현
- [x] 단위 테스트 작성

### Phase 2: 세액 계산 엔진 (✅ 완료)
- [x] TaxCalculator 구현
- [x] 누진세율 테이블 적용
- [x] 장기보유특별공제 로직
- [x] 중과세율 적용 (조정대상지역)
- [x] 1세대1주택 비과세 로직
- [x] 지방소득세 계산
- [x] 계산 과정 상세 추적

### Phase 3: API 및 데이터베이스 (✅ 완료)
- [x] FastAPI REST API 구현
- [x] PostgreSQL 연동 (SQLAlchemy ORM)
- [x] FactCollector 시스템 구현
- [x] ConflictResolver 구현
- [x] 데이터베이스 스키마 설계
- [x] CRUD 엔드포인트 구현
  - `/api/v1/facts/collect` - 사실관계 수집
  - `/api/v1/facts/{id}/confirm` - 사실관계 확정
  - `/api/v1/calculate/{id}` - 세액 계산
  - `/api/v1/transactions` - 거래 조회
- [x] API 통합 테스트

### Phase 4: 프론트엔드 및 감사 시스템 (✅ 완료)
- [x] React + TypeScript 프론트엔드
  - 4단계 계산 플로우
  - 사실관계 확인 UI
  - 결과 시각화 (차트 및 상세 내역)
- [x] 감사 추적(Audit Trail) 시스템
  - AuditService (이벤트 로깅)
  - AuditMiddleware (API 요청/응답 자동 기록)
  - CalculationAuditor (계산 과정 단계별 기록)
- [x] 통합 테스트
  - E2E 계산 플로우 테스트
  - 복잡한 시나리오 테스트 (중과세, 비과세, 장기보유)
  - 데이터 일관성 검증
- [x] Docker 배포 설정
  - Dockerfile (Python 백엔드)
  - docker-compose.yml (전체 스택)
  - Nginx 리버스 프록시

### Phase 5: 프로덕션 준비 (진행 예정)
- [ ] 사용자 인증/권한 (JWT)
- [ ] 관리자 대시보드
- [ ] PDF 보고서 생성
- [ ] 이메일 알림
- [ ] 성능 최적화
- [ ] 보안 강화 (HTTPS, API 레이트 리미팅)
- [ ] 모니터링 및 로깅 (Prometheus, Grafana)

## 6. 기술 결정 사항

### 6.1 Python 3.11 선택 이유
- 타입 힌팅 개선
- 성능 향상
- Dataclass 기능 강화

### 6.2 FastAPI 선택 이유
- 빠른 성능
- 자동 API 문서화
- 타입 안정성

### 6.3 PostgreSQL 선택 이유
- ACID 보장
- JSON 지원 (계산 과정 저장)
- 성숙한 에코시스템

### 6.4 React + Ant Design 선택 이유
- 컴포넌트 기반 아키텍처
- TypeScript 완벽 지원
- Ant Design의 전문적인 UI 컴포넌트
- 빠른 개발 속도

### 6.5 Docker 선택 이유
- 환경 일관성 보장
- 간편한 배포 및 확장
- 서비스 간 격리
- 개발/프로덕션 환경 동일성

## 6.6 프론트엔드 아키텍처

### React 컴포넌트 구조

```
src/
├── App.tsx                     # 메인 애플리케이션
├── components/
│   ├── DataInputStep.tsx       # 1단계: 데이터 입력
│   ├── FactConfirmationStep.tsx # 2단계: 사실관계 확인
│   ├── CalculationStep.tsx     # 3단계: 계산 진행
│   └── ResultDisplayStep.tsx   # 4단계: 결과 표시
├── services/
│   └── api.ts                  # API 통신 레이어
└── types/
    └── index.ts                # TypeScript 타입 정의
```

### 계산 플로우

```
1. DataInputStep
   ↓ (사용자 입력)
   POST /api/v1/facts/collect
   ↓
2. FactConfirmationStep
   ↓ (사실관계 확인)
   POST /api/v1/facts/{id}/confirm
   ↓
3. CalculationStep
   ↓ (계산 실행)
   POST /api/v1/calculate/{id}
   ↓
4. ResultDisplayStep
   (결과 표시 + 법적 근거)
```

## 6.7 배포 아키텍처

### Docker Compose 구성

```
┌───────────────────────────────────────┐
│           Nginx (Port 80)             │
│  - Frontend 정적 파일 서빙            │
│  - /api/* → Backend 프록시            │
│  - CORS 처리                          │
└───────────┬───────────────────────────┘
            │
            ↓
┌───────────────────────────────────────┐
│     FastAPI Backend (Port 8000)       │
│  - REST API 서버                      │
│  - Uvicorn ASGI 서버                  │
│  - 감사 미들웨어 적용                 │
└───────────┬───────────────────────────┘
            │
            ↓
┌───────────────────────────────────────┐
│     PostgreSQL (Port 5432)            │
│  - 거래 데이터 저장                   │
│  - 감사 로그 저장 (5년)               │
│  - Health Check 지원                  │
└───────────────────────────────────────┘
```

### 볼륨 구성

- `postgres_data`: 데이터베이스 영구 저장소
- `logs/`: 애플리케이션 로그
- `frontend/dist`: 빌드된 프론트엔드 파일

### 환경 변수

- `DATABASE_URL`: PostgreSQL 연결 문자열
- `SECRET_KEY`: API 보안 키
- `AUDIT_LOG_RETENTION_DAYS`: 감사 로그 보관 기간 (기본 1825일)
- `LOG_LEVEL`: 로깅 레벨
- `CORS_ORIGINS`: 허용된 CORS 출처

## 7. 감사 추적 시스템

### 7.1 이벤트 타입

```python
class AuditEventType(Enum):
    API_REQUEST = "API_REQUEST"              # API 요청
    FACT_COLLECTED = "FACT_COLLECTED"        # 사실관계 수집
    FACT_CONFIRMED = "FACT_CONFIRMED"        # 사실관계 확정
    CALCULATION_STARTED = "CALCULATION_STARTED"   # 계산 시작
    CALCULATION_COMPLETED = "CALCULATION_COMPLETED" # 계산 완료
    CALCULATION_STEP = "CALCULATION_STEP"    # 계산 단계
    RULE_APPLIED = "RULE_APPLIED"            # 규칙 적용
    ERROR_OCCURRED = "ERROR_OCCURRED"        # 에러 발생
```

### 7.2 감사 로그 구조

```python
@dataclass
class AuditEntry:
    event_type: AuditEventType
    timestamp: datetime
    transaction_id: Optional[int]
    user_id: Optional[str]
    request_data: Optional[Dict[str, Any]]
    response_data: Optional[Dict[str, Any]]
    error_message: Optional[str]
    stack_trace: Optional[str]
```

### 7.3 보관 정책

- **보관 기간**: 5년 (1825일)
- **저장 형식**: JSONB (PostgreSQL)
- **접근 제어**: 관리자만 열람 가능
- **불변성**: 한 번 기록된 로그는 수정 불가

## 8. 보안 고려사항

- 개인정보 암호화
- API 인증/인가
- 감사 로그 보안
- SQL Injection 방어

## 9. 테스트 전략

### 9.1 단위 테스트
- **위치**: `tests/test_*.py`
- **커버리지**: 핵심 비즈니스 로직 100%
- **도구**: pytest
- **테스트 대상**:
  - FactLedger 불변성
  - TaxCalculator 계산 정확성
  - ConflictResolver 검증 로직

### 9.2 통합 테스트
- **위치**: `tests/test_integration.py`
- **데이터베이스**: SQLite in-memory (격리된 환경)
- **테스트 시나리오**:
  - 완전한 계산 플로우 (수집 → 확정 → 계산)
  - 조정대상지역 3주택 중과세
  - 1세대1주택 12억 초과 부분과세
  - 장기보유특별공제 (15년 보유)
  - 트랜잭션 상태 전이 (draft → confirmed → calculated)
  - 데이터 일관성 검증

### 9.3 API 테스트
- **위치**: `tests/test_api.py`
- **도구**: pytest + httpx
- **테스트 대상**:
  - REST API 엔드포인트
  - 입력 검증
  - 에러 처리
  - 응답 형식

### 9.4 E2E 테스트 (향후)
- Playwright/Selenium을 활용한 브라우저 테스트
- 실제 사용자 시나리오 검증

## 10. 확장성 고려사항

### 10.1 수평 확장
- Docker Compose → Kubernetes 전환 가능
- 상태 비저장(stateless) 백엔드 설계
- 데이터베이스 연결 풀링

### 10.2 성능 최적화
- 계산 결과 캐싱 (Redis)
- 데이터베이스 인덱싱 전략
- API 응답 압축 (gzip)
- 정적 파일 CDN 배포

### 10.3 마이크로서비스 전환 경로
현재 모놀리식 구조에서 필요시 다음과 같이 분리 가능:
- **Fact Collection Service**: 사실관계 수집 전담
- **Calculation Service**: 세액 계산 전담
- **Audit Service**: 감사 로그 전담
- **API Gateway**: 라우팅 및 인증

### 10.4 비동기 처리
- 대량 계산 작업: Celery + Redis 큐
- 이메일 발송: 백그라운드 작업
- PDF 생성: 비동기 작업자

## 11. 개발 및 배포 워크플로우

### 11.1 로컬 개발
```bash
# 백엔드 개발
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn src.api.main:app --reload

# 프론트엔드 개발
cd frontend
npm install
npm run dev
```

### 11.2 Docker를 활용한 배포
```bash
# 전체 스택 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 서비스 재시작
docker-compose restart backend

# 정리
docker-compose down
```

### 11.3 CI/CD 파이프라인 (향후)
1. 코드 푸시 → GitHub Actions 트리거
2. 단위 테스트 실행
3. 통합 테스트 실행
4. Docker 이미지 빌드
5. 이미지 레지스트리 업로드
6. 스테이징 환경 배포
7. E2E 테스트 실행
8. 프로덕션 배포 승인
9. 프로덕션 배포

## 12. 모니터링 및 알림 (향후)

### 12.1 애플리케이션 모니터링
- Prometheus: 메트릭 수집
- Grafana: 대시보드 및 시각화
- 추적 항목:
  - API 응답 시간
  - 계산 소요 시간
  - 에러율
  - 동시 사용자 수

### 12.2 로그 관리
- ELK Stack (Elasticsearch, Logstash, Kibana)
- 중앙 집중식 로그 수집
- 로그 검색 및 분석

### 12.3 알림
- Slack/이메일 통합
- 알림 조건:
  - 서비스 다운
  - 에러율 급증
  - 응답 시간 지연

## 13. 결론

YSZ 양도소득세 계산 시스템은 **사실관계 중심**, **불변성**, **추적 가능성**이라는 핵심 원칙을 기반으로 설계되었습니다. Phase 4까지 완료된 현재 시스템은:

- ✅ 정확한 세액 계산 (누진세율, 공제, 중과세)
- ✅ 완전한 감사 추적 (5년 보관)
- ✅ 사용자 친화적 UI (4단계 플로우)
- ✅ Docker 기반 배포

를 제공하며, 프로덕션 배포를 위한 **견고한 기반**을 갖추었습니다.
