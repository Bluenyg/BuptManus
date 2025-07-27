function SessionList() {
  const { sessions, setCurrentSessionId } = useSessionStore();

  return (
    <div className="p-4 space-y-2">
      {sessions.map((s) => (
        <button
          key={s.id}
          onClick={() => setCurrentSessionId(s.id)}
          className="w-full text-left px-2 py-1 hover:bg-gray-100"
        >
          {s.title}
        </button>
      ))}
    </div>
  );
}
