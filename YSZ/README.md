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

### 개발 현황

- [x] 프로젝트 초기 설정
- [x] Git 저장소 구성
- [ ] FactLedger 불변 객체 구현
- [ ] 양도소득세 계산 엔진
- [ ] FastAPI REST API
- [ ] PostgreSQL 연동
- [ ] React 프론트엔드

## 문서

자세한 문서는 [docs](./docs) 폴더를 참조하세요.

## 라이선스

Proprietary - 모든 권리 보유
