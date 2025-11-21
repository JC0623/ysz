# YSZ Phase 2.5 Part 1 테스트 실행 스크립트 (PowerShell)
#
# 사용법:
#   1. PowerShell을 관리자 권한으로 실행
#   2. cd C:\Users\next0\claude-test\ysz\YSZ
#   3. .\run_tests.ps1

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "YSZ Phase 2.5 Part 1 테스트" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: 의존성 확인
Write-Host "[Step 1] 의존성 확인..." -ForegroundColor Yellow
Write-Host ""

$packages = @("fastapi", "uvicorn", "anthropic", "pydantic", "requests")
$missing = @()

foreach ($package in $packages) {
    try {
        python -c "import $package; print('✅ $package')"
        if ($LASTEXITCODE -ne 0) {
            $missing += $package
            Write-Host "❌ $package (누락)" -ForegroundColor Red
        }
    } catch {
        $missing += $package
        Write-Host "❌ $package (누락)" -ForegroundColor Red
    }
}

if ($missing.Count -gt 0) {
    Write-Host ""
    Write-Host "누락된 패키지를 설치합니다..." -ForegroundColor Yellow
    $packagesStr = $missing -join " "
    pip install $packagesStr
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "[Step 2] 백엔드 서버 실행 준비" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "새 PowerShell 창을 열어 다음 명령어를 실행하세요:" -ForegroundColor Green
Write-Host ""
Write-Host "  cd C:\Users\next0\claude-test\ysz\YSZ\src" -ForegroundColor White
Write-Host "  python -m api.main" -ForegroundColor White
Write-Host ""
Write-Host "서버가 시작되면 http://localhost:8000/docs 를 브라우저에서 확인하세요" -ForegroundColor Green
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "[Step 3] API 테스트 실행" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "서버가 실행되었다면, 이 창에서 다음 명령어를 실행하세요:" -ForegroundColor Green
Write-Host ""
Write-Host "  python test_strategy_api.py" -ForegroundColor White
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "준비 완료! 위 단계대로 진행하세요." -ForegroundColor Green
