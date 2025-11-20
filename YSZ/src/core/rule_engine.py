"""RuleEngine: 세법 규칙 엔진"""

import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from decimal import Decimal
from datetime import date


class RuleEngine:
    """YAML 파일에서 세법 규칙을 로드하고 적용하는 엔진

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

    def find_applicable_tax_rate(
        self,
        holding_period_years: int,
        is_adjusted_area: bool = False
    ) -> Dict[str, Any]:
        """적용 가능한 세율 규칙 찾기

        조건에 맞는 규칙 중 우선순위가 가장 높은 것을 반환합니다.

        Args:
            holding_period_years: 보유 기간(년)
            is_adjusted_area: 조정대상지역 여부

        Returns:
            적용 가능한 세율 규칙 딕셔너리

        Raises:
            ValueError: 적용 가능한 규칙이 없는 경우
        """
        tax_rates = self.rules.get('tax_rates', {})
        applicable_rules = []

        facts = {
            'holding_period_years': holding_period_years,
            'is_adjusted_area': is_adjusted_area
        }

        for rule_name, rule_data in tax_rates.items():
            if self._check_conditions(rule_data.get('conditions', []), facts):
                applicable_rules.append({
                    'name': rule_name,
                    'priority': rule_data.get('priority', 0),
                    'rate': rule_data.get('rate'),
                    'description': rule_data.get('description', ''),
                    'legal_basis': rule_data.get('legal_basis', ''),
                    **rule_data
                })

        if not applicable_rules:
            raise ValueError(
                f"적용 가능한 세율 규칙을 찾을 수 없습니다. "
                f"보유기간: {holding_period_years}년, 조정지역: {is_adjusted_area}"
            )

        # 우선순위가 가장 높은 규칙 반환 (priority 값이 클수록 우선)
        return max(applicable_rules, key=lambda x: x['priority'])

    def calculate_long_term_deduction_rate(
        self,
        holding_period_years: int
    ) -> float:
        """장기보유특별공제율 계산

        Args:
            holding_period_years: 보유 기간(년)

        Returns:
            공제율 (0.0~0.30)
        """
        deduction_rule = self.rules.get('deductions', {}).get('long_term_holding_deduction', {})
        rates = deduction_rule.get('rates', {})
        max_rate = deduction_rule.get('max_rate', 0.30)

        if holding_period_years < 3:
            return 0.0

        # 보유 기간에 해당하는 공제율 찾기
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
        return self.rules.get('calculation_steps', [])

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
