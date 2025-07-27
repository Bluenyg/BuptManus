'use client';

import { useState } from 'react';
import { useSessionStore } from '~/core/store/session';
import NewChatButton from './NewChatButton';
import ChatList from './ChatList';
import BottomMenu from './BottomMenu';
import { MagnifyingGlassIcon } from '@heroicons/react/24/outline';

interface SidebarProps {
  particleColor: string[];
  setParticleColor: React.Dispatch<React.SetStateAction<string[]>>;
  updateColor: (index: number, value: string) => void;
}

export default function Sidebar({ particleColor, setParticleColor, updateColor }: any) {

  const [isExpanded, setIsExpanded] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [isInputFocused, setIsInputFocused] = useState(false);
  const { sessions } = useSessionStore();
  const filteredSessions = sessions.filter((session) =>
    session.title?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div
      className={`flex h-screen flex-col justify-between border-r bg-gray-100 transition-all duration-300 ease-in-out dark:border-gray-800 dark:bg-gray-900 ${
        isExpanded ? "w-60" : "w-16"
      }`}
      onMouseEnter={() => setIsExpanded(true)}
      onMouseLeave={() => {
         if (!isInputFocused) {
          setIsExpanded(false);
        }
      }}
    >
      <div>
        {/* 将展开状态传递给子组件 */}
        <NewChatButton isExpanded={isExpanded} />
        {isExpanded && (
          <div className="p-2">
            <div className="relative">
              <span className="absolute inset-y-0 left-0 flex items-center pl-2">
                <MagnifyingGlassIcon className="h-4 w-4 text-gray-500" />
              </span>
              <input
                type="text"
                placeholder="Search history..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                onFocus={() => setIsInputFocused(true)}
                onBlur={() => {
                  setIsInputFocused(false);
                }}
                className="w-full rounded-md border border-gray-300 bg-gray-50 py-1.5 pl-8 pr-3 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-800"
              />
            </div>
          </div>
        )}
        <ChatList
          isExpanded={isExpanded}
          sessions={filteredSessions}
          searchTerm={searchTerm}
        />
      </div>
      <BottomMenu
        isExpanded={isExpanded}
        particleColor={particleColor}
        setParticleColor={setParticleColor}
        updateColor={updateColor}
      />
    </div>
  );
}
