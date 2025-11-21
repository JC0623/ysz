"""의존성 확인 스크립트

Phase 2.5 Part 1 테스트를 위한 필수 패키지 확인
"""

import sys

def check_dependencies():
    """필수 패키지 확인"""
    print("=" * 60)
    print("YSZ 의존성 확인")
    print("=" * 60)

    missing = []
    installed = []

    # 필수 패키지 목록
    required_packages = [
        ('fastapi', 'FastAPI'),
        ('uvicorn', 'Uvicorn'),
        ('anthropic', 'Anthropic Claude SDK'),
        ('pydantic', 'Pydantic'),
        ('requests', 'Requests'),
    ]

    for package, name in required_packages:
        try:
            __import__(package)
            installed.append(f"✅ {name} ({package})")
        except ImportError:
            missing.append(f"❌ {name} ({package})")

    print("\n설치된 패키지:")
    for item in installed:
        print(f"  {item}")

    if missing:
        print("\n❌ 누락된 패키지:")
        for item in missing:
            print(f"  {item}")
        print("\n설치 방법:")
        print("  pip install fastapi uvicorn anthropic requests")
        return False
    else:
        print("\n🎉 모든 필수 패키지가 설치되어 있습니다!")
        return True


def check_project_structure():
    """프로젝트 구조 확인"""
    import os

    print("\n" + "=" * 60)
    print("프로젝트 구조 확인")
    print("=" * 60)

    required_paths = [
        'src/api/routers/strategy.py',
        'src/agents/strategy_agent.py',
        'test_strategy_api.py',
        'docs/testing_guide.md',
    ]

    all_exist = True
    for path in required_paths:
        if os.path.exists(path):
            print(f"  ✅ {path}")
        else:
            print(f"  ❌ {path} (누락)")
            all_exist = False

    return all_exist


def main():
    """메인 실행"""
    deps_ok = check_dependencies()
    struct_ok = check_project_structure()

    print("\n" + "=" * 60)
    print("결과")
    print("=" * 60)

    if deps_ok and struct_ok:
        print("✅ 테스트를 실행할 준비가 되었습니다!")
        print("\n다음 단계:")
        print("  1. cd src")
        print("  2. python -m api.main")
        print("  3. 새 터미널: python test_strategy_api.py")
        return 0
    else:
        print("❌ 일부 문제가 발견되었습니다. 위 내용을 확인하세요.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
