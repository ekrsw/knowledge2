'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import axios from 'axios';

interface User {
  id: string;
  username: string;
  full_name: string;
  is_admin: boolean;
}

interface NavbarProps {
  currentUser?: User | null;
}

const Navbar = ({ currentUser }: NavbarProps) => {
  const [user, setUser] = useState<User | null>(currentUser || null);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const router = useRouter();

  useEffect(() => {
    if (!currentUser) {
      fetchUserInfo();
    }
  }, [currentUser]);

  const fetchUserInfo = async () => {
    try {
      const token = localStorage.getItem('access_token');
      if (!token) return;

      const response = await axios.get('http://localhost:8000/api/v1/auth/me', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      setUser(response.data);
    } catch (err) {
      console.error('Failed to fetch user info:', err);
    }
  };

  const handleLogout = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const refreshToken = localStorage.getItem('refresh_token');
      
      if (token) {
        await axios.post('http://localhost:8000/api/v1/auth/logout', 
          { refresh_token: refreshToken },
          {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json',
            },
          }
        );
      }
    } catch (err) {
      console.error('ログアウトエラー:', err);
    } finally {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      router.push('/login');
    }
  };

  return (
    <nav className="bg-white shadow-md border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          {/* ロゴとナビゲーション */}
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <button
                onClick={() => router.push('/home')}
                className="text-xl font-bold text-blue-600 hover:text-blue-800 transition-colors"
              >
                Knowledge System
              </button>
            </div>
            
            <div className="hidden md:ml-6 md:flex md:space-x-8">
              <button
                onClick={() => router.push('/home')}
                className="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium transition-colors"
              >
                ダッシュボード
              </button>
              <button
                onClick={() => {/* TODO: 記事管理ページ */}}
                className="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium transition-colors"
              >
                記事管理
              </button>
              <button
                onClick={() => {/* TODO: ナレッジベースページ */}}
                className="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium transition-colors"
              >
                ナレッジベース
              </button>
            </div>
          </div>

          {/* ユーザーメニュー */}
          <div className="flex items-center">
            <div className="ml-3 relative">
              <div>
                <button
                  onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                  className="flex items-center text-sm rounded-full focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                  <div className="bg-blue-600 text-white rounded-full h-8 w-8 flex items-center justify-center">
                    {user?.username?.charAt(0).toUpperCase() || 'U'}
                  </div>
                  <div className="ml-2 hidden md:block">
                    <div className="text-sm font-medium text-gray-700">
                      {user?.username || 'ユーザー'}
                    </div>
                    {user?.is_admin && (
                      <div className="text-xs text-blue-600">管理者</div>
                    )}
                  </div>
                  <svg
                    className="ml-2 h-4 w-4 text-gray-400"
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fillRule="evenodd"
                      d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
                      clipRule="evenodd"
                    />
                  </svg>
                </button>
              </div>

              {isDropdownOpen && (
                <div className="origin-top-right absolute right-0 mt-2 w-48 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5">
                  <div className="py-1">
                    <button
                      onClick={() => {
                        setIsDropdownOpen(false);
                        router.push('/home');
                      }}
                      className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    >
                      プロフィール
                    </button>
                    <button
                      onClick={() => {
                        setIsDropdownOpen(false);
                        router.push('/change-password');
                      }}
                      className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    >
                      パスワード変更
                    </button>
                    <div className="border-t border-gray-100"></div>
                    <button
                      onClick={() => {
                        setIsDropdownOpen(false);
                        handleLogout();
                      }}
                      className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    >
                      ログアウト
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;