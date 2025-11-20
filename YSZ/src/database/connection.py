"""데이터베이스 연결 설정"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from .models import Base


# 환경 변수에서 데이터베이스 URL 가져오기
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/ysz_dev"
)

# SQLAlchemy 엔진 생성
engine = create_engine(
    DATABASE_URL,
    echo=True,  # SQL 로깅 활성화 (개발 환경)
    pool_pre_ping=True,  # 연결 풀 헬스체크
    pool_size=5,
    max_overflow=10
)

# 세션 팩토리
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db() -> Generator[Session, None, None]:
    """데이터베이스 세션 의존성

    FastAPI 의존성으로 사용됩니다.

    Yields:
        데이터베이스 세션

    Example:
        >>> @app.get("/items")
        >>> async def get_items(db: Session = Depends(get_db)):
        >>>     return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """데이터베이스 초기화

    모든 테이블을 생성합니다.
    """
    Base.metadata.create_all(bind=engine)
