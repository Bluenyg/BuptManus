export type ChatSession = {
  id: string;
  title: string;
  created_at: string;
  createdAt: string; // 后端返回了两个时间字段
};



export async function fetchSessions(): Promise<ChatSession[]> {
  try {
    console.log("🔄 Fetching sessions...");
    const response = await fetch("http://localhost:8000/api/chat/sessions");

    console.log("📡 Response status:", response.status);
    console.log("📡 Response headers:", response.headers);

    if (!response.ok) {
      const errorText = await response.text();
      console.error("❌ Response not ok:", errorText);
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    console.log("📦 Raw response data:", data);

    // 处理不同的响应格式
    let sessions: ChatSession[];
    if (Array.isArray(data)) {
      sessions = data;
    } else if (data.sessions && Array.isArray(data.sessions)) {
      sessions = data.sessions;
    } else {
      console.warn("⚠️ Unexpected data format:", data);
      return [];
    }

    console.log("✅ Processed sessions:", sessions);
    return sessions;

  } catch (error) {
    console.error("❌ Failed to fetch sessions:", error);
    return [];
  }
}


export async function fetchMessages(sessionId: string) {
  const res = await fetch(`http://localhost:8000/api/chat/sessions/${sessionId}/messages`);
  if (!res.ok) throw new Error("Failed to fetch messages");
  return await res.json();
}

export async function createSession(): Promise<ChatSession> {
  const res = await fetch("http://localhost:8000/api/chat/sessions", {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to create session");
  return await res.json();
}

export async function deleteSession(sessionId: string) {
  const res = await fetch(`/api/chat/sessions/${sessionId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete session");
}
