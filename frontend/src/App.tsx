import { Routes, Route } from 'react-router-dom';
import { ConfigProvider, FloatButton } from 'antd';

import { HomePage, SignUpPage, LoginPage, MyPage, PersonalColorTestPage, ChatbotPage } from './pages';
import { Header, Footer, ScrollToTop } from './components';

import './App.css';
import RouterPaths from './routes/Router';

function App() {

  return (
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: '#1677ff',
          borderRadius: 6,
        },
      }}
    >
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-purple-50">
        {/* 페이지 이동 시 스크롤 맨 위로 */}
        <ScrollToTop />

        {/* Header */}
        <Header />

        {/* Main Routes */}
        <div className='mt-15'>
          <Routes>
            <Route path={RouterPaths.Home} element={<HomePage />} />
            <Route path={RouterPaths.SignUp} element={<SignUpPage />} />
            <Route path={RouterPaths.Login} element={<LoginPage />} />
            <Route path={RouterPaths.MyPage} element={<MyPage />} />
            <Route path={RouterPaths.PersonalColorTest} element={<PersonalColorTestPage />} />
            <Route path={RouterPaths.Chatbot} element={<ChatbotPage />} />
          </Routes>
        </div>

        {/* Footer */}
        <Footer />
        <FloatButton.BackTop type='primary' />
      </div>
    </ConfigProvider>
  );
}

export default App;
