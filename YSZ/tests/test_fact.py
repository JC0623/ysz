"""Fact 클래스 테스트"""

import pytest
from datetime import datetime
from decimal import Decimal

from src.core.fact import Fact


class TestFactCreation:
    """Fact 생성 테스트"""

    def test_create_basic_fact(self):
        """기본 Fact 생성"""
        fact = Fact(value=100)

        assert fact.value == 100
        assert fact.source == "user_input"
        assert fact.confidence == 1.0
        assert fact.is_confirmed is False
        assert fact.entered_by == "system"
        assert isinstance(fact.entered_at, datetime)

    def test_create_fact_with_metadata(self):
        """메타데이터를 포함한 Fact 생성"""
        fact = Fact(
            value=Decimal("500000000"),
            source="document",
            confidence=1.0,
            is_confirmed=True,
            entered_by="김세무사",
            notes="등기부등본 기준"
        )

        assert fact.value == Decimal("500000000")
        assert fact.source == "document"
        assert fact.is_confirmed is True
        assert fact.entered_by == "김세무사"
        assert fact.notes == "등기부등본 기준"


class TestFactValidation:
    """Fact 유효성 검증 테스트"""

    def test_confidence_range_validation(self):
        """confidence 범위 검증"""
        # 유효한 범위
        Fact(value=100, confidence=0.0)
        Fact(value=100, confidence=0.5)
        Fact(value=100, confidence=1.0)

        # 유효하지 않은 범위
        with pytest.raises(ValueError, match="confidence는 0.0에서 1.0 사이여야 합니다"):
            Fact(value=100, confidence=-0.1)

        with pytest.raises(ValueError, match="confidence는 0.0에서 1.0 사이여야 합니다"):
            Fact(value=100, confidence=1.1)

    def test_confirmed_must_have_confidence_one(self):
        """확정값은 confidence가 1.0이어야 함"""
        # 정상 케이스
        Fact(value=100, is_confirmed=True, confidence=1.0)

        # 비정상 케이스
        with pytest.raises(ValueError, match="확정된 값.*confidence가 1.0이어야 합니다"):
            Fact(value=100, is_confirmed=True, confidence=0.9)


class TestFactImmutability:
    """Fact 불변성 테스트"""

    def test_cannot_modify_value(self):
        """값 수정 불가"""
        fact = Fact(value=100)

        with pytest.raises(Exception):  # FrozenInstanceError
            fact.value = 200

    def test_cannot_modify_metadata(self):
        """메타데이터 수정 불가"""
        fact = Fact(value=100, source="user")

        with pytest.raises(Exception):
            fact.source = "system"


class TestFactMethods:
    """Fact 메서드 테스트"""

    def test_confirm_method(self):
        """confirm 메서드 테스트"""
        estimated_fact = Fact(
            value=Decimal("5000000"),
            confidence=0.8,
            entered_by="system"
        )

        confirmed_fact = estimated_fact.confirm(
            confirmed_by="김세무사",
            notes="계약서 확인 완료"
        )

        # 원본은 변경 안 됨
        assert estimated_fact.confidence == 0.8
        assert estimated_fact.is_confirmed is False

        # 새 객체는 확정됨
        assert confirmed_fact.confidence == 1.0
        assert confirmed_fact.is_confirmed is True
        assert confirmed_fact.entered_by == "김세무사"
        assert confirmed_fact.notes == "계약서 확인 완료"

    def test_update_value_method(self):
        """update_value 메서드 테스트"""
        original = Fact(
            value=100,
            is_confirmed=True,
            entered_by="user1"
        )

        updated = original.update_value(
            new_value=200,
            updated_by="user2",
            notes="오류 수정"
        )

        # 원본 불변
        assert original.value == 100
        assert original.is_confirmed is True

        # 새 객체는 변경됨
        assert updated.value == 200
        assert updated.is_confirmed is False  # 값 변경 시 확정 해제
        assert updated.entered_by == "user2"
        assert updated.notes == "오류 수정"

    def test_create_user_input_helper(self):
        """create_user_input 헬퍼 메서드 테스트"""
        fact = Fact.create_user_input(
            value=Decimal("700000000"),
            entered_by="김세무사",
            is_confirmed=True,
            notes="고객 제공"
        )

        assert fact.value == Decimal("700000000")
        assert fact.source == "user_input"
        assert fact.confidence == 1.0
        assert fact.is_confirmed is True
        assert fact.entered_by == "김세무사"

    def test_create_estimated_helper(self):
        """create_estimated 헬퍼 메서드 테스트"""
        fact = Fact.create_estimated(
            value=Decimal("500000000"),
            confidence=0.7,
            source="ai_prediction",
            notes="과거 데이터 기반 추정"
        )

        assert fact.value == Decimal("500000000")
        assert fact.source == "ai_prediction"
        assert fact.confidence == 0.7
        assert fact.is_confirmed is False


class TestFactSerialization:
    """Fact 직렬화 테스트"""

    def test_to_dict(self):
        """to_dict 메서드 테스트"""
        fact = Fact(
            value=100,
            source="user",
            confidence=0.9,
            entered_by="test_user"
        )

        data = fact.to_dict()

        assert data['value'] == 100
        assert data['source'] == "user"
        assert data['confidence'] == 0.9
        assert data['entered_by'] == "test_user"
        assert 'entered_at' in data

    def test_str_representation(self):
        """문자열 표현 테스트"""
        confirmed = Fact(value=100, is_confirmed=True, entered_by="user1")
        estimated = Fact(value=200, confidence=0.8, entered_by="user2")

        assert "확정" in str(confirmed)
        assert "추정" in str(estimated)
        assert "80%" in str(estimated)
