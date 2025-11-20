"""RuleEngine: 세법 규칙 엔진 (누진세율 구조)"""

import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from decimal import Decimal


class RuleEngine:
    """YAML 파일에서 세법 규칙을 로드하고 적용하는 엔진

    누진세율 구조를 지원합니다.

    Attributes:
        rules: 로드된 규칙 딕셔너리
        version: 규칙 버전
    """

    def __init__(self, rules_file: str = "rules/tax_rules_2024.yaml"):
        """RuleEngine 초기화

        Args:
            rules_file: 규칙 파일 경로
        """
        self.rules_file = rules_file
        self.rules = self._load_rules()
        self.version = self.rules.get('version', 'unknown')

    def _load_rules(self) -> Dict:
        """YAML 파일에서 규칙 로드

        Returns:
            규칙 딕셔너리

        Raises:
            FileNotFoundError: 규칙 파일이 없는 경우
            yaml.YAMLError: YAML 파싱 오류
        """
        rules_path = Path(self.rules_file)

        if not rules_path.exists():
            raise FileNotFoundError(f"규칙 파일을 찾을 수 없습니다: {rules_path}")

        with open(rules_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def get_short_term_rate(
        self,
        asset_type: str,
        holding_period_years: int
    ) -> Optional[Dict[str, Any]]:
        """단기보유 차등 비례세율 찾기 (2년 미만)

        Args:
            asset_type: 자산 유형 ('residential' 또는 'non_residential')
            holding_period_years: 보유 기간(년)

        Returns:
            적용 가능한 세율 규칙 또는 None
        """
        if holding_period_years >= 2:
            return None

        short_term_rates = self.rules.get('short_term_rates', {})

        for rate_name, rate_data in short_term_rates.items():
            if rate_data.get('asset_type') == asset_type:
                min_period = rate_data.get('holding_period_min', 0)
                max_period = rate_data.get('holding_period_max', 999)

                if min_period <= holding_period_years < max_period:
                    return {
                        'name': rate_data.get('name', ''),
                        'rate': rate_data.get('rate'),
                        'description': rate_data.get('description', ''),
                        'legal_basis': rate_data.get('legal_basis', ''),
                        'is_proportional': True  # 비례세율
                    }

        return None

    def calculate_progressive_tax(
        self,
        taxable_income: Decimal
    ) -> Tuple[float, Decimal, str]:
        """누진세율 계산 (2년 이상 보유)

        과세표준 구간에 따라 적용 세율 및 누진공제액을 반환합니다.

        Args:
            taxable_income: 과세표준

        Returns:
            (적용 세율, 누진공제액, 설명) 튜플
        """
        brackets = self.rules.get('progressive_tax_brackets', [])

        for bracket in brackets:
            threshold = bracket.get('threshold')

            # threshold가 None이면 최고 구간
            if threshold is None or taxable_income <= threshold:
                return (
                    bracket.get('rate'),
                    Decimal(str(bracket.get('deduction', 0))),
                    bracket.get('description', '')
                )

        # 기본값 (최고 구간)
        last_bracket = brackets[-1]
        return (
            last_bracket.get('rate'),
            Decimal(str(last_bracket.get('deduction', 0))),
            last_bracket.get('description', '')
        )

    def get_multi_house_surcharge(
        self,
        house_count: int,
        is_adjusted_area: bool,
        holding_period_years: int
    ) -> float:
        """다주택자 중과세율 조회

        Args:
            house_count: 보유 주택 수
            is_adjusted_area: 조정대상지역 여부
            holding_period_years: 보유 기간

        Returns:
            추가 세율 (없으면 0.0)
        """
        if not is_adjusted_area or holding_period_years < 2:
            return 0.0

        surcharges = self.rules.get('multi_house_surcharge', {})

        if house_count >= 3:
            # 3주택 이상
            three_or_more = surcharges.get('three_or_more_houses', {})
            return three_or_more.get('additional_rate', 0.0)
        elif house_count == 2:
            # 2주택
            two_houses = surcharges.get('two_houses', {})
            return two_houses.get('additional_rate', 0.0)

        return 0.0

    def calculate_long_term_deduction_rate(
        self,
        holding_period_years: int,
        is_primary_residence: bool = False,
        residence_period_years: int = 0
    ) -> float:
        """장기보유특별공제율 계산

        Args:
            holding_period_years: 보유 기간(년)
            is_primary_residence: 1세대 1주택 여부
            residence_period_years: 거주 기간(년)

        Returns:
            공제율 (0.0~0.80)
        """
        deduction_rule = self.rules.get('deductions', {}).get('long_term_holding_deduction', {})

        if holding_period_years < 3:
            return 0.0

        # 1세대 1주택
        if is_primary_residence and residence_period_years >= 2:
            one_house = deduction_rule.get('one_house_owner', {})

            # 보유기간 공제
            base_rates = one_house.get('base_rates', {})
            holding_rate = 0.0
            for years, rate in base_rates.items():
                if holding_period_years >= years:
                    holding_rate = rate

            # 거주기간 공제
            residence_rates = one_house.get('residence_rates', {})
            residence_rate = 0.0
            for years, rate in residence_rates.items():
                if residence_period_years >= years:
                    residence_rate = rate

            # 합산
            total_rate = holding_rate + residence_rate
            max_rate = one_house.get('max_rate', 0.80)
            return min(total_rate, max_rate)

        # 일반 자산
        else:
            general = deduction_rule.get('general', {})
            rates = general.get('rates', {})
            max_rate = general.get('max_rate', 0.30)

            applicable_rate = 0.0
            for years, rate in rates.items():
                if holding_period_years >= years:
                    applicable_rate = rate

            return min(applicable_rate, max_rate)

    def check_exemption_eligibility(
        self,
        is_primary_residence: bool,
        residence_period_years: int,
        holding_period_years: int
    ) -> Optional[Dict[str, Any]]:
        """1세대 1주택 비과세 요건 확인

        Args:
            is_primary_residence: 1세대 1주택 여부
            residence_period_years: 거주 기간(년)
            holding_period_years: 보유 기간(년)

        Returns:
            비과세 규칙 딕셔너리 또는 None
        """
        exemption = self.rules.get('deductions', {}).get('one_house_exemption', {})

        facts = {
            'is_primary_residence': is_primary_residence,
            'residence_period_years': residence_period_years,
            'holding_period_years': holding_period_years
        }

        conditions = exemption.get('conditions', [])
        if self._check_conditions(conditions, facts):
            return {
                'name': exemption.get('name', ''),
                'exemption_limit': exemption.get('exemption_limit', 0),
                'description': exemption.get('description', ''),
                'legal_basis': exemption.get('legal_basis', '')
            }

        return None

    def get_basic_deduction(self) -> Decimal:
        """기본공제액 조회

        Returns:
            기본공제액 (연 250만원)
        """
        basic = self.rules.get('additional_considerations', {}).get('basic_deduction', {})
        return Decimal(str(basic.get('amount', 2500000)))

    def get_local_tax_rate(self) -> float:
        """지방소득세율 조회

        Returns:
            지방소득세율 (10%)
        """
        local_tax = self.rules.get('additional_considerations', {}).get('local_income_tax', {})
        return local_tax.get('rate', 0.10)

    def _check_conditions(
        self,
        conditions: List[Dict],
        facts: Dict[str, Any]
    ) -> bool:
        """조건 검사

        모든 조건이 충족되면 True를 반환합니다.

        Args:
            conditions: 조건 리스트
            facts: 사실관계 딕셔너리

        Returns:
            모든 조건이 충족되면 True
        """
        for condition in conditions:
            field = condition.get('field')
            operator = condition.get('operator')
            value = condition.get('value')

            if field not in facts:
                return False

            fact_value = facts[field]

            if not self._evaluate_condition(fact_value, operator, value):
                return False

        return True

    def _evaluate_condition(
        self,
        fact_value: Any,
        operator: str,
        target_value: Any
    ) -> bool:
        """단일 조건 평가

        Args:
            fact_value: 사실 값
            operator: 연산자 (eq, ne, lt, lte, gt, gte)
            target_value: 비교 대상 값

        Returns:
            조건이 충족되면 True
        """
        operators = {
            'eq': lambda a, b: a == b,
            'ne': lambda a, b: a != b,
            'lt': lambda a, b: a < b,
            'lte': lambda a, b: a <= b,
            'gt': lambda a, b: a > b,
            'gte': lambda a, b: a >= b,
        }

        op_func = operators.get(operator)
        if not op_func:
            raise ValueError(f"지원하지 않는 연산자: {operator}")

        return op_func(fact_value, target_value)

    def validate_required_fields(
        self,
        facts: Dict[str, Any]
    ) -> List[str]:
        """필수 필드 검증

        Args:
            facts: 사실관계 딕셔너리

        Returns:
            누락된 필드 리스트
        """
        validation = self.rules.get('validation_rules', {})
        required = validation.get('required_fields', [])

        missing = []
        for field in required:
            if field not in facts or facts[field] is None:
                missing.append(field)

        return missing

    def get_calculation_steps(self) -> List[Dict]:
        """계산 단계 목록 조회

        Returns:
            계산 단계 리스트
        """
        return self.rules.get('calculation_sequence', [])

    def get_rule_metadata(self) -> Dict[str, Any]:
        """규칙 메타데이터 조회

        Returns:
            메타데이터 딕셔너리
        """
        return {
            'version': self.version,
            'effective_date': self.rules.get('effective_date', ''),
            'description': self.rules.get('description', ''),
            'metadata': self.rules.get('metadata', {})
        }
