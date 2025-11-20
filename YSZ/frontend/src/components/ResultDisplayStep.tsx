/**
 * 계산 결과 표시 단계 컴포넌트
 */

import React from 'react';
import { Card, Descriptions, Table, Alert, Button, Divider, Tag } from 'antd';
import {
  DollarCircleOutlined,
  FileTextOutlined,
  ReloadOutlined,
  DownloadOutlined
} from '@ant-design/icons';

interface ResultDisplayStepProps {
  result: any;
  factLedger: any[];
  onReset: () => void;
}

const ResultDisplayStep: React.FC<ResultDisplayStepProps> = ({
  result,
  factLedger,
  onReset
}) => {
  const formatCurrency = (value: number) => {
    return `${value.toLocaleString()}원`;
  };

  const formatPercent = (value: number) => {
    return `${(value * 100).toFixed(1)}%`;
  };

  const breakdownColumns = [
    {
      title: '항목',
      dataIndex: 'label',
      key: 'label',
      render: (text: string) => <strong>{text}</strong>
    },
    {
      title: '금액',
      dataIndex: 'amount',
      key: 'amount',
      render: (amount: number) => (
        <span style={{ fontSize: '16px' }}>{formatCurrency(amount)}</span>
      ),
      align: 'right' as const
    },
    {
      title: '설명',
      dataIndex: 'description',
      key: 'description'
    }
  ];

  return (
    <div>
      {/* 1. 계산의 대전제 (사실관계) */}
      <Card
        title={<><FileTextOutlined /> 계산의 대전제 (사실관계)</>}
        style={{ marginBottom: 24 }}
      >
        <Alert
          message="아래 사실이 실제와 다를 경우 세액은 달라질 수 있습니다."
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
        />

        <Descriptions bordered column={2}>
          {factLedger.map((fact: any) => (
            <Descriptions.Item
              key={fact.field_name}
              label={fact.field_name}
            >
              {String(fact.value)}
              {fact.is_confirmed && (
                <Tag color="green" style={{ marginLeft: 8 }}>확인됨</Tag>
              )}
            </Descriptions.Item>
          ))}
        </Descriptions>
      </Card>

      {/* 2. 계산 결과 */}
      <Card
        title={<><DollarCircleOutlined /> 양도소득세 계산 결과</>}
        style={{ marginBottom: 24 }}
      >
        <div style={{
          textAlign: 'center',
          padding: '40px 0',
          background: '#f6ffed',
          borderRadius: '8px',
          marginBottom: 24
        }}>
          <div style={{ fontSize: '16px', color: '#666', marginBottom: 8 }}>
            예상 납부세액
          </div>
          <div style={{
            fontSize: '48px',
            fontWeight: 'bold',
            color: '#52c41a'
          }}>
            {formatCurrency(result.total_tax)}
          </div>
          <div style={{ marginTop: 16 }}>
            <Tag color="blue">
              적용 세율: {formatPercent(result.applied_tax_rate || 0)}
            </Tag>
          </div>
        </div>

        <Descriptions bordered column={2}>
          <Descriptions.Item label="양도가액">
            {formatCurrency(result.disposal_price)}
          </Descriptions.Item>
          <Descriptions.Item label="취득가액">
            {formatCurrency(result.acquisition_price)}
          </Descriptions.Item>
          <Descriptions.Item label="양도차익">
            {formatCurrency(result.capital_gain)}
          </Descriptions.Item>
          <Descriptions.Item label="필요경비">
            {formatCurrency(result.necessary_expenses)}
          </Descriptions.Item>
          <Descriptions.Item label="장기보유특별공제">
            {formatCurrency(result.long_term_deduction)}
          </Descriptions.Item>
          <Descriptions.Item label="기본공제">
            {formatCurrency(result.basic_deduction)}
          </Descriptions.Item>
          <Descriptions.Item label="과세표준" span={2}>
            <strong style={{ fontSize: '18px' }}>
              {formatCurrency(result.taxable_income)}
            </strong>
          </Descriptions.Item>
          <Descriptions.Item label="산출세액">
            {formatCurrency(result.calculated_tax)}
          </Descriptions.Item>
          <Descriptions.Item label="지방소득세">
            {formatCurrency(result.local_tax)}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* 3. 계산 과정 상세 */}
      <Card
        title="🔍 계산 과정 상세"
        style={{ marginBottom: 24 }}
      >
        <Table
          dataSource={result.breakdown}
          columns={breakdownColumns}
          pagination={false}
          rowKey="label"
        />
      </Card>

      {/* 4. 적용된 법령 */}
      <Card
        title="📖 적용된 세법 규칙"
        style={{ marginBottom: 24 }}
      >
        <div>
          {result.applied_rules && result.applied_rules.length > 0 ? (
            result.applied_rules.map((rule: string, index: number) => (
              <Tag key={index} color="geekblue" style={{ marginBottom: 8 }}>
                {rule}
              </Tag>
            ))
          ) : (
            <p>적용된 규칙 정보가 없습니다.</p>
          )}
        </div>
      </Card>

      {/* 5. 액션 버튼 */}
      <Card>
        <div style={{ textAlign: 'center' }}>
          <Button
            size="large"
            icon={<DownloadOutlined />}
            style={{ marginRight: 16 }}
          >
            결과 다운로드 (PDF)
          </Button>

          <Button
            type="primary"
            size="large"
            icon={<ReloadOutlined />}
            onClick={onReset}
          >
            새로운 계산 시작
          </Button>
        </div>
      </Card>

      <Divider />

      <Alert
        message="법적 고지"
        description="본 계산 결과는 입력하신 사실관계를 바탕으로 한 추정치입니다. 실제 납부세액은 세무사 또는 국세청에 문의하시기 바랍니다."
        type="info"
        showIcon
      />
    </div>
  );
};

export default ResultDisplayStep;
