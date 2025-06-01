import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

const Home = () => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedFilter, setSelectedFilter] = useState('全て');
  const navigate = useNavigate();

  useEffect(() => {
    const fetchUserInfo = async () => {
      try {
        const token = localStorage.getItem('access_token');
        if (!token) {
          navigate('/login');
          return;
        }

        const response = await axios.get('http://localhost:8000/api/v1/auth/me', {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });

        setUser(response.data);
      } catch (err) {
        if (err.response?.status === 401) {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          navigate('/login');
        } else {
          setError('ユーザー情報の取得に失敗しました。');
        }
      } finally {
        setLoading(false);
      }
    };

    fetchUserInfo();
  }, [navigate]);

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
      navigate('/login');
    }
  };

  if (loading) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        minHeight: '100vh' 
      }}>
        <div>読み込み中...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        minHeight: '100vh' 
      }}>
        <div style={{ color: '#d32f2f' }}>{error}</div>
      </div>
    );
  }

  return (
    <div style={{ 
      display: 'flex',
      minHeight: '100vh',
      backgroundColor: '#f5f5f5'
    }}>
      {/* サイドバー */}
      <div style={{
        width: '250px',
        backgroundColor: '#2c3e50',
        color: 'white',
        padding: '1rem',
        boxShadow: '2px 0 5px rgba(0,0,0,0.1)'
      }}>
        <div style={{ marginBottom: '2rem' }}>
          <h2 style={{ margin: 0, fontSize: '1.2rem', color: '#ecf0f1' }}>
            Knowledge System
          </h2>
        </div>
        
        <nav>
          <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
            <li style={{ marginBottom: '0.5rem' }}>
              <a href="#" style={{
                display: 'block',
                padding: '0.75rem 1rem',
                color: '#ecf0f1',
                textDecoration: 'none',
                borderRadius: '4px',
                backgroundColor: '#34495e',
                transition: 'background-color 0.3s'
              }}>
                ダッシュボード
              </a>
            </li>
            <li style={{ marginBottom: '0.5rem' }}>
              <a href="#" style={{
                display: 'block',
                padding: '0.75rem 1rem',
                color: '#bdc3c7',
                textDecoration: 'none',
                borderRadius: '4px',
                transition: 'background-color 0.3s'
              }}>
                記事管理
              </a>
            </li>
            <li style={{ marginBottom: '0.5rem' }}>
              <a href="#" style={{
                display: 'block',
                padding: '0.75rem 1rem',
                color: '#bdc3c7',
                textDecoration: 'none',
                borderRadius: '4px',
                transition: 'background-color 0.3s'
              }}>
                ナレッジベース
              </a>
            </li>
            <li style={{ marginBottom: '0.5rem' }}>
              <a href="#" style={{
                display: 'block',
                padding: '0.75rem 1rem',
                color: '#bdc3c7',
                textDecoration: 'none',
                borderRadius: '4px',
                transition: 'background-color 0.3s'
              }}>
                設定
              </a>
            </li>
          </ul>
        </nav>
        
        <div style={{ marginTop: '2rem', marginBottom: '2rem' }}>
          <label style={{
            display: 'block',
            marginBottom: '0.5rem',
            color: '#bdc3c7',
            fontSize: '0.9rem'
          }}>
            ステータスフィルター
          </label>
          <select
            value={selectedFilter}
            onChange={(e) => setSelectedFilter(e.target.value)}
            style={{
              width: '100%',
              padding: '0.5rem',
              backgroundColor: '#34495e',
              color: '#ecf0f1',
              border: '1px solid #4a6741',
              borderRadius: '4px',
              fontSize: '0.9rem',
              cursor: 'pointer'
            }}
          >
            <option value="全て">全て</option>
            <option value="下書き">下書き</option>
            <option value="提出">提出</option>
            <option value="承認">承認</option>
            <option value="公開">公開</option>
          </select>
        </div>
        
        <div style={{ 
          position: 'absolute',
          bottom: '1rem',
          left: '1rem',
          right: '1rem',
          width: '218px'
        }}>
          <div style={{
            padding: '0.75rem',
            backgroundColor: '#34495e',
            borderRadius: '4px',
            marginBottom: '0.5rem'
          }}>
            <div style={{ fontSize: '0.9rem', color: '#bdc3c7' }}>ログイン中</div>
            <div style={{ fontSize: '0.8rem', color: '#ecf0f1', fontWeight: 'bold' }}>
              {user?.username}
            </div>
          </div>
          <button
            onClick={handleLogout}
            style={{
              width: '100%',
              padding: '0.75rem',
              backgroundColor: '#7f8c8d',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '0.9rem',
              transition: 'background-color 0.3s'
            }}
            onMouseEnter={(e) => {
              e.target.style.backgroundColor = '#95a5a6';
            }}
            onMouseLeave={(e) => {
              e.target.style.backgroundColor = '#7f8c8d';
            }}
          >
            ログアウト
          </button>
        </div>
      </div>

      {/* メインコンテンツ */}
      <div style={{ 
        flex: 1,
        padding: '2rem'
      }}>
        <div style={{
          backgroundColor: 'white',
          borderRadius: '8px',
          boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
          overflow: 'hidden'
        }}>
          <div style={{
            backgroundColor: '#1976d2',
            color: 'white',
            padding: '1.5rem'
          }}>
            <h1 style={{ margin: 0, fontSize: '1.5rem' }}>ダッシュボード</h1>
          </div>
          
          <div style={{ padding: '2rem' }}>
            <h2 style={{ marginBottom: '1.5rem', color: '#333' }}>ユーザー情報</h2>
            
            {user && (
              <div style={{ display: 'grid', gap: '1rem' }}>
                <div style={{
                  padding: '1rem',
                  backgroundColor: '#f8f9fa',
                  borderRadius: '4px',
                  border: '1px solid #e9ecef'
                }}>
                  <label style={{ 
                    display: 'block', 
                    fontWeight: 'bold', 
                    marginBottom: '0.5rem',
                    color: '#495057'
                  }}>
                    ユーザーID:
                  </label>
                  <span style={{ color: '#6c757d' }}>{user.id}</span>
                </div>
                
                <div style={{
                  padding: '1rem',
                  backgroundColor: '#f8f9fa',
                  borderRadius: '4px',
                  border: '1px solid #e9ecef'
                }}>
                  <label style={{ 
                    display: 'block', 
                    fontWeight: 'bold', 
                    marginBottom: '0.5rem',
                    color: '#495057'
                  }}>
                    ユーザー名:
                  </label>
                  <span style={{ color: '#212529' }}>{user.username}</span>
                </div>
                
                <div style={{
                  padding: '1rem',
                  backgroundColor: '#f8f9fa',
                  borderRadius: '4px',
                  border: '1px solid #e9ecef'
                }}>
                  <label style={{ 
                    display: 'block', 
                    fontWeight: 'bold', 
                    marginBottom: '0.5rem',
                    color: '#495057'
                  }}>
                    フルネーム:
                  </label>
                  <span style={{ color: '#212529' }}>{user.full_name || '未設定'}</span>
                </div>
                
                <div style={{
                  padding: '1rem',
                  backgroundColor: '#f8f9fa',
                  borderRadius: '4px',
                  border: '1px solid #e9ecef'
                }}>
                  <label style={{ 
                    display: 'block', 
                    fontWeight: 'bold', 
                    marginBottom: '0.5rem',
                    color: '#495057'
                  }}>
                    管理者権限:
                  </label>
                  <span style={{ 
                    color: user.is_admin ? '#28a745' : '#6c757d',
                    fontWeight: 'bold'
                  }}>
                    {user.is_admin ? 'あり' : 'なし'}
                  </span>
                </div>
                
                <div style={{
                  padding: '1rem',
                  backgroundColor: '#f8f9fa',
                  borderRadius: '4px',
                  border: '1px solid #e9ecef'
                }}>
                  <label style={{ 
                    display: 'block', 
                    fontWeight: 'bold', 
                    marginBottom: '0.5rem',
                    color: '#495057'
                  }}>
                    作成日時:
                  </label>
                  <span style={{ color: '#6c757d' }}>
                    {new Date(user.created_at).toLocaleString('ja-JP')}
                  </span>
                </div>
                
                <div style={{
                  padding: '1rem',
                  backgroundColor: '#f8f9fa',
                  borderRadius: '4px',
                  border: '1px solid #e9ecef'
                }}>
                  <label style={{ 
                    display: 'block', 
                    fontWeight: 'bold', 
                    marginBottom: '0.5rem',
                    color: '#495057'
                  }}>
                    更新日時:
                  </label>
                  <span style={{ color: '#6c757d' }}>
                    {new Date(user.updated_at).toLocaleString('ja-JP')}
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Home;