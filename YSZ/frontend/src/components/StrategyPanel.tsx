import React, { useState } from 'react';
import {
  Card,
  Button,
  Table,
  Alert,
  Tag,
  Descriptions,
  Spin,
  Space,
  Divider,
  Typography,
  Collapse
} from 'antd';
import {
  RocketOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  InfoCircleOutlined,
  DollarOutlined,
  CalendarOutlined,
  StarOutlined
} from '@ant-design/icons';

const { Title, Text, Paragraph } = Typography;
const { Panel } = Collapse;

interface StrategyPanelProps {
  facts: any; // 사실관계 정보
}

interface Scenario {
  scenario_id: string;
  scenario_name: string;
  disposal_date: string;
  expected_tax: number;
  net_benefit: number;
  is_recommended: boolean;
  pros: string[];
  cons: string[];
}

interface Risk {
  level: string;
  title: string;
  description: string;
  mitigation?: string;
}

interface StrategyResult {
  category: string;
  category_description: string;
  classification_reasoning: string;
  scenarios: Scenario[];
  recommended_scenario_id: string;
  risks: Risk[];
  llm_explanation?: string;
  analyzed_at: string;
}

const StrategyPanel: React.FC<StrategyPanelProps> = ({ facts }) => {
  const [loading, setLoading] = useState(false);
  const [strategy, setStrategy] = useState<StrategyResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const analyzeStrategy = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/v1/strategy/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...facts,
          enable_explanation: true, // LLM 설명 활성화
        }),
      });

      if (!response.ok) {
        throw new Error('전략 분석에 실패했습니다.');
      }

      const data = await response.json();
      setStrategy(data);
    } catch (err: any) {
      setError(err.message || '오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  // 리스크 레벨별 색상
  const getRiskColor = (level: string) => {
    switch (level) {
      case 'high':
        return 'red';
      case 'medium':
        return 'orange';
      case 'low':
        return 'yellow';
      default:
        return 'green';
    }
  };

  // 리스크 레벨별 아이콘
  const getRiskIcon = (level: string) => {
    switch (level) {
      case 'high':
      case 'medium':
        return <WarningOutlined />;
      case 'low':
        return <InfoCircleOutlined />;
      default:
        return <CheckCircleOutlined />;
    }
  };

  // 시나리오 테이블 컬럼
  const scenarioColumns = [
    {
      title: '시나리오',
      dataIndex: 'scenario_name',
      key: 'scenario_name',
      render: (text: string, record: Scenario) => (
        <Space>
          {record.is_recommended && (
            <StarOutlined style={{ color: '#faad14' }} />
          )}
          <Text strong={record.is_recommended}>{text}</Text>
        </Space>
      ),
    },
    {
      title: '양도일',
      dataIndex: 'disposal_date',
      key: 'disposal_date',
      render: (date: string) => (
        <Space>
          <CalendarOutlined />
          {date}
        </Space>
      ),
    },
    {
      title: '예상 세액',
      dataIndex: 'expected_tax',
      key: 'expected_tax',
      render: (tax: number) => (
        <Text strong style={{ color: tax === 0 ? '#52c41a' : '#000' }}>
          {tax.toLocaleString()}원
        </Text>
      ),
    },
    {
      title: '순 편익',
      dataIndex: 'net_benefit',
      key: 'net_benefit',
      render: (benefit: number) => (
        <Space>
          <DollarOutlined />
          {benefit.toLocaleString()}원
        </Space>
      ),
    },
    {
      title: '장점',
      dataIndex: 'pros',
      key: 'pros',
      render: (pros: string[]) => (
        <Space direction="vertical" size="small">
          {pros.map((pro, idx) => (
            <Tag key={idx} color="green" icon={<CheckCircleOutlined />}>
              {pro}
            </Tag>
          ))}
        </Space>
      ),
    },
    {
      title: '단점',
      dataIndex: 'cons',
      key: 'cons',
      render: (cons: string[]) => (
        <Space direction="vertical" size="small">
          {cons.map((con, idx) => (
            <Tag key={idx} color="red" icon={<WarningOutlined />}>
              {con}
            </Tag>
          ))}
        </Space>
      ),
    },
  ];

  return (
    <Card
      title={
        <Space>
          <RocketOutlined />
          <span>전략 분석</span>
        </Space>
      }
      extra={
        <Button
          type="primary"
          icon={<RocketOutlined />}
          onClick={analyzeStrategy}
          loading={loading}
          disabled={!facts}
        >
          분석 시작
        </Button>
      }
    >
      {!strategy && !loading && !error && (
        <Alert
          message="전략 분석 대기"
          description="사실관계 정보를 입력한 후 '분석 시작' 버튼을 클릭하세요."
          type="info"
          showIcon
        />
      )}

      {loading && (
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <Spin size="large" tip="AI가 전략을 분석하고 있습니다..." />
        </div>
      )}

      {error && (
        <Alert
          message="오류 발생"
          description={error}
          type="error"
          showIcon
          closable
        />
      )}

      {strategy && !loading && (
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          {/* 케이스 분류 */}
          <Card size="small" title="케이스 분류">
            <Space direction="vertical" style={{ width: '100%' }}>
              <div>
                <Tag color="blue" style={{ fontSize: '16px', padding: '8px 16px' }}>
                  {strategy.category}
                </Tag>
              </div>
              <Text>{strategy.category_description}</Text>
              <Collapse ghost>
                <Panel header="분류 근거 보기" key="1">
                  <Text type="secondary" style={{ whiteSpace: 'pre-line' }}>
                    {strategy.classification_reasoning}
                  </Text>
                </Panel>
              </Collapse>
            </Space>
          </Card>

          {/* LLM 설명 */}
          {strategy.llm_explanation && (
            <Alert
              message="AI 전문가 의견"
              description={
                <Paragraph style={{ marginBottom: 0, whiteSpace: 'pre-line' }}>
                  {strategy.llm_explanation}
                </Paragraph>
              }
              type="info"
              showIcon
              icon={<InfoCircleOutlined />}
            />
          )}

          {/* 시나리오 비교 */}
          <Card size="small" title="시나리오 비교">
            <Table
              dataSource={strategy.scenarios}
              columns={scenarioColumns}
              rowKey="scenario_id"
              pagination={false}
              rowClassName={(record) =>
                record.is_recommended ? 'recommended-row' : ''
              }
            />
          </Card>

          {/* 추천 */}
          <Alert
            message="추천 시나리오"
            description={
              <Space>
                <StarOutlined style={{ color: '#faad14' }} />
                <Text strong>
                  {strategy.scenarios.find(
                    (s) => s.scenario_id === strategy.recommended_scenario_id
                  )?.scenario_name || strategy.recommended_scenario_id}
                </Text>
              </Space>
            }
            type="success"
            showIcon
          />

          {/* 리스크 플래그 */}
          {strategy.risks.length > 0 && (
            <Card size="small" title="리스크 분석">
              <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                {strategy.risks.map((risk, idx) => (
                  <Alert
                    key={idx}
                    message={
                      <Space>
                        {getRiskIcon(risk.level)}
                        <Text strong>{risk.title}</Text>
                      </Space>
                    }
                    description={
                      <Space direction="vertical" style={{ width: '100%' }}>
                        <Text>{risk.description}</Text>
                        {risk.mitigation && (
                          <Text type="secondary">
                            <strong>대응방안:</strong> {risk.mitigation}
                          </Text>
                        )}
                      </Space>
                    }
                    type={
                      risk.level === 'high'
                        ? 'error'
                        : risk.level === 'medium'
                        ? 'warning'
                        : 'info'
                    }
                    showIcon
                  />
                ))}
              </Space>
            </Card>
          )}

          {/* 메타데이터 */}
          <Descriptions size="small" column={2} bordered>
            <Descriptions.Item label="분석 일시">
              {new Date(strategy.analyzed_at).toLocaleString('ko-KR')}
            </Descriptions.Item>
            <Descriptions.Item label="시나리오 수">
              {strategy.scenarios.length}개
            </Descriptions.Item>
          </Descriptions>

          {/* 법적 고지 */}
          <Alert
            message="법적 고지"
            description="본 전략 분석은 일반적인 정보 제공 목적이며, 실제 신고 시에는 반드시 세무사와 상담하시기 바랍니다."
            type="warning"
            showIcon
          />
        </Space>
      )}

      <style>{`
        .recommended-row {
          background-color: #fffbe6;
        }
      `}</style>
    </Card>
  );
};

export default StrategyPanel;
