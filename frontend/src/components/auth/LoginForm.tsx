import { Form, Input, Button, Flex } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useLogin } from '@/hooks/useUser';

interface LoginFormValues {
  username: string;
  password: string;
}

const LoginForm: React.FC = () => {
  const navigate = useNavigate();
  const [form] = Form.useForm<LoginFormValues>();

  const login = useLogin();

  const handleSubmit = async (values: LoginFormValues) => {
    await login.mutateAsync(values);
    navigate('/'); // 메인 페이지로 이동
  };

  // 회원가입 페이지로 이동
  const handleSignupClick = () => {
    navigate('/signup');
  };
  return (
    <Form form={form} layout="vertical" onFinish={handleSubmit}>
      <Form.Item
        label="닉네임"
        name="username"
        rules={[
          { required: true, message: '닉네임을 입력하세요' },
          { min: 2, max: 14, message: '닉네임은 2-14자 사이로 입력하세요' },
        ]}
      >
        <Input
          prefix={<UserOutlined style={{ color: '#bfbfbf' }} />}
          placeholder="닉네임"
        />
      </Form.Item>

      <Form.Item
        label="비밀번호"
        name="password"
        rules={[{ required: true, message: '비밀번호를 입력하세요' }]}
      >
        <Input.Password
          prefix={<LockOutlined style={{ color: '#bfbfbf' }} />}
          placeholder="비밀번호"
        />
      </Form.Item>

      {/* 버튼 그룹 */}
      <Form.Item className="mt-6 mb-0">
        {/* LOGIN 버튼 */}
        <Button
          type="primary"
          htmlType="submit"
          block
          className="h-12 rounded-lg text-base font-semibold mb-4 bg-gray-800 hover:bg-gray-700 border-gray-800"
        >
          LOGIN
        </Button>

        {/* 회원가입 버튼 */}
        <Flex justify="center" align="center" gap="small">
          <span className="!text-gray-600">계정이 없으신가요?</span>
          <Button
            type="link"
            onClick={handleSignupClick}
            className="h-11 rounded-lg text-sm text-gray-600 border-gray-300 hover:border-gray-400 hover:text-gray-700"
          >
            회원가입
          </Button>
        </Flex>
      </Form.Item>
    </Form>
  );
};

export default LoginForm;
