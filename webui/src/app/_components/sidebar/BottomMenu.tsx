'use client';

import { useState } from 'react';
import { Cog6ToothIcon, QuestionMarkCircleIcon } from '@heroicons/react/24/outline';
import DarkModeToggle from '../DarkModeToggle';

interface BottomMenuProps {
  isExpanded: boolean;
  particleColor: string[];
  setParticleColor: React.Dispatch<React.SetStateAction<string[]>>;
  updateColor: (index: number, value: string) => void;
}

export default function BottomMenu({ isExpanded, particleColor, setParticleColor, updateColor }: BottomMenuProps) {
  const [showSettings, setShowSettings] = useState(false);

  return (
    <div className={`flex flex-col border-t dark:border-gray-800 text-sm text-gray-600 dark:text-gray-400 ${
        isExpanded ? 'p-3' : 'py-3'
    }`}>
      {/* 设置按钮 */}
      <button
        onClick={() => setShowSettings((prev) => !prev)}
        className={`flex items-center hover:text-blue-500 w-full py-1 ${
          isExpanded ? 'space-x-2' : 'justify-center'
        }`}
      >
        <Cog6ToothIcon className={`transition-all duration-200 ${
            isExpanded ? 'w-4 h-4' : 'w-6 h-6' // [!code focus]
          }`} />
        {isExpanded && (
          <span className="whitespace-nowrap overflow-hidden">
            Settings
          </span>
        )}
      </button>

      {/* 展开设置内容 */}
      {isExpanded && showSettings && (
        <div className="mt-2 space-y-2 ml-6">
          {/* 暗黑模式开关 */}
          <div className="flex items-center justify-between">
            <span>DarkMode</span>
            <DarkModeToggle />
          </div>

          {/* 粒子颜色选择器 */}
          <div>
            <p className="text-sm mb-1">ParticleColor</p>
            <div className="flex gap-2">
              {particleColor.map((color, idx) => (
                <input
                  key={idx}
                  type="color"
                  value={color}
                  onChange={(e) => updateColor(idx, e.target.value)}
                  className="w-6 h-6 rounded-full cursor-pointer border"
                />
              ))}
              <button
                onClick={() => setParticleColor([...particleColor, '#ffffff'])}
                className="text-xs text-blue-500 hover:underline"
              >
                ➕
              </button>
              {particleColor.length > 1 && (
                <button
                  onClick={() => setParticleColor(particleColor.slice(0, -1))}
                  className="text-xs text-red-500 hover:underline"
                >
                ➖
              </button>
              )}
            </div>
          </div>
        </div>
      )}


    </div>
  );
}
