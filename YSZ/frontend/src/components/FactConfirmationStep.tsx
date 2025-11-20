/**
 * 사실관계 확인 단계 컴포넌트
 */

import React, { useState, useEffect } from 'react';
import { Card, Table, Button, Alert, Checkbox, Tag, Descriptions, Timeline } from 'antd';
import {
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  WarningOutlined
} from '@ant-design/icons';

interface FactConfirmationStepProps {
  transactionId: number;
  facts: any[];
  onConfirm: () => void;
}

const FactConfirmationStep: React.FC<FactConfirmationStepProps> = ({
  transactionId,
  facts,
  onConfirm
}) => {
  const [confirmations, setConfirmations] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(false);

  // 초기화: 모든 사실을 미확인 상태로
  useEffect(() => {
    const initial: Record<string, boolean> = {};
    facts.forEach(fact => {
      initial[fact.field_name] = false;
    });
    setConfirmations(initial);
  }, [facts]);

  const allConfirmed = Object.values(confirmations).every(v => v);

  const handleConfirmAll = async () => {
    setLoading(true);

    try {
      // 모든 필드 확인 API 호출
      const fieldNames = facts.map(f => f.field_name);

      await fetch(`/api/v1/facts/${transactionId}/confirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          field_names: fieldNames,
          confirmed_by: 'web_user'
        })
      });

      onConfirm();
    } catch (error) {
      console.error('Failed to confirm facts:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatValue = (value: any, type: string) => {
    if (type === 'numeric') {
      return `${Number(value).toLocaleString()}원`;
    } else if (type === 'date') {
      return new Date(value).toLocaleDateString('ko-KR');
    } else if (type === 'boolean') {
      return value ? '예' : '아니오';
    }
    return value;
  };

  const getFieldLabel = (fieldName: string): string => {
    const labels: Record<string, string> = {
      acquisition_date: '취득일',
      acquisition_price: '취득가액',
      disposal_date: '양도일',
      disposal_price: '양도가액',
      asset_type: '자산 유형',
      necessary_expenses: '필요경비',
      holding_period_years: '보유기간',
      is_primary_residence: '1세대 1주택 여부',
      number_of_houses: '주택 수',
      is_adjusted_area: '조정대상지역 여부'
    };
    return labels[fieldName] || fieldName;
  };

  const columns = [
    {
      title: '항목',
      dataIndex: 'field_name',
      key: 'field_name',
      render: (text: string) => <strong>{getFieldLabel(text)}</strong>
    },
    {
      title: '값',
      dataIndex: 'value',
      key: 'value',
      render: (value: any, record: any) => formatValue(value, record.value_type)
    },
    {
      title: '출처',
      dataIndex: 'source',
      key: 'source',
      render: (source: string) => {
        let color = 'blue';
        if (source === 'user_confirmed') color = 'green';
        else if (source === 'user_input') color = 'geekblue';
        return <Tag color={color}>{source}</Tag>;
      }
    },
    {
      title: '신뢰도',
      dataIndex: 'confidence',
      key: 'confidence',
      render: (confidence: number) => `${(confidence * 100).toFixed(0)}%`
    },
    {
      title: '확인',
      key: 'confirm',
      render: (_: any, record: any) => (
        <Checkbox
          checked={confirmations[record.field_name] || false}
          onChange={(e) => {
            setConfirmations(prev => ({
              ...prev,
              [record.field_name]: e.target.checked
            }));
          }}
        >
          확인함
        </Checkbox>
      )
    }
  ];

  return (
    <div>
      <Alert
        message={<><WarningOutlined /> 계산 전 사실관계 확인</>}
        description="아래 정보가 실제와 다를 경우 세액이 달라질 수 있습니다. 모든 항목을 신중히 확인해주세요."
        type="warning"
        showIcon
        style={{ marginBottom: 24 }}
      />

      <Card title="🔍 거래 타임라인" style={{ marginBottom: 24 }}>
        <Timeline
          items={[
            {
              color: 'green',
              children: (
                <>
                  <strong>취득</strong>
                  <br />
                  {facts.find(f => f.field_name === 'acquisition_date')?.value}
                  <br />
                  {formatValue(
                    facts.find(f => f.field_name === 'acquisition_price')?.value,
                    'numeric'
                  )}
                </>
              )
            },
            {
              color: 'blue',
              children: (
                <>
                  <strong>보유 기간</strong>
                  <br />
                  {facts.find(f => f.field_name === 'holding_period_years')?.value || '계산됨'}년
                </>
              )
            },
            {
              color: 'red',
              children: (
                <>
                  <strong>양도</strong>
                  <br />
                  {facts.find(f => f.field_name === 'disposal_date')?.value}
                  <br />
                  {formatValue(
                    facts.find(f => f.field_name === 'disposal_price')?.value,
                    'numeric'
                  )}
                </>
              )
            }
          ]}
        />
      </Card>

      <Card title="📋 핵심 사실관계" style={{ marginBottom: 24 }}>
        <Table
          dataSource={facts}
          columns={columns}
          rowKey="field_name"
          pagination={false}
        />
      </Card>

      <Card>
        <div style={{ textAlign: 'center' }}>
          <p>
            {allConfirmed ? (
              <><CheckCircleOutlined style={{ color: 'green' }} /> 모든 항목이 확인되었습니다.</>
            ) : (
              <><ExclamationCircleOutlined style={{ color: 'orange' }} /> {Object.values(confirmations).filter(v => v).length} / {facts.length} 항목 확인됨</>
            )}
          </p>

          <Button
            type="primary"
            size="large"
            onClick={handleConfirmAll}
            disabled={!allConfirmed}
            loading={loading}
            icon={<CheckCircleOutlined />}
          >
            위 사실관계로 계산 진행
          </Button>
        </div>
      </Card>
    </div>
  );
};

export default FactConfirmationStep;
