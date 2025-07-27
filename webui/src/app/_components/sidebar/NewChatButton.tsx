'use client';

import { PlusIcon } from '@heroicons/react/24/solid';
import { useSessionStore } from '~/core/store/session'; // 假设您的store路径
import { createSession } from '~/core/api/sessions'; // 假设您的api路径
import { useStore } from '~/core/store'; // 假设您的store路径

export default function NewChatButton({ isExpanded }: { isExpanded: boolean }) {
  const { setCurrentSessionId } = useSessionStore();

  const handleNewChat = async () => {
    const session = await createSession();
    setCurrentSessionId(session.id);
    useStore.setState({ messages: [] }); // 清空当前消息
    // 可以选择刷新页面，或者通过状态管理让右侧内容更新
    window.location.href = `/?session=${session.id}`;
  };

  return (
    <button
      className={`flex items-center w-full py-3 text-blue-600 hover:bg-blue-50 dark:hover:bg-gray-800 transition-colors ${
        isExpanded ? 'px-4' : 'justify-center'
      }`}
    >
      <PlusIcon
        className={`transition-all duration-200 ${
          isExpanded ? 'w-5 h-5' : 'w-6 h-6' // [!code focus]
        }`}
      />
      {isExpanded && (
        <span className="ml-2 whitespace-nowrap overflow-hidden">
          NewChat
        </span>
      )}
    </button>
  );
}