/**
 * 계산 진행 단계 컴포넌트
 */

import React, { useEffect, useState } from 'react';
import { Card, Progress, Alert, Spin } from 'antd';
import { LoadingOutlined, CheckCircleOutlined } from '@ant-design/icons';

interface CalculationStepProps {
  transactionId: number;
  onComplete: (result: any) => void;
}

const CalculationStep: React.FC<CalculationStepProps> = ({
  transactionId,
  onComplete
}) => {
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState('계산 준비 중...');

  useEffect(() => {
    performCalculation();
  }, [transactionId]);

  const performCalculation = async () => {
    try {
      // 단계별 진행 표시
      setProgress(10);
      setStatus('사실관계 검증 중...');
      await new Promise(resolve => setTimeout(resolve, 500));

      setProgress(30);
      setStatus('양도차익 계산 중...');
      await new Promise(resolve => setTimeout(resolve, 500));

      setProgress(50);
      setStatus('공제액 계산 중...');
      await new Promise(resolve => setTimeout(resolve, 500));

      setProgress(70);
      setStatus('과세표준 산출 중...');
      await new Promise(resolve => setTimeout(resolve, 500));

      setProgress(90);
      setStatus('세율 적용 및 세액 계산 중...');

      // 실제 계산 API 호출
      const response = await fetch(`/api/v1/calculate/${transactionId}`, {
        method: 'POST'
      });

      const result = await response.json();

      setProgress(100);
      setStatus('계산 완료!');

      // 결과 전달
      setTimeout(() => {
        onComplete(result);
      }, 500);

    } catch (error) {
      console.error('Calculation failed:', error);
      setStatus('계산 중 오류가 발생했습니다.');
    }
  };

  return (
    <Card>
      <div style={{ textAlign: 'center', padding: '40px 0' }}>
        <Spin
          indicator={<LoadingOutlined style={{ fontSize: 48 }} spin />}
          spinning={progress < 100}
        />

        <h2 style={{ marginTop: 24 }}>양도소득세 계산 중</h2>

        <Progress
          percent={progress}
          status={progress < 100 ? 'active' : 'success'}
          style={{ marginTop: 24, marginBottom: 24 }}
        />

        <Alert
          message={status}
          type={progress < 100 ? 'info' : 'success'}
          icon={progress < 100 ? <LoadingOutlined /> : <CheckCircleOutlined />}
          showIcon
        />

        {progress === 100 && (
          <p style={{ marginTop: 16, color: '#52c41a' }}>
            잠시 후 결과 화면으로 이동합니다...
          </p>
        )}
      </div>
    </Card>
  );
};

export default CalculationStep;
