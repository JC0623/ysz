"""FastAPI 애플리케이션 메인"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from ..database import init_db
from .routers import facts, calculate, strategy


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 라이프사이클 관리"""
    # 시작 시 데이터베이스 초기화
    init_db()
    yield
    # 종료 시 정리 작업 (필요시)


# FastAPI 앱 생성
app = FastAPI(
    title="YSZ 양도소득세 계산 API",
    description="양도소득세 자동 계산 및 사실관계 관리 시스템",
    version="0.1.0",
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(
    facts.router,
    prefix="/api/v1/facts",
    tags=["사실관계"]
)

app.include_router(
    calculate.router,
    prefix="/api/v1/calculate",
    tags=["세금계산"]
)

app.include_router(
    strategy.router,
    prefix="/api/v1",
    tags=["전략분석"]
)


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "YSZ 양도소득세 계산 API",
        "version": "0.1.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """헬스체크 엔드포인트"""
    return {"status": "healthy"}
