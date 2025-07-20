'use client';

import { useEffect, useState } from 'react';

export function UserGuide() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const hasSeenGuide = localStorage.getItem('langmanus.userGuideShown');
    if (!hasSeenGuide) {
      setVisible(true);
    }
  }, []);

  const handleClose = () => {
    setVisible(false);
    localStorage.setItem('langmanus.userGuideShown', 'true');
  };

  if (!visible) return null;

  return (
    <div className="fixed bottom-24 left-4 md:left-8 z-50 bg-white dark:bg-gray-800 text-gray-800 dark:text-white border rounded-lg shadow-lg p-4 w-72">
      <h3 className="font-semibold mb-2">👋 欢迎使用 LangManus！</h3>
      <ul className="list-disc pl-5 text-sm space-y-1">
        <li>🌗 点击右上角切换亮/暗模式</li>
        <li>🎨 点击左上角按钮更改粒子颜色</li>
        <li>🖼️ 上传图片体验多模态输入</li>
      </ul>
      <button
        onClick={handleClose}
        className="mt-4 px-3 py-1 rounded bg-blue-500 text-white text-sm hover:bg-blue-600"
      >
        我知道了
      </button>
    </div>
  );
}
