# 양상증닷컴 (YangSangJeung.com)

양도소득세 자동 계산 SaaS 프로그램

## 프로젝트 개요

세무법인에서 사용할 양도소득세 자동 계산 프로그램 MVP

## 핵심 아키텍처 원칙

1. **사실관계 중심**: 모든 계산은 확정된 사실관계(FactLedger) 기반으로 수행
2. **불변 객체**: 사실관계는 한 번 확정되면 변경 불가
3. **추적 가능성**: 모든 계산 과정과 사용된 사실관계를 완전히 기록

## 기술 스택

- **Backend**: Python 3.11 + FastAPI + SQLAlchemy
- **Database**: PostgreSQL
- **Frontend**: React (향후 추가 예정)
- **환경 관리**: Conda

## 프로젝트 구조

```
ysz/
├── docs/               # 프로젝트 문서
├── src/                # 소스 코드
│   ├── core/          # 핵심 비즈니스 로직
│   ├── api/           # FastAPI 엔드포인트
│   ├── models/        # 데이터베이스 모델
│   └── utils/         # 유틸리티 함수
├── tests/              # 테스트 코드
├── environment.yml     # Conda 환경 설정
└── requirements.txt    # Python 패키지 목록
```

## 시작하기

### 환경 설정

```bash
# 저장소 클론
git clone https://github.com/JC0623/ysz.git
cd ysz

# Conda 환경 생성 및 활성화
conda env create -f environment.yml
conda activate ysz

# 또는 pip 사용
pip install -r requirements.txt
```

### 사용 예제

```python
from datetime import date
from decimal import Decimal
from src.core import Fact, FactLedger

# 1. FactLedger 생성 (Fact 래핑 방식)
ledger = FactLedger.create({
    "acquisition_date": Fact(
        value=date(2020, 1, 1),
        source="user_input",
        is_confirmed=True,
        confidence=1.0,
        entered_by="김세무사"
    ),
    "acquisition_price": Decimal("500000000"),  # 자동으로 Fact 래핑
    "disposal_date": Fact(
        value=date(2023, 12, 31),
        is_confirmed=True,
        confidence=1.0,
        entered_by="김세무사"
    ),
    "disposal_price": Decimal("700000000")
}, created_by="김세무사")

# 2. 확정되지 않은 필드 확인
unconfirmed = ledger.get_unconfirmed_fields()
print(f"확정 필요: {unconfirmed}")

# 3. 추정값 확정
if ledger.acquisition_price and not ledger.acquisition_price.is_confirmed:
    confirmed = ledger.acquisition_price.confirm(
        confirmed_by="김세무사",
        notes="등기부등본 확인"
    )
    ledger.update_field('acquisition_price', confirmed)

# 4. 모든 필드 확정 후 freeze
ledger.freeze()
print(f"양도차익: {ledger.capital_gain:,}원")
```

### 개발 현황

- [x] 프로젝트 초기 설정
- [x] Git 저장소 구성
- [x] **Fact 클래스 구현** (추적 가능한 사실 정보)
- [x] **FactLedger 구현** (Fact 래핑, freeze 메커니즘)
- [x] **양도소득세 계산 엔진** (RuleEngine, TaxCalculator)
- [x] **계산 추적 시스템** (CalculationTrace, CalculationResult)
- [x] **세법 규칙 관리** (YAML 기반)
- [x] **테스트 코드** (43개 테스트 통과)
- [ ] **정확한 누진세율 적용** (현재는 단순 평면 세율)
- [ ] FastAPI REST API
- [ ] PostgreSQL 연동
- [ ] React 프론트엔드

## 문서

자세한 문서는 [docs](./docs) 폴더를 참조하세요.

## 라이선스

Proprietary - 모든 권리 보유
