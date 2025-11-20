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
- 법률 변경 시 소급 적용 가능
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
┌─────────────────────────────────┐
│   Presentation Layer (React)    │
├─────────────────────────────────┤
│      API Layer (FastAPI)        │
├─────────────────────────────────┤
│   Business Logic Layer          │
│   - FactLedger                  │
│   - Tax Calculation Engine      │
├─────────────────────────────────┤
│   Data Layer (SQLAlchemy)       │
├─────────────────────────────────┤
│   Database (PostgreSQL)         │
└─────────────────────────────────┘
```

### 3.2 핵심 컴포넌트

#### FactLedger (사실관계 원장)
- 불변 객체로 구현
- 거래의 모든 사실을 기록
- 버전 관리 지원

#### Tax Calculation Engine
- FactLedger를 입력으로 받음
- 세법 규칙을 적용하여 계산
- 단계별 계산 과정 기록

#### Audit Trail Service
- 모든 계산 이력 저장
- 재계산 및 검증 지원

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

### Phase 1 (현재)
- [x] 프로젝트 구조 설정
- [ ] FactLedger 불변 객체 구현
- [ ] 기본 양도소득세 계산 로직
- [ ] 단위 테스트

### Phase 2
- [ ] FastAPI REST API 구현
- [ ] PostgreSQL 연동
- [ ] 기본 CRUD 작업

### Phase 3
- [ ] React 프론트엔드
- [ ] 사용자 인증/권한
- [ ] 대시보드

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

## 7. 보안 고려사항

- 개인정보 암호화
- API 인증/인가
- 감사 로그 보안
- SQL Injection 방어

## 8. 확장성 고려사항

- 마이크로서비스 전환 가능한 구조
- 캐싱 전략
- 비동기 처리 지원
- 수평 확장 가능한 설계
