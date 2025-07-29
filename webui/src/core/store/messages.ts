import { create } from 'zustand';

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
  session_id?: string;
}

interface MessageState {
  messages: Message[];
  isLoading: boolean;
  setMessages: (messages: Message[]) => void;
  addMessage: (message: Message) => void;
  clearMessages: () => void;
  loadMessagesForSession: (sessionId: string) => Promise<void>;
  setLoading: (loading: boolean) => void;
}

export const useMessageStore = create<MessageState>((set, get) => ({
  messages: [],
  isLoading: false,

  setMessages: (messages) => {
    set({ messages });
  },

  addMessage: (message) => {
    set((state) => ({
      messages: [...state.messages, message]
    }));
  },

  clearMessages: () => {
    set({ messages: [] });
  },

  setLoading: (loading) => {
    set({ isLoading: loading });
  },

  loadMessagesForSession: async (sessionId: string) => {
    set({ isLoading: true });
    try {
      console.log(`Loading messages for session: ${sessionId}`);

      const response = await fetch(`http://localhost:8000/api/chat/sessions/${sessionId}/messages`);

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Failed to fetch messages:', response.status, errorText);
        throw new Error(`Failed to fetch messages: ${response.status}`);
      }

      const messages = await response.json();
      console.log(`Loaded ${messages.length} messages for session ${sessionId}:`, messages);

      set({ messages, isLoading: false });

    } catch (error) {
      console.error('Error loading messages:', error);
      set({ messages: [], isLoading: false });
      throw error;
    }
  },
}));