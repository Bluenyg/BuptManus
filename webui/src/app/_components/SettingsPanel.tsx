'use client';

import { useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import Draggable from 'react-draggable';

export default function SettingsPanel({
  visible,
  onClose,
  onNewChat,
  onViewHistory,
  particleColor,
  setParticleColor,
}: {
  visible: boolean;
  onClose: () => void;
  onNewChat: () => void;
  onViewHistory: () => void;
  particleColor: string[];
  setParticleColor: (colors: string[]) => void;
}) {
  const [isDark, setIsDark] = useState(false);
  const [activeTab, setActiveTab] = useState<'appearance' | 'chat'>('appearance');
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    setIsDark(document.documentElement.classList.contains('dark'));
  }, []);

  const toggleDarkMode = () => {
    const newTheme = isDark ? 'light' : 'dark';
    localStorage.setItem('theme', newTheme);
    document.documentElement.classList.toggle('dark');
    setIsDark(!isDark);
  };

  return (
    <AnimatePresence>
      {visible && (
        <Draggable handle=".handle-drag" defaultPosition={{ x: 0, y: 0 }}>
          <motion.div
            initial={{ opacity: 0, y: -20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -20, scale: 0.95 }}
            transition={{ duration: 0.25 }}
            className="fixed top-16 right-4 z-50 w-72 bg-white dark:bg-gray-900 rounded-lg shadow-lg cursor-default"
          >
            {/* Header */}
            <div className="handle-drag flex items-center justify-between p-4 border-b dark:border-gray-700 cursor-move bg-gray-100 dark:bg-gray-800 rounded-t-lg">
              <div className="flex space-x-4">
                <button
                  className={`px-2 py-1 text-sm font-medium ${
                    activeTab === 'appearance'
                      ? 'text-blue-600 border-b-2 border-blue-600'
                      : 'text-gray-500 dark:text-gray-400'
                  }`}
                  onClick={() => setActiveTab('appearance')}
                >
                  界面设置
                </button>
                <button
                  className={`px-2 py-1 text-sm font-medium ${
                    activeTab === 'chat'
                      ? 'text-blue-600 border-b-2 border-blue-600'
                      : 'text-gray-500 dark:text-gray-400'
                  }`}
                  onClick={() => setActiveTab('chat')}
                >
                  聊天功能
                </button>
              </div>
              <button onClick={onClose} className="text-gray-500 hover:text-gray-700 dark:hover:text-white">
                ✖
              </button>
            </div>

            {/* Search */}
            <div className="p-4">
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="搜索设置..."
                className="w-full px-3 py-1 text-sm border rounded bg-gray-50 dark:bg-gray-800 dark:border-gray-700 dark:text-white"
              />
            </div>

            {/* Content */}
            <div className="p-4 space-y-4 max-h-[60vh] overflow-y-auto">
              {activeTab === 'appearance' && (
                <>
                  {searchTerm === '' || '模式'.includes(searchTerm) ? (
                    <div className="space-y-2">
                      <button
                        onClick={toggleDarkMode}
                        className="w-full px-4 py-2 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 rounded"
                      >
                        {isDark ? '☀️ 切换亮色模式' : '🌙 切换暗黑模式'}
                      </button>
                    </div>
                  ) : null}

                  {(searchTerm === '' || '粒子'.includes(searchTerm)) && (
                    <div className="mt-4">
                      <h4 className="text-sm font-medium mb-1 dark:text-gray-300">粒子颜色</h4>
                      <div className="flex gap-2 flex-wrap">
                        {particleColor.map((color, i) => (
                          <input
                            key={i}
                            type="color"
                            value={color}
                            onChange={(e) => {
                              const arr = [...particleColor];
                              arr[i] = e.target.value;
                              setParticleColor(arr);
                            }}
                            className="w-6 h-6 rounded-full p-0 border-none cursor-pointer"
                          />
                        ))}
                        <button onClick={() => setParticleColor([...particleColor, '#ffffff'])} className="text-sm text-blue-600">➕</button>
                        {particleColor.length > 1 && (
                          <button onClick={() => setParticleColor(particleColor.slice(0, -1))} className="text-sm text-red-600">➖</button>
                        )}
                      </div>
                    </div>
                  )}
                </>
              )}

              {activeTab === 'chat' && (
                <>
                  {(searchTerm === '' || '新聊天'.includes(searchTerm)) && (
                    <button
                      onClick={onNewChat}
                      className="w-full px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded"
                    >
                      🆕 开启新聊天
                    </button>
                  )}
                  {(searchTerm === '' || '历史'.includes(searchTerm)) && (
                    <button
                      onClick={onViewHistory}
                      className="w-full px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded"
                    >
                      📜 查看历史记录
                    </button>
                  )}
                </>
              )}
            </div>
          </motion.div>
        </Draggable>
      )}
    </AnimatePresence>
  );
}
