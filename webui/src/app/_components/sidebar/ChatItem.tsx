import { useSessionStore } from '~/core/store/session';

export default function ChatItem({ session }: { session: any }) {
  const { currentSessionId, setCurrentSessionId } = useSessionStore();

  const isActive = currentSessionId === session.id;

  return (
    <button
      onClick={() => setCurrentSessionId(session.id)}
      className={`w-full text-left px-4 py-2 rounded-md ${
        isActive
          ? 'bg-blue-100 text-blue-700 font-semibold'
          : 'hover:bg-gray-200 dark:hover:bg-gray-700'
      }`}
    >
      {session.title || 'Untitled'}
    </button>
  );
}
