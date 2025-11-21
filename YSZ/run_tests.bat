@echo off
REM YSZ Phase 2.5 Part 1 테스트 실행 스크립트 (Windows CMD)
REM
REM 사용법:
REM   1. CMD를 열고
REM   2. cd C:\Users\next0\claude-test\ysz\YSZ
REM   3. run_tests.bat

echo ============================================================
echo YSZ Phase 2.5 Part 1 테스트
echo ============================================================
echo.

echo [Step 1] 의존성 확인...
echo.

python -c "import fastapi" 2>nul
if %errorlevel% neq 0 (
    echo ❌ fastapi 누락
    set MISSING=1
) else (
    echo ✅ fastapi
)

python -c "import uvicorn" 2>nul
if %errorlevel% neq 0 (
    echo ❌ uvicorn 누락
    set MISSING=1
) else (
    echo ✅ uvicorn
)

python -c "import anthropic" 2>nul
if %errorlevel% neq 0 (
    echo ❌ anthropic 누락
    set MISSING=1
) else (
    echo ✅ anthropic
)

python -c "import pydantic" 2>nul
if %errorlevel% neq 0 (
    echo ❌ pydantic 누락
    set MISSING=1
) else (
    echo ✅ pydantic
)

python -c "import requests" 2>nul
if %errorlevel% neq 0 (
    echo ❌ requests 누락
    set MISSING=1
) else (
    echo ✅ requests
)

echo.

if defined MISSING (
    echo 누락된 패키지를 설치합니다...
    pip install fastapi uvicorn anthropic requests
)

echo.
echo ============================================================
echo [Step 2] 백엔드 서버 실행 준비
echo ============================================================
echo.
echo 새 CMD 창을 열어 다음 명령어를 실행하세요:
echo.
echo   cd C:\Users\next0\claude-test\ysz\YSZ\src
echo   python -m api.main
echo.
echo 서버가 시작되면 http://localhost:8000/docs 를 브라우저에서 확인하세요
echo.
echo ============================================================
echo [Step 3] API 테스트 실행
echo ============================================================
echo.
echo 서버가 실행되었다면, 이 창에서 다음 명령어를 실행하세요:
echo.
echo   python test_strategy_api.py
echo.
echo ============================================================
echo.
echo 준비 완료! 위 단계대로 진행하세요.
echo.

pause
