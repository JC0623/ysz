"""양도소득세 계산기 사용 예제"""

from datetime import date
from decimal import Decimal
from src.core import Fact, FactLedger, TaxCalculator


def example_basic_case():
    """기본 케이스: 일반지역, 3년 보유"""
    print("=" * 60)
    print("예제 1: 기본 케이스 (일반지역, 3년 보유)")
    print("=" * 60)

    # 1. FactLedger 생성
    ledger = FactLedger.create({
        "asset_type": Fact(
            value="residential",
            source="user_input",
            is_confirmed=True,
            confidence=1.0,
            entered_by="사용자"
        ),
        "acquisition_date": Fact(
            value=date(2020, 1, 1),
            source="등기부등본",
            is_confirmed=True,
            confidence=1.0,
            entered_by="사용자"
        ),
        "acquisition_price": Fact(
            value=Decimal("500000000"),  # 5억원
            source="계약서",
            is_confirmed=True,
            confidence=1.0,
            entered_by="사용자"
        ),
        "disposal_date": Fact(
            value=date(2023, 1, 1),
            source="계약서",
            is_confirmed=True,
            confidence=1.0,
            entered_by="사용자"
        ),
        "disposal_price": Fact(
            value=Decimal("800000000"),  # 8억원
            source="계약서",
            is_confirmed=True,
            confidence=1.0,
            entered_by="사용자"
        )
    })

    # 2. FactLedger 확정
    ledger.freeze()

    # 3. 계산
    calculator = TaxCalculator()
    result = calculator.calculate(ledger, is_adjusted_area=False)

    # 4. 결과 출력
    print(result.get_summary())
    print("\n" + result.get_trace_summary())


def example_short_term_case():
    """단기보유 케이스: 1년 미만 보유"""
    print("\n" + "=" * 60)
    print("예제 2: 단기보유 케이스 (1년 미만)")
    print("=" * 60)

    ledger = FactLedger.create({
        "asset_type": Fact(
            value="residential",
            source="user_input",
            is_confirmed=True,
            confidence=1.0,
            entered_by="사용자"
        ),
        "acquisition_date": Fact(
            value=date(2023, 1, 1),
            source="등기부등본",
            is_confirmed=True,
            confidence=1.0,
            entered_by="사용자"
        ),
        "acquisition_price": Fact(
            value=Decimal("1000000000"),  # 10억원
            source="계약서",
            is_confirmed=True,
            confidence=1.0,
            entered_by="사용자"
        ),
        "disposal_date": Fact(
            value=date(2023, 7, 1),
            source="계약서",
            is_confirmed=True,
            confidence=1.0,
            entered_by="사용자"
        ),
        "disposal_price": Fact(
            value=Decimal("1500000000"),  # 15억원
            source="계약서",
            is_confirmed=True,
            confidence=1.0,
            entered_by="사용자"
        )
    })

    ledger.freeze()

    calculator = TaxCalculator()
    result = calculator.calculate(ledger, is_adjusted_area=False)

    print(result.get_summary())


def example_multi_house_surcharge():
    """다주택자 중과세 케이스"""
    print("\n" + "=" * 60)
    print("예제 3: 다주택자 중과세 (조정지역, 2주택)")
    print("=" * 60)

    ledger = FactLedger.create({
        "asset_type": Fact(
            value="residential",
            source="user_input",
            is_confirmed=True,
            confidence=1.0,
            entered_by="사용자"
        ),
        "acquisition_date": Fact(
            value=date(2020, 1, 1),
            source="등기부등본",
            is_confirmed=True,
            confidence=1.0,
            entered_by="사용자"
        ),
        "acquisition_price": Fact(
            value=Decimal("500000000"),
            source="계약서",
            is_confirmed=True,
            confidence=1.0,
            entered_by="사용자"
        ),
        "disposal_date": Fact(
            value=date(2023, 1, 1),
            source="계약서",
            is_confirmed=True,
            confidence=1.0,
            entered_by="사용자"
        ),
        "disposal_price": Fact(
            value=Decimal("800000000"),
            source="계약서",
            is_confirmed=True,
            confidence=1.0,
            entered_by="사용자"
        ),
        "house_count": Fact(
            value=2,  # 2주택
            source="user_input",
            is_confirmed=True,
            confidence=1.0,
            entered_by="사용자"
        )
    })

    ledger.freeze()

    calculator = TaxCalculator()
    result = calculator.calculate(ledger, is_adjusted_area=True)  # 조정지역

    print(result.get_summary())

    if result.warnings:
        print("\n[경고]")
        for warning in result.warnings:
            print(f"  - {warning}")


def example_one_house_exemption():
    """1세대 1주택 비과세 케이스"""
    print("\n" + "=" * 60)
    print("예제 4: 1세대 1주택 비과세")
    print("=" * 60)

    ledger = FactLedger.create({
        "asset_type": Fact(
            value="residential",
            source="user_input",
            is_confirmed=True,
            confidence=1.0,
            entered_by="사용자"
        ),
        "acquisition_date": Fact(
            value=date(2020, 1, 1),
            source="등기부등본",
            is_confirmed=True,
            confidence=1.0,
            entered_by="사용자"
        ),
        "acquisition_price": Fact(
            value=Decimal("500000000"),
            source="계약서",
            is_confirmed=True,
            confidence=1.0,
            entered_by="사용자"
        ),
        "disposal_date": Fact(
            value=date(2023, 1, 1),
            source="계약서",
            is_confirmed=True,
            confidence=1.0,
            entered_by="사용자"
        ),
        "disposal_price": Fact(
            value=Decimal("800000000"),
            source="계약서",
            is_confirmed=True,
            confidence=1.0,
            entered_by="사용자"
        ),
        "is_primary_residence": Fact(
            value=True,
            source="user_input",
            is_confirmed=True,
            confidence=1.0,
            entered_by="사용자"
        ),
        "residence_period_years": Fact(
            value=3,
            source="user_input",
            is_confirmed=True,
            confidence=1.0,
            entered_by="사용자"
        )
    })

    ledger.freeze()

    calculator = TaxCalculator()
    result = calculator.calculate(ledger)

    print(result.get_summary())


if __name__ == "__main__":
    example_basic_case()
    example_short_term_case()
    example_multi_house_surcharge()
    example_one_house_exemption()
