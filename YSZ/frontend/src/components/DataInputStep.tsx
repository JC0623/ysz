/**
 * 데이터 입력 단계 컴포넌트
 */

import React from 'react';
import { Form, Input, DatePicker, InputNumber, Select, Button, Card, Row, Col } from 'antd';
import { HomeOutlined, DollarOutlined, CalendarOutlined } from '@ant-design/icons';

interface DataInputStepProps {
  onComplete: (data: any) => void;
}

const DataInputStep: React.FC<DataInputStepProps> = ({ onComplete }) => {
  const [form] = Form.useForm();

  const handleSubmit = (values: any) => {
    // 날짜 포맷 변환
    const formattedData = {
      ...values,
      acquisition_date: values.acquisition_date.format('YYYY-MM-DD'),
      disposal_date: values.disposal_date.format('YYYY-MM-DD')
    };

    onComplete(formattedData);
  };

  return (
    <Card title="거래 정보 입력" bordered={false}>
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        initialValues={{
          asset_type: 'residential',
          is_primary_residence: false,
          is_adjusted_area: false,
          number_of_houses: 1
        }}
      >
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              name="acquisition_date"
              label="취득일"
              rules={[{ required: true, message: '취득일을 입력해주세요' }]}
            >
              <DatePicker
                style={{ width: '100%' }}
                placeholder="취득 날짜 선택"
                prefix={<CalendarOutlined />}
              />
            </Form.Item>
          </Col>

          <Col span={12}>
            <Form.Item
              name="acquisition_price"
              label="취득가액 (원)"
              rules={[{ required: true, message: '취득가액을 입력해주세요' }]}
            >
              <InputNumber
                style={{ width: '100%' }}
                min={0}
                step={1000000}
                formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                parser={value => value!.replace(/\$\s?|(,*)/g, '')}
                prefix={<DollarOutlined />}
              />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              name="disposal_date"
              label="양도일"
              rules={[{ required: true, message: '양도일을 입력해주세요' }]}
            >
              <DatePicker
                style={{ width: '100%' }}
                placeholder="양도 날짜 선택"
                prefix={<CalendarOutlined />}
              />
            </Form.Item>
          </Col>

          <Col span={12}>
            <Form.Item
              name="disposal_price"
              label="양도가액 (원)"
              rules={[{ required: true, message: '양도가액을 입력해주세요' }]}
            >
              <InputNumber
                style={{ width: '100%' }}
                min={0}
                step={1000000}
                formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                parser={value => value!.replace(/\$\s?|(,*)/g, '')}
                prefix={<DollarOutlined />}
              />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              name="asset_type"
              label="자산 유형"
              rules={[{ required: true }]}
            >
              <Select>
                <Select.Option value="residential">주거용 부동산</Select.Option>
                <Select.Option value="commercial">상업용 부동산</Select.Option>
                <Select.Option value="land">토지</Select.Option>
              </Select>
            </Form.Item>
          </Col>

          <Col span={12}>
            <Form.Item
              name="necessary_expenses"
              label="필요경비 (원)"
              tooltip="취득세, 중개수수료 등"
            >
              <InputNumber
                style={{ width: '100%' }}
                min={0}
                step={100000}
                formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                parser={value => value!.replace(/\$\s?|(,*)/g, '')}
              />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col span={8}>
            <Form.Item
              name="number_of_houses"
              label="주택 수"
            >
              <InputNumber style={{ width: '100%' }} min={1} />
            </Form.Item>
          </Col>

          <Col span={8}>
            <Form.Item
              name="is_primary_residence"
              label="1세대 1주택 여부"
            >
              <Select>
                <Select.Option value={true}>예</Select.Option>
                <Select.Option value={false}>아니오</Select.Option>
              </Select>
            </Form.Item>
          </Col>

          <Col span={8}>
            <Form.Item
              name="is_adjusted_area"
              label="조정대상지역 여부"
            >
              <Select>
                <Select.Option value={true}>예</Select.Option>
                <Select.Option value={false}>아니오</Select.Option>
              </Select>
            </Form.Item>
          </Col>
        </Row>

        <Form.Item>
          <Button
            type="primary"
            htmlType="submit"
            size="large"
            block
            icon={<HomeOutlined />}
          >
            다음 단계: 사실관계 확인
          </Button>
        </Form.Item>
      </Form>
    </Card>
  );
};

export default DataInputStep;
