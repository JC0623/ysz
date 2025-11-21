"""RuleVersion: 세법 규칙 버전 관리 시스템

AI 에이전트가 사용한 세법 규칙의 버전을 추적하고 관리합니다.
모든 계산과 판단은 특정 Rule Version에 기반하며, 감사 추적을 위해 기록됩니다.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
import yaml


@dataclass(frozen=True)
class RuleVersion:
    """세법 규칙 버전

    불변 객체로 세법 규칙의 특정 버전을 나타냅니다.

    Attributes:
        rule_id: 규칙 고유 식별자 (예: "tax_rate_2024")
        version: 버전 문자열 (예: "2024.1.0")
        effective_date: 시행일
        rule_type: 규칙 유형 ("tax_rate", "deduction", "exemption", "calculation")
        rule_data: 규칙 데이터 (YAML에서 로드)
        source: 법적 근거 (예: "소득세법 제95조")
        description: 규칙 설명
        supersedes: 이전 버전 ID (있는 경우)
        created_at: 생성 시각

    Example:
        >>> rule = RuleVersion(
        ...     rule_id="primary_residence_exemption",
        ...     version="2024.1.0",
        ...     effective_date=date(2024, 1, 1),
        ...     rule_type="exemption",
        ...     rule_data={"max_exemption": 1200000000, "holding_period_years": 2},
        ...     source="소득세법 제89조",
        ...     description="1세대 1주택 비과세"
        ... )
    """

    rule_id: str
    version: str
    effective_date: date
    rule_type: str
    rule_data: Dict[str, Any]
    source: str
    description: str
    supersedes: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    def is_effective_on(self, target_date: date) -> bool:
        """특정 날짜에 이 규칙이 유효한지 확인

        Args:
            target_date: 확인할 날짜

        Returns:
            유효하면 True, 아니면 False
        """
        return target_date >= self.effective_date

    def get_value(self, key: str, default: Any = None) -> Any:
        """규칙 데이터에서 값 가져오기

        Args:
            key: 데이터 키
            default: 기본값

        Returns:
            규칙 데이터의 값 또는 기본값
        """
        return self.rule_data.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환

        Returns:
            규칙 정보를 담은 딕셔너리
        """
        return {
            'rule_id': self.rule_id,
            'version': self.version,
            'effective_date': self.effective_date.isoformat(),
            'rule_type': self.rule_type,
            'rule_data': self.rule_data,
            'source': self.source,
            'description': self.description,
            'supersedes': self.supersedes,
            'created_at': self.created_at.isoformat()
        }

    def __str__(self) -> str:
        return f"RuleVersion({self.rule_id} v{self.version}, effective {self.effective_date})"

    def __repr__(self) -> str:
        return (
            f"RuleVersion(rule_id={self.rule_id!r}, version={self.version!r}, "
            f"effective_date={self.effective_date!r})"
        )


class RuleRegistry:
    """세법 규칙 레지스트리

    세법 규칙의 버전을 관리하고 검색하는 중앙 저장소입니다.
    YAML 파일에서 규칙을 로드하고, 날짜별로 적용 가능한 규칙을 제공합니다.

    Attributes:
        rules: rule_id -> List[RuleVersion] 매핑
        rules_dir: 규칙 YAML 파일이 저장된 디렉토리
    """

    def __init__(self, rules_dir: Optional[Path] = None):
        """
        Args:
            rules_dir: 규칙 YAML 파일 디렉토리 (기본값: ./rules)
        """
        self.rules: Dict[str, List[RuleVersion]] = {}
        self.rules_dir = rules_dir or Path(__file__).parent.parent.parent / "rules"

        # 초기화 시 규칙 로드
        if self.rules_dir.exists():
            self._load_rules_from_dir()

    def register_rule(self, rule: RuleVersion) -> None:
        """규칙 등록

        Args:
            rule: 등록할 RuleVersion

        Raises:
            ValueError: 동일한 rule_id와 version이 이미 존재하는 경우
        """
        if rule.rule_id not in self.rules:
            self.rules[rule.rule_id] = []

        # 중복 확인
        for existing_rule in self.rules[rule.rule_id]:
            if existing_rule.version == rule.version:
                raise ValueError(
                    f"Rule {rule.rule_id} version {rule.version} already exists"
                )

        # 추가 및 정렬 (최신 버전이 먼저)
        self.rules[rule.rule_id].append(rule)
        self.rules[rule.rule_id].sort(
            key=lambda r: r.effective_date,
            reverse=True
        )

    def get_rule(self, rule_id: str, effective_date: date) -> Optional[RuleVersion]:
        """특정 날짜에 유효한 규칙 가져오기

        Args:
            rule_id: 규칙 ID
            effective_date: 기준 날짜

        Returns:
            해당 날짜에 유효한 RuleVersion, 없으면 None
        """
        if rule_id not in self.rules:
            return None

        # 기준 날짜 이전에 시행된 규칙 중 가장 최신 규칙 반환
        for rule in self.rules[rule_id]:
            if rule.is_effective_on(effective_date):
                return rule

        return None

    def get_latest_rule(self, rule_id: str) -> Optional[RuleVersion]:
        """최신 규칙 가져오기

        Args:
            rule_id: 규칙 ID

        Returns:
            가장 최신 RuleVersion, 없으면 None
        """
        if rule_id not in self.rules or not self.rules[rule_id]:
            return None

        return self.rules[rule_id][0]  # 이미 정렬되어 있음

    def get_rule_by_version(self, rule_id: str, version: str) -> Optional[RuleVersion]:
        """특정 버전의 규칙 가져오기

        Args:
            rule_id: 규칙 ID
            version: 버전 문자열

        Returns:
            해당 버전의 RuleVersion, 없으면 None
        """
        if rule_id not in self.rules:
            return None

        for rule in self.rules[rule_id]:
            if rule.version == version:
                return rule

        return None

    def list_rules(self, rule_type: Optional[str] = None) -> List[RuleVersion]:
        """규칙 목록 가져오기

        Args:
            rule_type: 필터링할 규칙 유형 (None이면 전체)

        Returns:
            RuleVersion 리스트
        """
        all_rules = []
        for rule_list in self.rules.values():
            all_rules.extend(rule_list)

        if rule_type:
            all_rules = [r for r in all_rules if r.rule_type == rule_type]

        return sorted(all_rules, key=lambda r: r.effective_date, reverse=True)

    def list_rule_ids(self) -> List[str]:
        """등록된 모든 규칙 ID 목록

        Returns:
            규칙 ID 리스트
        """
        return sorted(self.rules.keys())

    def _load_rules_from_dir(self) -> None:
        """규칙 디렉토리에서 YAML 파일 로드

        rules/ 디렉토리의 모든 .yml, .yaml 파일을 읽어서
        RuleVersion으로 변환하여 등록합니다.
        """
        if not self.rules_dir.exists():
            return

        for yaml_file in self.rules_dir.glob("*.y*ml"):
            try:
                self._load_rule_file(yaml_file)
            except Exception as e:
                print(f"Warning: Failed to load rule file {yaml_file}: {e}")

    def _load_rule_file(self, file_path: Path) -> None:
        """YAML 파일에서 규칙 로드

        Args:
            file_path: YAML 파일 경로
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            raise ValueError(f"Invalid rule file format: {file_path}")

        # 파일에 여러 규칙이 있을 수 있음
        if 'rules' in data:
            # 배열 형식: rules: [{...}, {...}]
            for rule_data in data['rules']:
                rule = self._parse_rule_data(rule_data)
                self.register_rule(rule)
        else:
            # 단일 규칙 형식
            rule = self._parse_rule_data(data)
            self.register_rule(rule)

    def _parse_rule_data(self, data: Dict[str, Any]) -> RuleVersion:
        """딕셔너리에서 RuleVersion 생성

        Args:
            data: 규칙 데이터 딕셔너리

        Returns:
            생성된 RuleVersion

        Raises:
            ValueError: 필수 필드가 누락된 경우
        """
        required_fields = ['rule_id', 'version', 'effective_date', 'rule_type']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        # effective_date 파싱
        effective_date = data['effective_date']
        if isinstance(effective_date, str):
            effective_date = date.fromisoformat(effective_date)

        # rule_data 추출 (나머지 필드들)
        rule_data = data.get('data', {})

        return RuleVersion(
            rule_id=data['rule_id'],
            version=data['version'],
            effective_date=effective_date,
            rule_type=data['rule_type'],
            rule_data=rule_data,
            source=data.get('source', ''),
            description=data.get('description', ''),
            supersedes=data.get('supersedes')
        )

    def snapshot(self, as_of_date: date) -> Dict[str, RuleVersion]:
        """특정 날짜 기준 규칙 스냅샷 생성

        케이스 처리 시작 시 이 날짜 기준의 모든 규칙 버전을 고정합니다.

        Args:
            as_of_date: 기준 날짜

        Returns:
            rule_id -> RuleVersion 매핑
        """
        snapshot = {}
        for rule_id in self.rules.keys():
            rule = self.get_rule(rule_id, as_of_date)
            if rule:
                snapshot[rule_id] = rule
        return snapshot

    def __len__(self) -> int:
        """등록된 규칙 총 개수"""
        return sum(len(versions) for versions in self.rules.values())

    def __str__(self) -> str:
        return f"RuleRegistry({len(self)} rules, {len(self.rules)} rule IDs)"


# 싱글톤 인스턴스 (선택적)
_default_registry: Optional[RuleRegistry] = None


def get_default_registry() -> RuleRegistry:
    """기본 규칙 레지스트리 가져오기

    애플리케이션 전역에서 사용할 단일 레지스트리 인스턴스를 반환합니다.

    Returns:
        기본 RuleRegistry 인스턴스
    """
    global _default_registry
    if _default_registry is None:
        _default_registry = RuleRegistry()
    return _default_registry


def reset_default_registry() -> None:
    """기본 규칙 레지스트리 초기화 (주로 테스트용)"""
    global _default_registry
    _default_registry = None
