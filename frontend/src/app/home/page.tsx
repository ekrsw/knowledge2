'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import axios from 'axios';
import Navbar from '../../components/Navbar';

interface User {
  id: string;
  username: string;
  full_name: string;
  is_admin: boolean;
  created_at: string;
  updated_at: string;
}

const HomePage = () => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedFilter, setSelectedFilter] = useState('全て');
  const router = useRouter();

  useEffect(() => {
    const fetchUserInfo = async () => {
      try {
        const token = localStorage.getItem('access_token');
        if (!token) {
          router.push('/login');
          return;
        }

        const response = await axios.get('http://localhost:8000/api/v1/auth/me', {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });

        setUser(response.data);
      } catch (err) {
        if (axios.isAxiosError(err) && err.response?.status === 401) {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          router.push('/login');
        } else {
          setError('ユーザー情報の取得に失敗しました。');
        }
      } finally {
        setLoading(false);
      }
    };

    fetchUserInfo();
  }, [router]);

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

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="text-gray-600">読み込み中...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="text-red-600">{error}</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <Navbar currentUser={user} />
      <div className="flex">
        {/* サイドバー */}
        <div className="w-64 bg-slate-700 text-white p-4 shadow-lg flex flex-col" style={{ minHeight: 'calc(100vh - 64px)' }}>
        <div className="mb-8">
          <h2 className="text-xl font-semibold text-gray-100">
            サイドメニュー
          </h2>
        </div>
        
        <nav className="mb-8">
          <ul className="space-y-2">
            <li>
              <a href="#" className="block px-4 py-3 text-gray-100 bg-slate-600 rounded-md transition-colors duration-200">
                ダッシュボード
              </a>
            </li>
            <li>
              <a href="#" className="block px-4 py-3 text-gray-300 hover:bg-slate-600 rounded-md transition-colors duration-200">
                記事管理
              </a>
            </li>
            <li>
              <a href="#" className="block px-4 py-3 text-gray-300 hover:bg-slate-600 rounded-md transition-colors duration-200">
                ナレッジベース
              </a>
            </li>
            <li>
              <a href="#" className="block px-4 py-3 text-gray-300 hover:bg-slate-600 rounded-md transition-colors duration-200">
                設定
              </a>
            </li>
          </ul>
        </nav>
        
        <div className="mb-8">
          <label className="block text-gray-300 text-sm font-medium mb-2">
            ステータスフィルター
          </label>
          <select
            value={selectedFilter}
            onChange={(e) => setSelectedFilter(e.target.value)}
            className="w-full px-3 py-2 bg-slate-600 text-gray-100 border border-slate-500 rounded-md text-sm cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="全て">全て</option>
            <option value="下書き">下書き</option>
            <option value="提出">提出</option>
            <option value="承認">承認</option>
            <option value="公開">公開</option>
          </select>
        </div>
        
        <div className="mt-auto">
          <div className="bg-slate-600 rounded-md p-3 mb-2">
            <div className="text-sm text-gray-300">ログイン中</div>
            <div className="text-sm text-gray-100 font-semibold truncate">
              {user?.username}
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="w-full py-2 px-4 bg-gray-500 hover:bg-gray-600 text-white rounded-md transition-colors duration-200 text-sm font-medium"
          >
            ログアウト
          </button>
        </div>
        </div>

        {/* メインコンテンツ */}
        <div className="flex-1 p-8">
        <div className="bg-white rounded-lg shadow-md overflow-hidden">
          <div className="bg-blue-600 text-white p-6">
            <h1 className="text-2xl font-bold">ダッシュボード</h1>
          </div>
          
          <div className="p-8">
            <h2 className="text-xl font-semibold mb-6 text-gray-800">ユーザー情報</h2>
            
            {user && (
              <div className="grid gap-4">
                <div className="bg-gray-50 border border-gray-200 rounded-md p-4">
                  <label className="block font-semibold text-gray-700 mb-2">
                    ユーザーID:
                  </label>
                  <span className="text-gray-600">{user.id}</span>
                </div>
                
                <div className="bg-gray-50 border border-gray-200 rounded-md p-4">
                  <label className="block font-semibold text-gray-700 mb-2">
                    ユーザー名:
                  </label>
                  <span className="text-gray-900">{user.username}</span>
                </div>
                
                <div className="bg-gray-50 border border-gray-200 rounded-md p-4">
                  <label className="block font-semibold text-gray-700 mb-2">
                    フルネーム:
                  </label>
                  <span className="text-gray-900">{user.full_name || '未設定'}</span>
                </div>
                
                <div className="bg-gray-50 border border-gray-200 rounded-md p-4">
                  <label className="block font-semibold text-gray-700 mb-2">
                    管理者権限:
                  </label>
                  <span className={`font-semibold ${
                    user.is_admin ? 'text-green-600' : 'text-gray-600'
                  }`}>
                    {user.is_admin ? 'あり' : 'なし'}
                  </span>
                </div>
                
                <div className="bg-gray-50 border border-gray-200 rounded-md p-4">
                  <label className="block font-semibold text-gray-700 mb-2">
                    作成日時:
                  </label>
                  <span className="text-gray-600">
                    {new Date(user.created_at).toLocaleString('ja-JP')}
                  </span>
                </div>
                
                <div className="bg-gray-50 border border-gray-200 rounded-md p-4">
                  <label className="block font-semibold text-gray-700 mb-2">
                    更新日時:
                  </label>
                  <span className="text-gray-600">
                    {new Date(user.updated_at).toLocaleString('ja-JP')}
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
        </div>
      </div>
    </div>
  );
};

export default HomePage;