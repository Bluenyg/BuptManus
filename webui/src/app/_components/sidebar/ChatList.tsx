import ChatItem from './ChatItem';

// 定义将要接收的 session 对象的类型
interface Session {
  id: string;
  title: string;
  // 您可以根据需要添加其他字段
}

// 定义 props 的类型
interface ChatListProps {
  isExpanded: boolean;
  sessions: Session[]; // 明确指出 sessions 是一个 prop
  searchTerm: string;
}

export default function ChatList({ isExpanded, sessions = [], searchTerm }: ChatListProps) {

  return (
    <div
      className={`mt-2 px-2 transition-opacity duration-200 ${
        isExpanded ? 'opacity-100' : 'opacity-0'
      }`}
    >
      <p className="text-sm text-gray-500 px-2 mb-1">History</p>
      <div className="space-y-1">
        {sessions.map((s) => (
          <ChatItem key={s.id} session={s} />
        ))}
        {sessions.length === 0 && isExpanded && searchTerm.length > 0 && (
          <p className="text-xs text-gray-400 text-center py-2">No matching.</p>
        )}
      </div>
    </div>
  );
}
