'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Navbar from '../../components/Navbar';

export default function ChangePasswordPage() {
  const [formData, setFormData] = useState({
    oldPassword: '',
    newPassword: '',
    confirmPassword: ''
  });
  const [errors, setErrors] = useState<{ [key: string]: string }>({});
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState('');
  const router = useRouter();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    // Clear error when user starts typing
    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: ''
      }));
    }
  };

  const validateForm = () => {
    const newErrors: { [key: string]: string } = {};

    if (!formData.oldPassword) {
      newErrors.oldPassword = '現在のパスワードを入力してください';
    }

    if (!formData.newPassword) {
      newErrors.newPassword = '新しいパスワードを入力してください';
    } else if (formData.newPassword.length < 6) {
      newErrors.newPassword = 'パスワードは6文字以上で入力してください';
    }

    if (!formData.confirmPassword) {
      newErrors.confirmPassword = 'パスワードの確認を入力してください';
    } else if (formData.newPassword !== formData.confirmPassword) {
      newErrors.confirmPassword = 'パスワードが一致しません';
    }

    if (formData.oldPassword === formData.newPassword) {
      newErrors.newPassword = '新しいパスワードは現在のパスワードと異なる必要があります';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    setIsLoading(true);
    setMessage('');

    try {
      const token = localStorage.getItem('access_token');
      if (!token) {
        router.push('/login');
        return;
      }

      const response = await fetch('http://localhost:8000/api/v1/auth/password', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          old_password: formData.oldPassword,
          new_password: formData.newPassword
        })
      });

      if (response.ok) {
        const result = await response.json();
        setMessage('パスワードが正常に更新されました');
        setFormData({
          oldPassword: '',
          newPassword: '',
          confirmPassword: ''
        });
        setTimeout(() => {
          router.push('/home');
        }, 2000);
      } else {
        const errorData = await response.json();
        if (response.status === 400) {
          setErrors({ oldPassword: errorData.detail || 'パスワードの更新に失敗しました' });
        } else {
          setMessage('パスワードの更新に失敗しました');
        }
      }
    } catch (error) {
      console.error('Password update error:', error);
      setMessage('ネットワークエラーが発生しました');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="flex flex-col justify-center py-12 sm:px-6 lg:px-8">
        <div className="sm:mx-auto sm:w-full sm:max-w-md">
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            パスワード変更
          </h2>
        </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="oldPassword" className="block text-sm font-medium text-gray-700">
                現在のパスワード
              </label>
              <div className="mt-1">
                <input
                  id="oldPassword"
                  name="oldPassword"
                  type="password"
                  value={formData.oldPassword}
                  onChange={handleChange}
                  className={`appearance-none block w-full px-3 py-2 border ${
                    errors.oldPassword ? 'border-red-300' : 'border-gray-300'
                  } rounded-md placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm`}
                  placeholder="現在のパスワードを入力"
                />
                {errors.oldPassword && (
                  <p className="mt-2 text-sm text-red-600">{errors.oldPassword}</p>
                )}
              </div>
            </div>

            <div>
              <label htmlFor="newPassword" className="block text-sm font-medium text-gray-700">
                新しいパスワード
              </label>
              <div className="mt-1">
                <input
                  id="newPassword"
                  name="newPassword"
                  type="password"
                  value={formData.newPassword}
                  onChange={handleChange}
                  className={`appearance-none block w-full px-3 py-2 border ${
                    errors.newPassword ? 'border-red-300' : 'border-gray-300'
                  } rounded-md placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm`}
                  placeholder="新しいパスワードを入力"
                />
                {errors.newPassword && (
                  <p className="mt-2 text-sm text-red-600">{errors.newPassword}</p>
                )}
              </div>
            </div>

            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700">
                新しいパスワード（確認）
              </label>
              <div className="mt-1">
                <input
                  id="confirmPassword"
                  name="confirmPassword"
                  type="password"
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  className={`appearance-none block w-full px-3 py-2 border ${
                    errors.confirmPassword ? 'border-red-300' : 'border-gray-300'
                  } rounded-md placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm`}
                  placeholder="新しいパスワードを再入力"
                />
                {errors.confirmPassword && (
                  <p className="mt-2 text-sm text-red-600">{errors.confirmPassword}</p>
                )}
              </div>
            </div>

            {message && (
              <div className={`text-sm text-center ${
                message.includes('正常') ? 'text-green-600' : 'text-red-600'
              }`}>
                {message}
              </div>
            )}

            <div>
              <button
                type="submit"
                disabled={isLoading}
                className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:bg-gray-400 disabled:cursor-not-allowed"
              >
                {isLoading ? 'パスワード更新中...' : 'パスワードを更新'}
              </button>
            </div>

            <div className="text-center">
              <button
                type="button"
                onClick={() => router.push('/home')}
                className="text-sm text-blue-600 hover:text-blue-500"
              >
                ホームに戻る
              </button>
            </div>
          </form>
        </div>
        </div>
      </div>
    </div>
  );
}