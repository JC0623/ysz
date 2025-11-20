# 개발 가이드

## 개발 환경 설정

### 1. Conda 환경 활성화

```bash
conda activate ysz
```

### 2. 의존성 설치

```bash
pip install fastapi uvicorn sqlalchemy psycopg2-binary pydantic python-dotenv pytest
```

### 3. 환경 변수 설정

`.env` 파일 생성:
```
DATABASE_URL=postgresql://user:password@localhost/ysz
SECRET_KEY=your-secret-key
DEBUG=True
```

## 코딩 규칙

### 1. 타입 힌팅 필수

```python
def calculate_tax(fact: FactLedger) -> TaxCalculationResult:
    pass
```

### 2. Docstring 작성

```python
def calculate_tax(fact: FactLedger) -> TaxCalculationResult:
    """양도소득세를 계산합니다.

    Args:
        fact: 확정된 사실관계 객체

    Returns:
        계산 결과 객체

    Raises:
        ValueError: 입력값이 유효하지 않은 경우
    """
    pass
```

### 3. 불변 객체 사용

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class FactLedger:
    # frozen=True로 불변성 보장
    transaction_id: str
```

## 테스트 작성

### 1. 테스트 파일 구조

```
tests/
├── test_fact_ledger.py
├── test_calculation.py
└── test_api.py
```

### 2. 테스트 실행

```bash
pytest
pytest -v  # 상세 출력
pytest tests/test_fact_ledger.py  # 특정 파일만
```

### 3. 테스트 커버리지

```bash
pytest --cov=src
```

## Git 워크플로우

### 1. 브랜치 전략

- `main`: 안정 버전
- `develop`: 개발 중인 기능
- `feature/xxx`: 새 기능 개발

### 2. 커밋 메시지 규칙

```
feat: 새로운 기능 추가
fix: 버그 수정
docs: 문서 수정
test: 테스트 추가/수정
refactor: 코드 리팩토링
```

예시:
```bash
git commit -m "feat: FactLedger 불변 객체 구현"
```

### 3. 작업 흐름

```bash
# 1. 새 기능 브랜치 생성
git checkout -b feature/fact-ledger

# 2. 작업 및 커밋
git add .
git commit -m "feat: FactLedger 구현"

# 3. 푸시
git push origin feature/fact-ledger

# 4. 머지 (main으로)
git checkout main
git merge feature/fact-ledger
```

## 문서화

### 1. 코드 변경 시
- 관련 문서 업데이트
- README.md의 체크리스트 업데이트

### 2. 새 기능 추가 시
- docs/ 폴더에 관련 문서 추가
- 사용 예시 포함

### 3. API 변경 시
- API 문서 자동 생성 (FastAPI 사용)
- `/docs` 엔드포인트에서 확인 가능

## 디버깅

### 1. 로깅 설정

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.debug("디버그 메시지")
logger.info("정보 메시지")
logger.error("에러 메시지")
```

### 2. 개발 서버 실행

```bash
uvicorn src.api.main:app --reload
```

## 성능 고려사항

### 1. 데이터베이스 쿼리 최적화
- N+1 쿼리 문제 방지
- 적절한 인덱스 사용

### 2. 캐싱
- 계산 결과 캐싱
- Redis 사용 고려

### 3. 비동기 처리
- FastAPI의 async/await 활용
- 대량 계산 시 백그라운드 작업
