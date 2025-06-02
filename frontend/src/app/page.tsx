'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    router.push('/login');
  }, [router]);

  return (
    <div className="flex justify-center items-center min-h-screen">
      <div className="text-gray-600">リダイレクト中...</div>
    </div>
  );
}
