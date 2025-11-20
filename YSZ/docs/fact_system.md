# Fact 시스템 설계 문서

## 개요

Fact 시스템은 모든 입력값에 메타데이터를 부여하여 완벽한 추적 가능성을 제공합니다.

## Fact 클래스

### 목적

세무 계산에서 "이 값은 어디서 왔는가?", "누가 입력했는가?", "확정된 값인가?"와 같은 질문에 답할 수 있도록 모든 값을 메타데이터와 함께 저장합니다.

### 구조

```python
@dataclass(frozen=True)
class Fact(Generic[T]):
    value: T                        # 실제 값
    source: str                     # 출처 (user_input, system, api, document 등)
    confidence: float               # 신뢰도 (0.0~1.0)
    is_confirmed: bool              # 확정 여부
    entered_by: str                 # 입력자
    entered_at: datetime            # 입력 시각
    notes: Optional[str]            # 메모
    reference: Optional[str]        # 근거 자료
```

### 사용 예제

#### 1. 확정값 생성

```python
confirmed_price = Fact(
    value=Decimal("500000000"),
    source="document",
    confidence=1.0,
    is_confirmed=True,
    entered_by="김세무사",
    notes="등기부등본 기준",
    reference="등기부등본_2020_001.pdf"
)
```

#### 2. 추정값 생성

```python
estimated_price = Fact.create_estimated(
    value=Decimal("480000000"),
    confidence=0.7,
    source="ai_prediction",
    notes="과거 거래 데이터 기반 추정"
)
```

#### 3. 추정값을 확정값으로 변경

```python
confirmed = estimated_price.confirm(
    confirmed_by="김세무사",
    notes="고객 제공 계약서로 확인"
)
```

## FactLedger 클래스

### 목적

양도소득세 계산에 필요한 모든 사실관계를 Fact 객체로 관리하고, 확정 프로세스를 제공합니다.

### 생명주기

```
1. 생성 (create)
   ↓
2. 데이터 입력/수정 (update_field)
   ↓
3. 확정되지 않은 필드 확인 (get_unconfirmed_fields)
   ↓
4. 추정값 확정 (Fact.confirm)
   ↓
5. 검증 및 확정 (freeze)
   ↓
6. 계산 수행 (calculate_tax)
```

### 사용 예제

#### 전체 워크플로우

```python
from datetime import date
from decimal import Decimal
from src.core import Fact, FactLedger

# Step 1: 초기 데이터 입력
ledger = FactLedger.create({
    "asset_type": Fact.create_user_input(
        value="부동산",
        entered_by="김세무사",
        is_confirmed=True
    ),
    "acquisition_date": Fact.create_user_input(
        value=date(2020, 1, 1),
        entered_by="김세무사",
        is_confirmed=True
    ),
    # 취득가액은 추정값
    "acquisition_price": Fact.create_estimated(
        value=Decimal("500000000"),
        confidence=0.8,
        notes="유사 매물 기준 추정"
    ),
    "disposal_date": Fact.create_user_input(
        value=date(2023, 12, 31),
        entered_by="김세무사",
        is_confirmed=True
    ),
    "disposal_price": Fact.create_user_input(
        value=Decimal("700000000"),
        entered_by="김세무사",
        is_confirmed=True
    )
}, created_by="김세무사")

# Step 2: 확정되지 않은 필드 확인
unconfirmed = ledger.get_unconfirmed_fields()
print(f"확정 필요: {unconfirmed}")  # ['acquisition_price']

# Step 3: 신뢰도 확인
confidence = ledger.get_confidence_summary()
print(f"신뢰도: {confidence}")

# Step 4: 추정값 확정 (등기부등본 확인 후)
if ledger.acquisition_price and not ledger.acquisition_price.is_confirmed:
    confirmed_price = ledger.acquisition_price.confirm(
        confirmed_by="김세무사",
        notes="등기부등본 확인 완료"
    )
    ledger.update_field('acquisition_price', confirmed_price)

# Step 5: 모든 필드 확정 및 freeze
try:
    ledger.freeze()
    print("✅ 사실관계 확정 완료")
    print(f"양도차익: {ledger.capital_gain:,}원")
except ValueError as e:
    print(f"❌ 확정 실패: {e}")
```

## 추적 가능성 구현

### 1. 출처 추적

모든 값의 출처를 명확히 기록:
- `user_input`: 사용자 직접 입력
- `document`: 문서에서 추출
- `api`: 외부 API 조회
- `system`: 시스템 계산
- `ai_prediction`: AI 예측

### 2. 신뢰도 관리

```python
# 신뢰도 레벨
1.0  # 확정값 (공식 문서, 계약서 등)
0.9  # 높은 신뢰도 (사용자 입력)
0.7  # 중간 신뢰도 (유사 사례 기반 추정)
0.5  # 낮은 신뢰도 (대략적 추정)
```

### 3. 감사 추적

```python
# 특정 필드의 이력 조회
fact = ledger.acquisition_price
print(f"입력자: {fact.entered_by}")
print(f"입력시각: {fact.entered_at}")
print(f"출처: {fact.source}")
print(f"근거: {fact.reference}")
print(f"메모: {fact.notes}")
```

## 동시 작업 지원

### 버전 관리

```python
# 버전 1
ledger_v1 = FactLedger.create({
    "disposal_price": Decimal("700000000")
})

# 버전 2 (수정본)
ledger_v2 = ledger_v1.create_new_version(
    disposal_price=Fact(
        value=Decimal("750000000"),
        entered_by="이세무사",
        notes="고객 추가 정보 반영"
    )
)

print(ledger_v1.version)  # 1
print(ledger_v2.version)  # 2
```

## 에러 처리

### Freeze 실패 케이스

```python
try:
    ledger.freeze()
except ValueError as e:
    if "필수 필드" in str(e):
        print("필수 필드가 누락되었습니다")
    elif "확정되지 않았습니다" in str(e):
        print("모든 필드를 확정해주세요")
        unconfirmed = ledger.get_unconfirmed_fields()
        for field in unconfirmed:
            fact = getattr(ledger, field)
            print(f"- {field}: {fact.confidence*100}% 신뢰도")
```

## 모범 사례

### 1. 항상 출처 명시

```python
# Good
Fact(value=5000000, source="user_input", entered_by="김세무사")

# Bad
Fact(value=5000000)  # source가 기본값
```

### 2. 추정값에는 근거 기록

```python
# Good
Fact.create_estimated(
    value=5000000,
    confidence=0.7,
    notes="2019년 유사 매물 3건 평균값"
)

# Bad
Fact.create_estimated(value=5000000, confidence=0.7)
```

### 3. 확정 시 반드시 검증

```python
# Good
if validate_with_document(price):
    confirmed = fact.confirm(
        confirmed_by="김세무사",
        notes="등기부등본 확인"
    )

# Bad
confirmed = fact.confirm(confirmed_by="김세무사")  # 검증 없음
```

## 성능 고려사항

### 메모리 효율

Fact 객체는 불변이므로:
- 같은 값을 재사용 가능
- 메모리 복사 최소화
- 캐싱 가능

### 직렬화

```python
# DB 저장용
fact_dict = fact.to_dict()

# API 응답용
ledger_dict = ledger.to_dict()
```

## 향후 확장

### 1. 변경 이력 추적

```python
class FactHistory:
    """Fact의 변경 이력 추적"""
    original: Fact
    changes: List[Fact]
    change_reasons: List[str]
```

### 2. 승인 워크플로우

```python
class ApprovalWorkflow:
    """다단계 승인 프로세스"""
    submitted_by: str
    reviewed_by: Optional[str]
    approved_by: Optional[str]
```

### 3. AI 통합

```python
# AI가 자동으로 값을 추정하고 신뢰도 제공
fact = predict_acquisition_price(
    location="서울 강남구",
    area=85,
    year=2020
)
# → Fact(value=500000000, confidence=0.75, source="ai_prediction")
```
