import React from 'react';
import { Typography, Button, Space, Avatar, Dropdown } from 'antd';
import {
  UserAddOutlined,
  LoginOutlined,
  UserOutlined,
  LogoutOutlined,
} from '@ant-design/icons';
import type { MenuProps } from 'antd';
import { useNavigate } from 'react-router-dom';

import { useCurrentUser, useLogout } from '@/hooks/useUser';
import RouterPaths from '@/routes/Router';
import { getAvatarRenderInfo } from '@/utils/genderUtils';

const { Title } = Typography;

/**
 * 애플리케이션 헤더 컴포넌트
 * 로그인 상태에 따라 다른 UI를 보여줍니다
 */
const Header: React.FC = () => {
  const navigate = useNavigate();
  const { data: user, isLoading } = useCurrentUser();
  const logout = useLogout();

  // 로그인 버튼 클릭 핸들러
  const handleLogin = () => {
    navigate(RouterPaths.Login);
  };

  // 회원가입 버튼 클릭 핸들러
  const handleSignUp = () => {
    navigate(RouterPaths.SignUp);
  };

  // 마이페이지 버튼 클릭 핸들러
  const handleMyPage = () => {
    navigate(RouterPaths.MyPage);
  };
  // 대시보드 버튼 클릭 핸들러
  const handleDashboard = () => {
    navigate(RouterPaths.AdminDashboard);
  };

  // 로그아웃 버튼 클릭 핸들러
  const handleLogout = () => {
    logout();
    navigate(RouterPaths.Home);
  };

  // 아바타 렌더링: getAvatarRenderInfo를 직접 사용

  // 로그인된 사용자의 드롭다운 메뉴
  const userMenuItems: MenuProps['items'] =
    user?.role === 'admin'
      ? [
          {
            key: 'mypage',
            icon: <UserOutlined />,
            label: '마이페이지',
            onClick: handleMyPage,
          },
          {
            key: 'dashboard',
            icon: <UserOutlined />,
            label: '대시보드',
            onClick: handleDashboard,
          },
          { type: 'divider' },
          {
            key: 'logout',
            icon: <LogoutOutlined />,
            label: '로그아웃',
            onClick: handleLogout,
          },
        ]
      : [
          {
            key: 'mypage',
            icon: <UserOutlined />,
            label: '마이페이지',
            onClick: handleMyPage,
          },
          { type: 'divider' },
          {
            key: 'logout',
            icon: <LogoutOutlined />,
            label: '로그아웃',
            onClick: handleLogout,
          },
        ];

  // 로딩 중일 때는 기본 헤더만 표시
  const isLoggedIn = !!user && !isLoading;

  return (
    <header className="bg-white shadow-sm fixed top-0 left-0 right-0 z-50">
      <div className="max-w-6xl min-h-[64px] mx-auto px-4 py-2 flex justify-between items-center">
        <Title
          level={3}
          className="gradient-text !mb-0 cursor-pointer"
          onClick={() => navigate(RouterPaths.Home)}
        >
          퍼스널 컬러 진단 AI
        </Title>

        {isLoggedIn && user ? (
          // 로그인된 상태
          <div className="flex items-center gap-4">
            <span className="text-gray-600 hidden sm:inline">
              안녕하세요,{' '}
              <span className="font-bold text-gray-800">{user.nickname}</span>님
            </span>
            <Dropdown
              menu={{ items: userMenuItems }}
              placement="bottomRight"
              arrow
            >
              <div className="flex items-center gap-2 cursor-pointer hover:bg-gray-50 px-3 py-2 rounded-lg transition-colors">
                {(() => {
                  const avatarConfig = getAvatarRenderInfo(
                    user?.gender,
                    user?.id
                  );
                  return (
                    <Avatar
                      size="default"
                      className={avatarConfig.className}
                      style={avatarConfig.style}
                    >
                      {avatarConfig.content}
                    </Avatar>
                  );
                })()}
                <span className="hidden sm:inline text-gray-700">
                  {user.nickname}
                </span>
              </div>
            </Dropdown>
          </div>
        ) : (
          // 로그인되지 않은 상태
          <Space>
            <Button
              type="default"
              icon={<LoginOutlined />}
              onClick={handleLogin}
            >
              로그인
            </Button>
            <Button
              type="primary"
              icon={<UserAddOutlined />}
              onClick={handleSignUp}
            >
              회원가입
            </Button>
          </Space>
        )}
      </div>
    </header>
  );
};

export default Header;
