'use client';

import React, { useEffect, useState } from 'react';
import { useSessionStore } from '~/core/store/session';
import { useStore } from '~/core/store';

interface Session {
  id: string;
  title: string;
  createdAt: string;
}

interface ChatHistoryModalProps {
  onClose: () => void;
  onSelectSession: (sessionId: string) => void;
}

export default function ChatHistoryModal({ onClose, onSelectSession }: ChatHistoryModalProps) {
  const { sessions, setSessions, currentSessionId, setCurrentSessionId } = useSessionStore();
  const [search, setSearch] = useState('');
  const [confirmId, setConfirmId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    async function loadSessions() {
      try {
        const res = await fetch('http://localhost:8000/api/chat/sessions');

        if (!res.ok) {
          const errorText = await res.text();
          console.error("Failed to fetch sessions:", res.status, errorText);
          setSessions([]);
          return;
        }

        const data = await res.json();
        console.log("API response:", data);

        if (Array.isArray(data)) {
          setSessions(data);
        } else {
          console.error("API response is not an array:", data);
          setSessions([]);
        }
      } catch (error) {
        console.error("Error loading sessions:", error);
        setSessions([]);
      }
    }
    loadSessions();
  }, [setSessions]);

  // 🔥 修复：正确处理会话切换和消息加载
  const handleOpenSession = async (sessionId: string) => {
    try {
      setIsLoading(true);
      console.log(`🔄 Switching to session: ${sessionId}`);

      // 调用父组件的选择会话方法
      await onSelectSession(sessionId);

      // 关闭模态框
      onClose();

      console.log(`✅ Successfully switched to session: ${sessionId}`);

    } catch (error) {
      console.error('❌ Error loading session:', error);
      alert('加载会话失败，请重试');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteConfirmed = async () => {
    if (!confirmId) return;

    try {
      console.log(`🗑️ Attempting to delete session: ${confirmId}`);

      const res = await fetch(`http://localhost:8000/api/chat/sessions/${confirmId}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      console.log(`Delete response status: ${res.status}`);

      if (!res.ok) {
        const errorText = await res.text();
        console.error('Delete failed:', res.status, errorText);
        throw new Error(`Failed to delete session: ${res.status} ${errorText}`);
      }

      const responseData = await res.json();
      console.log('Delete response:', responseData);

      // 更新会话列表
      setSessions((prev) => {
        if (!Array.isArray(prev)) return [];
        const filtered = prev.filter((s) => s.id !== confirmId);
        console.log(`Removed session ${confirmId}, remaining sessions:`, filtered.length);
        return filtered;
      });

      // 如果删除的是当前会话，清空当前会话
      if (currentSessionId === confirmId) {
        setCurrentSessionId(null);
        useStore.setState({ messages: [] });
        window.history.pushState({}, '', '/');
      }

      setConfirmId(null);
      console.log(`✅ Successfully deleted session: ${confirmId}`);

    } catch (error) {
      console.error("❌ Error deleting session:", error);
      alert(`删除失败: ${error.message}`);
      setConfirmId(null);
    }
  };

  const safeSessions = Array.isArray(sessions) ? sessions : [];
  const filtered = safeSessions.filter((s) =>
    s.title?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg w-[500px] max-h-[80vh] p-6 overflow-y-auto relative">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">History Chat</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-red-500 text-xl font-bold"
            disabled={isLoading}
          >
            ✕
          </button>
        </div>

        <input
          type="text"
          placeholder="Search the title..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full border px-3 py-2 rounded mb-4"
          disabled={isLoading}
        />

        {isLoading ? (
          <div className="text-center py-8">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <p className="text-gray-500 mt-2">加载中...</p>
          </div>
        ) : filtered.length === 0 ? (
          <p className="text-gray-500 text-center py-8">No matching conversation</p>
        ) : (
          <ul className="space-y-3">
            {filtered.map((s) => (
              <li
                key={s.id}
                className="flex justify-between items-center border-b pb-2"
              >
                <div className="flex-1">
                  <p
                    className={`font-medium cursor-pointer hover:underline hover:text-blue-600 ${
                      s.id === currentSessionId ? 'text-blue-600 font-bold' : ''
                    }`}
                    onClick={() => handleOpenSession(s.id)}
                  >
                    {s.title || 'Untitled Chat'}
                    {s.id === currentSessionId && ' (当前)'}
                  </p>
                  <p className="text-xs text-gray-400">
                    {new Date(s.createdAt).toLocaleString()}
                  </p>
                </div>
                <button
                  className="text-red-600 hover:underline ml-2"
                  onClick={(e) => {
                    e.stopPropagation();
                    setConfirmId(s.id);
                  }}
                  disabled={isLoading}
                >
                  Delete
                </button>
              </li>
            ))}
          </ul>
        )}

        {/* 删除确认弹窗 */}
        {confirmId && (
          <div className="absolute inset-0 bg-black bg-opacity-40 flex items-center justify-center z-10">
            <div className="bg-white dark:bg-gray-700 rounded-lg p-6 shadow-lg max-w-xs text-center">
              <p className="text-lg font-medium mb-4">Are you sure you want to delete this session?</p>
              <div className="flex justify-center gap-4">
                <button
                  onClick={() => setConfirmId(null)}
                  className="px-4 py-2 rounded bg-gray-300 hover:bg-gray-400"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDeleteConfirmed}
                  className="px-4 py-2 rounded bg-red-500 text-white hover:bg-red-600"
                >
                  Confirm deletion
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
