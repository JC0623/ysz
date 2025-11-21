"""Strategy Models: 전략 수립 관련 데이터 모델

StrategyAgent가 사용하는 케이스 분류, 시나리오, 전략 모델입니다.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from decimal import Decimal
from enum import Enum


class CaseCategory(str, Enum):
    """케이스 분류"""
    SINGLE_HOUSE_EXEMPT = "1주택_비과세"  # 1세대 1주택 비과세
    SINGLE_HOUSE_TAXABLE = "1주택_과세"  # 1주택이지만 비과세 요건 미달
    MULTI_HOUSE_HEAVY = "다주택_중과"  # 다주택 중과세
    MULTI_HOUSE_GENERAL = "다주택_일반"  # 다주택 일반과세
    ADJUSTED_AREA_HEAVY = "조정지역_중과"  # 조정대상지역 중과
    CORPORATE = "법인_양도"  # 법인 양도
    INHERITANCE = "상속_취득"  # 상속 취득 자산
    GIFT = "증여_취득"  # 증여 취득 자산
    COMPLEX = "복합_케이스"  # 여러 조건 복합
    OUT_OF_SCOPE = "범위외"  # MVP 범위 밖


class RiskLevel(str, Enum):
    """리스크 수준"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ClassificationRule:
    """분류 규칙 (결정론적)"""
    rule_id: str
    condition: str  # 조건 설명
    category: CaseCategory
    priority: int  # 우선순위 (낮을수록 먼저 체크)

    def __str__(self):
        return f"Rule[{self.rule_id}]: {self.condition} → {self.category.value}"


@dataclass
class Scenario:
    """시나리오 (계산 가능한 옵션)

    각 시나리오는 구체적인 행동 계획과 예상 결과를 포함합니다.
    """
    scenario_id: str
    name: str  # "지금_양도", "1년_후_양도" 등
    description: str

    # 시나리오 조건
    timing: str  # "즉시", "1년_후", "2년_후"
    actions: List[str]  # ["양도", "증여_후_양도"] 등

    # 계산 결과 (결정론적)
    expected_tax: Decimal  # 예상 세액
    expected_local_tax: Decimal  # 예상 지방세
    total_cost: Decimal  # 총 비용 (세금 + 기타)

    # 추가 비용/수익
    additional_costs: Dict[str, Decimal] = field(default_factory=dict)  # {"보유세": 3000000}
    expected_gains: Dict[str, Decimal] = field(default_factory=dict)  # {"시세상승": 50000000}

    # 평가 (로직 기반)
    pros: List[str] = field(default_factory=list)
    cons: List[str] = field(default_factory=list)
    required_conditions: List[str] = field(default_factory=list)

    # 법적 근거
    legal_basis: List[str] = field(default_factory=list)  # ["소득세법 제89조"]

    # 실행 가능성
    is_feasible: bool = True
    feasibility_notes: Optional[str] = None

    def net_benefit(self) -> Decimal:
        """순 편익 계산"""
        total_gains = sum(self.expected_gains.values(), Decimal(0))
        total_costs = self.total_cost + sum(self.additional_costs.values(), Decimal(0))
        return total_gains - total_costs

    def to_dict(self) -> Dict[str, Any]:
        return {
            'scenario_id': self.scenario_id,
            'name': self.name,
            'description': self.description,
            'timing': self.timing,
            'actions': self.actions,
            'expected_tax': float(self.expected_tax),
            'expected_local_tax': float(self.expected_local_tax),
            'total_cost': float(self.total_cost),
            'additional_costs': {k: float(v) for k, v in self.additional_costs.items()},
            'expected_gains': {k: float(v) for k, v in self.expected_gains.items()},
            'net_benefit': float(self.net_benefit()),
            'pros': self.pros,
            'cons': self.cons,
            'required_conditions': self.required_conditions,
            'legal_basis': self.legal_basis,
            'is_feasible': self.is_feasible,
            'feasibility_notes': self.feasibility_notes
        }


@dataclass
class Risk:
    """리스크 항목"""
    risk_id: str
    level: RiskLevel
    title: str
    description: str
    impact: str  # 영향도 설명
    mitigation: Optional[str] = None  # 완화 방안

    def to_dict(self) -> Dict[str, Any]:
        return {
            'risk_id': self.risk_id,
            'level': self.level.value,
            'title': self.title,
            'description': self.description,
            'impact': self.impact,
            'mitigation': self.mitigation
        }


@dataclass
class MissingInfo:
    """추가 필요 정보"""
    info_id: str
    field_name: str
    description: str
    reason: str  # 왜 필요한가
    is_critical: bool  # 필수 여부
    how_to_obtain: Optional[str] = None  # 어떻게 얻는가

    def to_dict(self) -> Dict[str, Any]:
        return {
            'info_id': self.info_id,
            'field_name': self.field_name,
            'description': self.description,
            'reason': self.reason,
            'is_critical': self.is_critical,
            'how_to_obtain': self.how_to_obtain
        }


@dataclass
class Strategy:
    """전략 (분류 + 시나리오들 + 분석)

    StrategyAgent의 최종 출력물입니다.
    """
    strategy_id: str = field(default_factory=lambda: f"STR{datetime.now().strftime('%Y%m%d%H%M%S')}")
    created_at: datetime = field(default_factory=datetime.now)

    # 케이스 분류 (결정론적)
    category: CaseCategory = CaseCategory.COMPLEX
    classification_reasoning: str = ""  # 분류 근거 (로직 설명)
    classification_rules_applied: List[str] = field(default_factory=list)  # 적용된 규칙 ID

    # 시나리오들 (계산된)
    scenarios: List[Scenario] = field(default_factory=list)

    # 추천 (로직 기반)
    recommended_scenario_id: Optional[str] = None
    recommendation_reasoning: str = ""  # 추천 근거 (로직 설명)

    # 리스크 분석 (규칙 기반)
    risks: List[Risk] = field(default_factory=list)

    # 추가 필요 정보
    missing_info: List[MissingInfo] = field(default_factory=list)

    # 계산 메타데이터
    confidence_score: float = 1.0  # 전체 전략의 신뢰도 (0~1)
    rule_version: Optional[str] = None  # 사용된 규칙 버전

    # LLM 생성 내용 (선택적)
    llm_explanation: Optional[str] = None  # LLM이 생성한 친절한 설명
    llm_additional_advice: Optional[str] = None  # LLM 추가 조언

    def get_recommended_scenario(self) -> Optional[Scenario]:
        """추천 시나리오 반환"""
        if not self.recommended_scenario_id:
            return None

        for scenario in self.scenarios:
            if scenario.scenario_id == self.recommended_scenario_id:
                return scenario
        return None

    def get_high_risks(self) -> List[Risk]:
        """높은 리스크만 필터링"""
        return [r for r in self.risks if r.level in [RiskLevel.HIGH, RiskLevel.CRITICAL]]

    def get_critical_missing_info(self) -> List[MissingInfo]:
        """필수 누락 정보만 필터링"""
        return [m for m in self.missing_info if m.is_critical]

    def is_ready_to_execute(self) -> bool:
        """실행 가능 여부 (필수 정보 모두 확보?)"""
        return len(self.get_critical_missing_info()) == 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'strategy_id': self.strategy_id,
            'created_at': self.created_at.isoformat(),
            'category': self.category.value,
            'classification_reasoning': self.classification_reasoning,
            'classification_rules_applied': self.classification_rules_applied,
            'scenarios': [s.to_dict() for s in self.scenarios],
            'recommended_scenario_id': self.recommended_scenario_id,
            'recommendation_reasoning': self.recommendation_reasoning,
            'risks': [r.to_dict() for r in self.risks],
            'missing_info': [m.to_dict() for m in self.missing_info],
            'confidence_score': self.confidence_score,
            'rule_version': self.rule_version,
            'llm_explanation': self.llm_explanation,
            'llm_additional_advice': self.llm_additional_advice,
            'is_ready_to_execute': self.is_ready_to_execute()
        }

    def __str__(self) -> str:
        return (
            f"Strategy(category={self.category.value}, "
            f"scenarios={len(self.scenarios)}, "
            f"recommended={self.recommended_scenario_id})"
        )
