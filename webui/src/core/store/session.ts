import { create } from 'zustand';
import { useMessageStore } from './messages';

interface Session {
  id: string;
  title: string;
  createdAt: string;
}

interface SessionState {
  sessions: Session[];
  currentSessionId: string | null;
  setSessions: (sessions: Session[] | ((prev: Session[]) => Session[])) => void;
  setCurrentSessionId: (id: string | null) => void;
  removeSession: (id: string) => void;
  addSession: (session: Session) => void;
  switchToSession: (sessionId: string) => Promise<void>; // 新增方法
}

export const useSessionStore = create<SessionState>((set, get) => ({
  sessions: [],
  currentSessionId: null,

  setSessions: (sessions) => {
    set((state) => ({
      sessions: typeof sessions === 'function' ? sessions(state.sessions) : sessions
    }));
  },

  setCurrentSessionId: (id) => {
    set({ currentSessionId: id });
  },

  removeSession: (id) => {
    set((state) => ({
      sessions: state.sessions.filter(s => s.id !== id),
      currentSessionId: state.currentSessionId === id ? null : state.currentSessionId
    }));
  },

  addSession: (session) => {
    set((state) => ({
      sessions: [session, ...state.sessions]
    }));
  },

  // 新增：切换到指定会话并加载消息
  switchToSession: async (sessionId: string) => {
    try {
      console.log(`Switching to session: ${sessionId}`);

      // 更新当前会话ID
      set({ currentSessionId: sessionId });

      // 加载该会话的消息
      const messageStore = useMessageStore.getState();
      await messageStore.loadMessagesForSession(sessionId);

      console.log(`Successfully switched to session: ${sessionId}`);

    } catch (error) {
      console.error(`Error switching to session ${sessionId}:`, error);
      throw error;
    }
  },
}));
