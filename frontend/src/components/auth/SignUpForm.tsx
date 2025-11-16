import React from 'react';
import { Form, Input, Button, Radio } from 'antd';
import { useNavigate } from 'react-router-dom';

import type { GenderType } from '@/api/user';
import { useCreateUser } from '@/hooks/useUser';
import RouterPaths from '@/routes/Router';

interface SignUpFormValues {
  nickname: string;
  username: string;
  password: string;
  password_confirm: string;
  email: string;
  gender: GenderType;
}

const SignUpForm: React.FC = () => {
  const navigate = useNavigate();
  const createUser = useCreateUser();

  const [form] = Form.useForm();

  // 폼 제출 처리
  const handleSubmit = async (values: SignUpFormValues) => {
    try {
      await createUser.mutateAsync(values);
      navigate(RouterPaths.Login);
    } catch (error) {
      // 에러는 useCreateUser의 onError에서 처리됨
      console.error('회원가입 처리 중 에러:', error);
    }
  };

  // 닉네임 유효성 검사
  const validateNickname = async (_: any, value: string) => {
    if (!value) {
      return Promise.resolve();
    }

    // 1. 길이 체크 (2~14자)
    if (value.length < 2 || value.length > 14) {
      return Promise.reject(new Error('닉네임은 2~14자 사이로 입력하세요'));
    }

    // 2. 허용된 문자만 사용 (영문 대소문자, 한글, 숫자)
    const allowedPattern = /^[a-zA-Z가-힣0-9]+$/;
    if (!allowedPattern.test(value)) {
      return Promise.reject(new Error('영문, 한글, 숫자만 사용 가능합니다'));
    }

    // 3. 공백 체크
    if (value.includes(' ')) {
      return Promise.reject(new Error('공백은 사용할 수 없습니다'));
    }

    // 4. 금지 단어 체크
    const forbiddenWords = [
      '운영자',
      '관리자',
      'admin',
      'administrator',
      '어드민',
    ];
    const lowerValue = value.toLowerCase();
    for (const word of forbiddenWords) {
      if (lowerValue.includes(word.toLowerCase())) {
        return Promise.reject(
          new Error('사용할 수 없는 단어가 포함되어 있습니다')
        );
      }
    }

    return Promise.resolve();
  };

  // 비밀번호 확인 validation
  const validateConfirmPassword = ({ getFieldValue }: any) => ({
    validator(_: any, value: string) {
      if (!value || getFieldValue('password') === value) {
        return Promise.resolve();
      }
      return Promise.reject(new Error('비밀번호가 일치하지 않습니다.'));
    },
  });
  return (
    <Form form={form} layout="vertical" onFinish={handleSubmit}>
      <Form.Item
        label="닉네임"
        name="nickname"
        rules={[
          { required: true, message: '닉네임을 입력하세요' },
          { validator: validateNickname },
        ]}
        extra={
          <div className="text-xs text-gray-500 mt-1">
            <div>• 2~14자 (영문, 한글, 숫자만 가능)</div>
            <div>• 특수문자, 공백 사용 불가</div>
          </div>
        }
      >
        <Input placeholder="닉네임을 입력하세요 (2~14자)" maxLength={14} />
      </Form.Item>

      <Form.Item
        label="이름"
        name="username"
        rules={[
          { required: true, message: '이름을 입력하세요' },
          { min: 2, max: 50, message: '이름은 2-50자 사이로 입력하세요' },
        ]}
      >
        <Input placeholder="이름을 입력하세요" />
      </Form.Item>

      <Form.Item
        label="비밀번호"
        name="password"
        rules={[
          { required: true, message: '비밀번호를 입력하세요' },
          { min: 8, max: 16, message: '비밀번호는 8-16자 사이로 입력하세요' },
          {
            pattern:
              /^(?=.*[a-zA-Z])(?=.*[0-9])[a-zA-Z0-9!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]*$/,
            message: '영문, 숫자를 포함하여 8-16자로 입력하세요',
          },
        ]}
        extra={
          <div className="text-xs text-gray-500 mt-1">
            <div>
              • 영문 대소문자, 숫자, 특수문자 중 2가지 이상 조합 (8~16자)
            </div>
            <div>• 4자리 이상 반복되는 문자와 숫자는 사용 불가</div>
            <div>
              • 사용 가능 특수문자:
              !@#$%^&*()_+-=[]&#123;&#125;;':&quot;\|,.&lt;&gt;/?
            </div>
          </div>
        }
      >
        <Input.Password placeholder="비밀번호를 입력하세요" />
      </Form.Item>

      <Form.Item
        label="비밀번호 확인"
        name="password_confirm"
        dependencies={['password']}
        rules={[
          { required: true, message: '비밀번호 확인을 입력하세요' },
          validateConfirmPassword,
        ]}
      >
        <Input.Password placeholder="비밀번호를 다시 입력하세요" />
      </Form.Item>

      <Form.Item
        label="이메일"
        name="email"
        rules={[
          { required: true, message: '이메일을 입력하세요' },
          { type: 'email', message: '올바른 이메일 형식을 입력하세요' },
        ]}
      >
        <Input type="email" placeholder="이메일을 입력하세요" />
      </Form.Item>

      <Form.Item
        label="성별"
        name="gender"
        rules={[{ message: '성별을 선택하세요' }]}
        initialValue="여성"
      >
        <Radio.Group
          block
          options={[
            { label: '여성', value: '여성' },
            { label: '남성', value: '남성' },
          ]}
          optionType="button"
        />
      </Form.Item>

      <Form.Item className="mb-0">
        <Button
          type="primary"
          htmlType="submit"
          block
          size="large"
          className="h-12"
        >
          회원가입
        </Button>
      </Form.Item>
    </Form>
  );
};

export default SignUpForm;
