/**
 * YSZ 양도소득세 계산기 메인 애플리케이션
 */

import React, { useState } from 'react';
import { Layout, Steps, Typography, Alert } from 'antd';
import DataInputStep from './components/DataInputStep';
import FactConfirmationStep from './components/FactConfirmationStep';
import CalculationStep from './components/CalculationStep';
import ResultDisplayStep from './components/ResultDisplayStep';

const { Header, Content, Footer } = Layout;
const { Title } = Typography;

interface AppState {
  currentStep: number;
  transactionId: number | null;
  factLedger: any | null;
  calculationResult: any | null;
}

function App() {
  const [state, setState] = useState<AppState>({
    currentStep: 0,
    transactionId: null,
    factLedger: null,
    calculationResult: null
  });

  const handleDataInput = async (data: any) => {
    // API 호출하여 사실관계 수집
    try {
      const response = await fetch('/api/v1/facts/collect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_data: data,
          created_by: 'web_user'
        })
      });

      const result = await response.json();

      setState(prev => ({
        ...prev,
        transactionId: result.transaction_id,
        factLedger: result.facts,
        currentStep: 1
      }));
    } catch (error) {
      console.error('Failed to collect facts:', error);
    }
  };

  const handleFactConfirmation = async () => {
    setState(prev => ({ ...prev, currentStep: 2 }));
  };

  const handleCalculationComplete = (result: any) => {
    setState(prev => ({
      ...prev,
      calculationResult: result,
      currentStep: 3
    }));
  };

  const handleReset = () => {
    setState({
      currentStep: 0,
      transactionId: null,
      factLedger: null,
      calculationResult: null
    });
  };

  const steps = [
    { title: '정보 입력', description: '거래 정보 입력' },
    { title: '사실관계 확인', description: '입력 내용 검토' },
    { title: '계산', description: '세금 계산 진행' },
    { title: '결과', description: '계산 결과 확인' }
  ];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ background: '#001529', padding: '0 50px' }}>
        <Title level={3} style={{ color: 'white', margin: '16px 0' }}>
          YSZ 양도소득세 계산기
        </Title>
      </Header>

      <Content style={{ padding: '50px', maxWidth: '1200px', margin: '0 auto', width: '100%' }}>
        <Alert
          message="법적 고지"
          description="본 시스템의 계산 결과는 참고용이며, 실제 세액은 세무사 또는 국세청에 문의하시기 바랍니다."
          type="warning"
          showIcon
          closable
          style={{ marginBottom: 24 }}
        />

        <Steps
          current={state.currentStep}
          items={steps}
          style={{ marginBottom: 40 }}
        />

        {state.currentStep === 0 && (
          <DataInputStep onComplete={handleDataInput} />
        )}

        {state.currentStep === 1 && state.transactionId && (
          <FactConfirmationStep
            transactionId={state.transactionId}
            facts={state.factLedger}
            onConfirm={handleFactConfirmation}
          />
        )}

        {state.currentStep === 2 && state.transactionId && (
          <CalculationStep
            transactionId={state.transactionId}
            onComplete={handleCalculationComplete}
          />
        )}

        {state.currentStep === 3 && state.calculationResult && (
          <ResultDisplayStep
            result={state.calculationResult}
            factLedger={state.factLedger}
            onReset={handleReset}
          />
        )}
      </Content>

      <Footer style={{ textAlign: 'center', background: '#f0f2f5' }}>
        YSZ 양도소득세 계산기 ©2025 |
        사실관계 기반 정확한 세금 계산
      </Footer>
    </Layout>
  );
}

export default App;
