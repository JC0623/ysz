"""StrategyAgent API 간단 테스트 스크립트

사용법:
    python test_strategy_api.py
"""

import requests
import json
from datetime import date

# API 베이스 URL
BASE_URL = "http://localhost:8000"

def test_health_check():
    """Health Check 테스트"""
    print("\n=== Health Check ===")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/strategy/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_categories():
    """카테고리 목록 테스트"""
    print("\n=== 카테고리 목록 ===")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/strategy/categories")
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"카테고리 수: {len(data['categories'])}")
        for cat in data['categories']:
            print(f"  - {cat['code']}: {cat['name']}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_strategy_analyze_case1():
    """전략 분석 테스트 - 1주택 비과세"""
    print("\n=== 전략 분석: 1주택 비과세 ===")

    payload = {
        "acquisition_date": "2020-01-15",
        "acquisition_price": 500000000,
        "disposal_date": "2024-12-01",
        "disposal_price": 1000000000,
        "asset_type": "residential",
        "house_count": 1,
        "residence_period_years": 3,
        "is_adjusted_area": False,
        "necessary_expenses": 0,
        "enable_explanation": True
    }

    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/strategy/analyze",
            json=payload
        )
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"\n카테고리: {data['category']}")
            print(f"분류 근거: {data['classification_reasoning']}")
            print(f"\n시나리오 수: {len(data['scenarios'])}")
            for scenario in data['scenarios']:
                print(f"  - {scenario['scenario_name']}")
                print(f"    예상 세액: {scenario['expected_tax']:,}원")
                print(f"    순 편익: {scenario['net_benefit']:,}원")
                if scenario['is_recommended']:
                    print(f"    ⭐ 추천")

            print(f"\n추천 시나리오: {data['recommended_scenario_id']}")
            print(f"리스크 수: {len(data['risks'])}")

            if data.get('llm_explanation'):
                print(f"\nAI 설명:\n{data['llm_explanation'][:200]}...")

            return True
        else:
            print(f"Error: {response.text}")
            return False

    except Exception as e:
        print(f"Error: {e}")
        return False


def test_strategy_analyze_case2():
    """전략 분석 테스트 - 다주택 중과세"""
    print("\n=== 전략 분석: 다주택 중과세 ===")

    payload = {
        "acquisition_date": "2022-06-15",
        "acquisition_price": 800000000,
        "disposal_date": "2024-12-01",
        "disposal_price": 1200000000,
        "asset_type": "residential",
        "house_count": 3,
        "residence_period_years": 0,
        "is_adjusted_area": True,
        "necessary_expenses": 10000000,
        "enable_explanation": True
    }

    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/strategy/analyze",
            json=payload
        )
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"\n카테고리: {data['category']}")
            print(f"분류 근거: {data['classification_reasoning']}")
            print(f"\n시나리오 수: {len(data['scenarios'])}")
            for scenario in data['scenarios']:
                print(f"  - {scenario['scenario_name']}")
                print(f"    예상 세액: {scenario['expected_tax']:,}원")
                if scenario['is_recommended']:
                    print(f"    ⭐ 추천")

            print(f"\n리스크 수: {len(data['risks'])}")
            for risk in data['risks']:
                print(f"  - [{risk['level'].upper()}] {risk['title']}")
                print(f"    {risk['description']}")

            return True
        else:
            print(f"Error: {response.text}")
            return False

    except Exception as e:
        print(f"Error: {e}")
        return False


def main():
    """메인 테스트 실행"""
    print("=" * 60)
    print("YSZ StrategyAgent API 테스트")
    print("=" * 60)

    results = []

    # 1. Health Check
    results.append(("Health Check", test_health_check()))

    # 2. 카테고리 목록
    results.append(("카테고리 목록", test_categories()))

    # 3. 전략 분석 - 1주택 비과세
    results.append(("전략 분석 (1주택)", test_strategy_analyze_case1()))

    # 4. 전략 분석 - 다주택 중과세
    results.append(("전략 분석 (다주택)", test_strategy_analyze_case2()))

    # 결과 요약
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name:30s} {status}")

    total = len(results)
    passed = sum(1 for _, p in results if p)
    print(f"\n총 {total}개 중 {passed}개 통과 ({passed/total*100:.0f}%)")

    if passed == total:
        print("\n🎉 모든 테스트 통과!")
    else:
        print(f"\n⚠️  {total - passed}개 테스트 실패")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n테스트 중단됨")
    except Exception as e:
        print(f"\n\n예상치 못한 오류: {e}")
