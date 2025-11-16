import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';

import { queryClient } from './lib/query-client';
import './index.css';
import App from './App.tsx';
import {
  HomePage,
  SignUpPage,
  LoginPage,
  MyPage,
  // PersonalColorTestPage, // 대화형 진단으로 변경으로 인해 비활성화
  ChatbotPage,
  AdminDashboard,
} from './pages';

const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      {
        index: true,
        element: <HomePage />,
      },
      {
        path: 'signup',
        element: <SignUpPage />,
      },
      {
        path: 'login',
        element: <LoginPage />,
      },
      {
        path: 'mypage',
        element: <MyPage />,
      },
      // {
      //   path: 'personal-color-test',
      //   element: <PersonalColorTestPage />,
      // }, // 대화형 진단으로 변경으로 인해 비활성화
      {
        path: 'chatbot',
        element: <ChatbotPage />,
      },
      {
        path: 'admin-dashboard',
        element: <AdminDashboard />,
      },
    ],
  },
]);

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
      {/* 개발 환경에서만 DevTools 표시 */}
      {import.meta.env.DEV && <ReactQueryDevtools initialIsOpen={false} />}
    </QueryClientProvider>
  </StrictMode>
);
