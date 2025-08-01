'use client';
import { useEffect, useState } from 'react';
import { Message } from '~/core/messaging';

interface ChatHistoryItem {
  id: string;
  timestamp: number;
  messages: Message[];
}

export default function HistoryPanel({
  onLoadHistory,
  onClose,
}: {
  onLoadHistory: (messages: Message[]) => void;
  onClose: () => void;
}) {
  const [history, setHistory] = useState<ChatHistoryItem[]>([]);

  useEffect(() => {
    const stored = localStorage.getItem('langmanus.history');
    if (stored) setHistory(JSON.parse(stored));
  }, []);

  const handleLoad = (msgs: Message[]) => {
    onLoadHistory(msgs);
    onClose();
  };

  const handleClear = () => {
    localStorage.removeItem('BuptManus.history');
    setHistory([]);
  };

  return (
    <div className="absolute top-20 right-4 z-50 w-80 max-h-[60vh] overflow-auto bg-white dark:bg-gray-800 shadow-lg rounded p-4">
      <div className="flex justify-between items-center mb-2">
        <h3 className="font-bold">🕒 Chat History</h3>
        <button
          onClick={onClose}
          className="text-gray-500 hover:text-gray-700"
        >
          ✖
        </button>
      </div>
      {history.length === 0 ? (
        <p className="text-gray-500">No history yet.</p>
      ) : (
        <ul className="space-y-2">
          {history.map((item) => (
            <li
              key={item.id}
              className="flex justify-between items-center hover:bg-gray-100 dark:hover:bg-gray-700 p-1 rounded cursor-pointer"
            >
              <span
                onClick={() => handleLoad(item.messages)}
                className="flex-1 truncate"
              >
                {new Date(item.timestamp).toLocaleString()}
              </span>
              <button
                onClick={() => {
                  const newHistory = history.filter((h) => h.id !== item.id);
                  setHistory(newHistory);
                  localStorage.setItem('langmanus.history', JSON.stringify(newHistory));
                }}
                className="text-red-500 hover:text-red-700"
                title="Delete"
              >
                🗑
              </button>
            </li>
          ))}
        </ul>
      )}
      <div className="mt-4 text-right">
        <button
          onClick={handleClear}
          className="text-sm text-blue-600 hover:underline"
        >
          Clear all
        </button>
      </div>
    </div>
  );
}
