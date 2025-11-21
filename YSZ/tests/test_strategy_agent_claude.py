"""StrategyAgent Claude Integration 테스트

Claude LLM 통합 테스트
"""

import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch

from src.core import FactLedger
from src.agents import StrategyAgent, CaseCategory


class TestClaudeIntegration:
    """Claude 통합 테스트"""

    @pytest.mark.asyncio
    async def test_strategy_agent_without_llm(self):
        """LLM 없이도 정상 작동"""
        agent = StrategyAgent(enable_llm=False)

        ledger = FactLedger.create({
            "acquisition_date": date(2020, 1, 1),
            "acquisition_price": Decimal("500000000"),
            "disposal_date": date(2024, 6, 1),
            "disposal_price": Decimal("700000000"),
            "house_count": 1,
            "residence_period_years": 3
        })

        strategy = await agent.analyze(ledger)

        # 로직 결과는 정상
        assert strategy.category == CaseCategory.SINGLE_HOUSE_EXEMPT
        assert len(strategy.scenarios) > 0

        # LLM 설명은 없음
        assert strategy.llm_explanation is None
        assert strategy.llm_additional_advice is None

    @pytest.mark.asyncio
    async def test_strategy_agent_with_llm_but_no_api_key(self):
        """LLM 활성화했지만 API 키 없음"""
        # API 키 없이 초기화
        agent = StrategyAgent(enable_llm=True, claude_api_key=None)

        # enable_llm이 자동으로 False로 전환되어야 함
        assert agent.enable_llm is False or agent.claude is None

    @pytest.mark.asyncio
    @patch('src.agents.strategy_agent.Anthropic')
    async def test_strategy_agent_with_mocked_claude(self, mock_anthropic):
        """Mocked Claude로 테스트"""
        # Mock Claude 응답
        mock_message = Mock()
        mock_message.content = [Mock(text="이것은 테스트 설명입니다.")]

        mock_client = Mock()
        mock_client.messages.create = Mock(return_value=mock_message)
        mock_anthropic.return_value = mock_client

        # Agent 생성 (LLM 활성화)
        agent = StrategyAgent(enable_llm=True, claude_api_key="test-key")

        ledger = FactLedger.create({
            "acquisition_date": date(2020, 1, 1),
            "acquisition_price": Decimal("500000000"),
            "disposal_date": date(2024, 6, 1),
            "disposal_price": Decimal("700000000"),
            "house_count": 1,
            "residence_period_years": 3
        })

        strategy = await agent.analyze(ledger)

        # 로직 결과는 정상
        assert strategy.category == CaseCategory.SINGLE_HOUSE_EXEMPT

        # LLM 설명이 생성되었는지 확인
        assert strategy.llm_explanation is not None
        assert strategy.llm_additional_advice is not None
        assert "테스트 설명" in strategy.llm_explanation

        # Claude API 호출 확인
        assert mock_client.messages.create.call_count == 2  # explanation + advice

    @pytest.mark.asyncio
    async def test_logic_consistency_with_and_without_llm(self):
        """LLM 유무와 관계없이 로직 결과는 동일해야 함"""
        ledger = FactLedger.create({
            "acquisition_date": date(2020, 1, 1),
            "acquisition_price": Decimal("500000000"),
            "disposal_date": date(2024, 6, 1),
            "disposal_price": Decimal("700000000"),
            "house_count": 1,
            "residence_period_years": 3
        })

        # LLM 없이
        agent_no_llm = StrategyAgent(enable_llm=False)
        strategy_no_llm = await agent_no_llm.analyze(ledger)

        # LLM 있음 (mock)
        with patch('src.agents.strategy_agent.Anthropic') as mock_anthropic:
            mock_message = Mock()
            mock_message.content = [Mock(text="설명")]

            mock_client = Mock()
            mock_client.messages.create = Mock(return_value=mock_message)
            mock_anthropic.return_value = mock_client

            agent_with_llm = StrategyAgent(enable_llm=True, claude_api_key="test-key")
            strategy_with_llm = await agent_with_llm.analyze(ledger)

        # 핵심 로직 결과는 동일
        assert strategy_no_llm.category == strategy_with_llm.category
        assert len(strategy_no_llm.scenarios) == len(strategy_with_llm.scenarios)
        assert strategy_no_llm.recommended_scenario_id == strategy_with_llm.recommended_scenario_id

        # 세금 계산 동일
        assert strategy_no_llm.scenarios[0].expected_tax == strategy_with_llm.scenarios[0].expected_tax

        # LLM 설명만 차이
        assert strategy_no_llm.llm_explanation is None
        assert strategy_with_llm.llm_explanation is not None

    @pytest.mark.asyncio
    @patch('src.agents.strategy_agent.Anthropic')
    async def test_claude_error_handling(self, mock_anthropic):
        """Claude API 오류 처리"""
        # Claude API가 예외를 던지도록 설정
        mock_client = Mock()
        mock_client.messages.create = Mock(side_effect=Exception("API Error"))
        mock_anthropic.return_value = mock_client

        agent = StrategyAgent(enable_llm=True, claude_api_key="test-key")

        ledger = FactLedger.create({
            "acquisition_date": date(2020, 1, 1),
            "acquisition_price": Decimal("500000000"),
            "disposal_date": date(2024, 6, 1),
            "disposal_price": Decimal("700000000"),
            "house_count": 1,
            "residence_period_years": 3
        })

        # 오류가 발생해도 전체 분석은 성공해야 함
        strategy = await agent.analyze(ledger)

        # 로직 결과는 정상
        assert strategy.category == CaseCategory.SINGLE_HOUSE_EXEMPT
        assert len(strategy.scenarios) > 0

        # LLM 설명은 빈 문자열 (오류로 인해)
        assert strategy.llm_explanation == ""
        assert strategy.llm_additional_advice == ""


class TestClaudePrompts:
    """Claude 프롬프트 테스트"""

    @pytest.mark.asyncio
    @patch('src.agents.strategy_agent.Anthropic')
    async def test_explanation_prompt_content(self, mock_anthropic):
        """설명 프롬프트가 적절한 내용을 포함하는지"""
        # Mock 설정
        captured_prompts = []

        def capture_prompt(**kwargs):
            captured_prompts.append(kwargs['messages'][0]['content'])
            mock_message = Mock()
            mock_message.content = [Mock(text="설명")]
            return mock_message

        mock_client = Mock()
        mock_client.messages.create = Mock(side_effect=capture_prompt)
        mock_anthropic.return_value = mock_client

        agent = StrategyAgent(enable_llm=True, claude_api_key="test-key")

        ledger = FactLedger.create({
            "acquisition_date": date(2020, 1, 1),
            "acquisition_price": Decimal("500000000"),
            "disposal_date": date(2024, 6, 1),
            "disposal_price": Decimal("700000000"),
            "house_count": 1,
            "residence_period_years": 3
        })

        await agent.analyze(ledger)

        # 프롬프트 내용 확인
        explanation_prompt = captured_prompts[0]

        # 분석 결과가 포함되어야 함
        assert "케이스 분류" in explanation_prompt
        assert "시나리오" in explanation_prompt
        assert "예상 세금" in explanation_prompt

        # "계산을 다시 하지 말고" 같은 지시가 있어야 함
        assert "다시" in explanation_prompt.lower() or "결과" in explanation_prompt

    @pytest.mark.asyncio
    @patch('src.agents.strategy_agent.Anthropic')
    async def test_advice_prompt_content(self, mock_anthropic):
        """조언 프롬프트가 적절한 내용을 포함하는지"""
        captured_prompts = []

        def capture_prompt(**kwargs):
            captured_prompts.append(kwargs['messages'][0]['content'])
            mock_message = Mock()
            mock_message.content = [Mock(text="조언")]
            return mock_message

        mock_client = Mock()
        mock_client.messages.create = Mock(side_effect=capture_prompt)
        mock_anthropic.return_value = mock_client

        agent = StrategyAgent(enable_llm=True, claude_api_key="test-key")

        ledger = FactLedger.create({
            "acquisition_date": date(2020, 1, 1),
            "acquisition_price": Decimal("300000000"),
            "disposal_date": date(2024, 6, 1),
            "disposal_price": Decimal("1000000000"),  # 고액 차익
            "house_count": 1,
            "residence_period_years": 3
        })

        await agent.analyze(ledger)

        # 조언 프롬프트 (두 번째 호출)
        advice_prompt = captured_prompts[1]

        # 케이스 정보가 포함되어야 함
        assert "케이스" in advice_prompt or "분류" in advice_prompt

        # 전문가 관점 요청
        assert "세무사" in advice_prompt or "전문가" in advice_prompt or "조언" in advice_prompt


class TestClaudeModelUsage:
    """Claude 모델 사용 테스트"""

    @pytest.mark.asyncio
    @patch('src.agents.strategy_agent.Anthropic')
    async def test_uses_correct_claude_model(self, mock_anthropic):
        """올바른 Claude 모델을 사용하는지"""
        captured_calls = []

        def capture_call(**kwargs):
            captured_calls.append(kwargs)
            mock_message = Mock()
            mock_message.content = [Mock(text="응답")]
            return mock_message

        mock_client = Mock()
        mock_client.messages.create = Mock(side_effect=capture_call)
        mock_anthropic.return_value = mock_client

        agent = StrategyAgent(enable_llm=True, claude_api_key="test-key")

        ledger = FactLedger.create({
            "acquisition_date": date(2020, 1, 1),
            "acquisition_price": Decimal("500000000"),
            "disposal_date": date(2024, 6, 1),
            "disposal_price": Decimal("700000000"),
            "house_count": 1,
            "residence_period_years": 3
        })

        await agent.analyze(ledger)

        # 모델 확인
        for call in captured_calls:
            assert call['model'] == "claude-3-5-sonnet-20241022"
            assert call['max_tokens'] == 1024
            assert 'temperature' in call


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
