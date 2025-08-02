'use client';

import { nanoid } from 'nanoid';
import { useCallback, useEffect, useRef, useState } from 'react';

import { sendMessage, useStore } from '~/core/store';
import { fetchSessions, fetchMessages, createSession } from '~/core/api/sessions';
import { useSessionStore } from '~/core/store/session';
import { useMessageStore } from '~/core/store/messages';
import { cn } from '~/core/utils';
import { type Message } from '~/core/messaging';

import { AppHeader } from './_components/AppHeader';
import { InputBox } from './_components/InputBox';
import { MessageHistoryView } from './_components/MessageHistoryView';
import ParticleBgBackground from './_components/ParticlesBackground';
import { UserGuide } from './_components/UserGuide';
import ChatHistoryModal from './_components/ChatHistoryModal';
import { PlusIcon, ClockIcon } from '@heroicons/react/24/solid';

// 🔥 修复消息格式化函数
const formatMessage = (msg: any): Message => {
  console.log('🔍 Formatting message:', msg);

  // 如果content是字符串，检查是否是JSON格式的workflow或multimodal
  if (typeof msg.content === 'string') {
    try {
      const parsed = JSON.parse(msg.content);

      // 检查是否是workflow消息 - 增加更严格的检查
      if (parsed && (parsed.thought || parsed.title || parsed.steps || parsed.workflow)) {
        console.log('🔄 Detected workflow message');

        // 🔥 确保workflow对象完整
        let workflowContent = parsed.workflow || parsed;

        // 验证必需的字段
        if (!workflowContent.steps) {
          workflowContent.steps = [];
        }
        if (!workflowContent.title) {
          workflowContent.title = 'Workflow';
        }
        if (!workflowContent.thought) {
          workflowContent.thought = '';
        }

        return {
          id: msg.id || nanoid(),
          role: msg.role as 'user' | 'assistant',
          type: 'workflow' as const,
          content: { workflow: workflowContent }, // 🔥 确保包装在workflow对象中
          timestamp: msg.timestamp,
          session_id: msg.session_id
        };
      }

      // 检查是否是multimodal消息
      if (Array.isArray(parsed) || (parsed.text && parsed.image)) {
        console.log('🖼️ Detected multimodal message');
        let multimodalContent = [];

        if (Array.isArray(parsed)) {
          multimodalContent = parsed;
        } else if (parsed.text && parsed.image) {
          multimodalContent = [
            { type: "text", text: parsed.text },
            { type: "image_url", image_url: { url: parsed.image } }
          ];
        }

        return {
          id: msg.id || nanoid(),
          role: msg.role as 'user' | 'assistant',
          type: 'multimodal' as const,
          content: multimodalContent,
          timestamp: msg.timestamp,
          session_id: msg.session_id
        };
      }
    } catch (e) {
      console.log('❌ Failed to parse JSON content, treating as text:', e);
    }
  }

  // 如果content是对象
  if (typeof msg.content === 'object' && msg.content) {
    // 检查是否是workflow - 增加更严格的检查
    if (msg.content.workflow || msg.content.thought || msg.content.title || msg.content.steps) {
      console.log('🔄 Detected workflow object message');

      // 🔥 确保workflow对象完整
      let workflowContent = msg.content.workflow || msg.content;

      // 验证必需的字段
      if (!workflowContent.steps) {
        workflowContent.steps = [];
      }
      if (!workflowContent.title) {
        workflowContent.title = 'Workflow';
      }
      if (!workflowContent.thought) {
        workflowContent.thought = '';
      }

      return {
        id: msg.id || nanoid(),
        role: msg.role as 'user' | 'assistant',
        type: 'workflow' as const,
        content: { workflow: workflowContent }, // 🔥 确保包装在workflow对象中
        timestamp: msg.timestamp,
        session_id: msg.session_id
      };
    }

    // 检查是否是multimodal
    if (Array.isArray(msg.content) || (msg.content.text && msg.content.image)) {
      console.log('🖼️ Detected multimodal object message');
      let multimodalContent = [];

      if (Array.isArray(msg.content)) {
        multimodalContent = msg.content;
      } else if (msg.content.text && msg.content.image) {
        multimodalContent = [
          { type: "text", text: msg.content.text },
          { type: "image_url", image_url: { url: msg.content.image } }
        ];
      }

      return {
        id: msg.id || nanoid(),
        role: msg.role as 'user' | 'assistant',
        type: 'multimodal' as const,
        content: multimodalContent,
        timestamp: msg.timestamp,
        session_id: msg.session_id
      };
    }
  }

  // 默认作为文本消息处理
  console.log('📝 Treating as text message');
  return {
    id: msg.id || nanoid(),
    role: msg.role as 'user' | 'assistant',
    type: 'text' as const,
    content: typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content),
    timestamp: msg.timestamp,
    session_id: msg.session_id
  };
};

export default function HomePage() {
  const abortControllerRef = useRef<AbortController | null>(null);
  const messages = useStore((state) => state.messages);
  const responding = useStore((state) => state.responding);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { sessions, currentSessionId, setSessions, setCurrentSessionId, addSession } = useSessionStore();
  const { loadMessagesForSession } = useMessageStore();

  const [particleColor, setParticleColor] = useState<string[]>(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('langmanus.particleColor');
      return stored ? JSON.parse(stored) : ['#ffcc00'];
    }
    return ['#ffcc00'];
  });
  const [showColorPanel, setShowColorPanel] = useState(false);
  const [showHistoryModal, setShowHistoryModal] = useState(false);
  const [isInitialized, setIsInitialized] = useState(false);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('langmanus.particleColor', JSON.stringify(particleColor));
    }
  }, [particleColor]);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files.length > 0) {
      const file = event.target.files[0];
      setSelectedFile(file);
    } else {
      setSelectedFile(null);
    }
  };

  const handleUploadButtonClick = () => {
    fileInputRef.current?.click();
  };

  const handleClearFile = () => {
    setSelectedFile(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  // 🔥 关键修改：确保消息发送到正确的会话
  const handleSendMessage = useCallback(
    async (
      text: string,
      config: { deepThinkingMode: boolean; searchBeforePlanning: boolean }
    ) => {
      // 🔥 确保有当前会话ID
      if (!currentSessionId) {
        console.error('❌ No current session ID, cannot send message');
        return;
      }

      console.log('📤 Sending message to session:', currentSessionId, 'Message:', text);

      let imageBase64: string | null = null;

      if (selectedFile) {
        imageBase64 = await new Promise<string | null>((resolve) => {
          const reader = new FileReader();
          reader.onloadend = () => resolve(reader.result as string);
          reader.onerror = () => resolve(null);
          reader.readAsDataURL(selectedFile);
        });
        handleClearFile();
      }

      const abortController = new AbortController();
      abortControllerRef.current = abortController;

      const messageToSend = imageBase64
        ? {
            id: nanoid(),
            role: 'user' as const,
            type: 'multimodal' as const,
            content: { text: text, image: imageBase64 },
          }
        : {
            id: nanoid(),
            role: 'user' as const,
            type: 'text' as const,
            content: text,
          };

      try {
        // 🔥 关键：明确传递当前会话ID
        await sendMessage(
          messageToSend,
          {
            ...config,
            sessionId: currentSessionId // 🔥 确保传递正确的会话ID
          },
          { abortSignal: abortController.signal }
        );

        console.log('✅ Message sent successfully to session:', currentSessionId);

      } catch (error) {
        console.error('❌ Failed to send message:', error);
      } finally {
        abortControllerRef.current = null;
      }
    },
    [selectedFile, currentSessionId]
  );

  const chatScrollAnchorRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (chatScrollAnchorRef.current) {
      chatScrollAnchorRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  // 初始化数据
  useEffect(() => {
    async function init() {
      if (isInitialized) return;

      console.log('🔄 Initializing HomePage...');

      try {
        // 从URL中获取session ID
        const urlParams = new URLSearchParams(window.location.search);
        const sessionIdFromUrl = urlParams.get('session');

        // 获取所有会话
        const sessionList = await fetchSessions();
        setSessions(sessionList);

        if (sessionIdFromUrl) {
          // 如果URL中有session ID，先验证该session是否存在
          const sessionExists = sessionList.find(s => s.id === sessionIdFromUrl);
          if (sessionExists) {
            console.log('📜 Loading session from URL:', sessionIdFromUrl);
            setCurrentSessionId(sessionIdFromUrl);

            // 🔥 关键修复：加载历史消息到正确的store
            const historyMessages = await fetchMessages(sessionIdFromUrl);
            console.log('💬 Loaded history messages:', historyMessages);

            // 🔥 使用新的格式化函数处理消息
            const formattedMessages = historyMessages.map(formatMessage);
            console.log('✅ Formatted messages:', formattedMessages);

            // 🔥 同时更新store的状态
            useStore.setState({
              messages: formattedMessages,
              state: {
                messages: formattedMessages.map(msg => ({
                  role: msg.role,
                  content: typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content)
                }))
              }
            });

            setIsInitialized(true);
            return;
          } else {
            // 如果session不存在，清除URL参数
            console.warn('⚠️ Session not found in URL, clearing...');
            window.history.replaceState({}, '', '/');
          }
        }

        // 如果没有URL参数或session不存在
        if (sessionList.length > 0) {
          const firstSession = sessionList[0];
          console.log('📜 Loading first session:', firstSession.id);
          setCurrentSessionId(firstSession.id);

          const historyMessages = await fetchMessages(firstSession.id);
          console.log('💬 Loaded first session messages:', historyMessages);

          // 🔥 使用新的格式化函数处理消息
          const formattedMessages = historyMessages.map(formatMessage);
          console.log('✅ Formatted first session messages:', formattedMessages);

          useStore.setState({
            messages: formattedMessages,
            state: {
              messages: formattedMessages.map(msg => ({
                role: msg.role,
                content: typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content)
              }))
            }
          });

          // 更新URL但不刷新页面
          window.history.replaceState({}, '', `/?session=${firstSession.id}`);
        } else {
          // 创建新会话
          console.log('🆕 No sessions found, creating new one...');
          const newSession = await createSession();
          setCurrentSessionId(newSession.id);
          addSession(newSession);
          useStore.setState({ messages: [], state: { messages: [] } });
          window.history.replaceState({}, '', `/?session=${newSession.id}`);
        }

        setIsInitialized(true);
      } catch (error) {
        console.error('❌ Failed to initialize:', error);
        setIsInitialized(true);
      }
    }

    init();
  }, [isInitialized, setSessions, setCurrentSessionId, addSession]);

  const handleNewChat = async () => {
    console.log('🆕 Creating new chat...');
    try {
      const session = await createSession();
      setCurrentSessionId(session.id);
      addSession(session);
      useStore.setState({ messages: [], state: { messages: [] } });
      // 更新URL但不刷新页面
      window.history.pushState({}, '', `/?session=${session.id}`);
      console.log('✅ Created new chat session:', session.id);
    } catch (error) {
      console.error('❌ Failed to create new chat:', error);
    }
  };

  // 🔥 修改：处理历史记录选择的函数
  const handleHistorySelect = async (sessionId: string) => {
    console.log('📜 Switching to session:', sessionId);

    try {
      // 🔥 关闭历史记录模态框
      setShowHistoryModal(false);

      // 1. 设置当前会话ID
      setCurrentSessionId(sessionId);

      // 2. 加载该会话的消息
      const historyMessages = await fetchMessages(sessionId);
      console.log('💬 Loaded session messages:', historyMessages);

      // 3. 🔥 使用新的格式化函数处理消息
      const formattedMessages = historyMessages.map(formatMessage);
      console.log('✅ Formatted history messages:', formattedMessages);

      useStore.setState({
        messages: formattedMessages,
        state: {
          messages: formattedMessages.map(msg => ({
            role: msg.role,
            content: typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content)
          }))
        }
      });

      // 4. 🔥 重要：更新URL，确保后续操作都在正确的会话中
      window.history.pushState({}, '', `/?session=${sessionId}`);

      console.log('✅ Successfully switched to session:', sessionId, 'Messages:', formattedMessages.length);
    } catch (error) {
      console.error('❌ Error switching to session:', error);
      alert('切换会话失败，请重试');
    }
  };

  // 如果还没初始化完成，显示加载状态
  if (!isInitialized) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-lg">Loading...</div>
      </div>
    );
  }

  return (
    <div className="relative w-full min-h-screen flex flex-col items-center justify-center bg-transparent">
      <ParticleBgBackground color={particleColor} />
      <UserGuide />

      {/* 颜色调色板按钮 */}
      <div className="fixed top-4 left-4 z-50">
        <button
          onClick={() => setShowColorPanel(!showColorPanel)}
          className="w-8 h-8 rounded-full text-white text-sm flex items-center justify-center shadow-md"
          title="Customize particle color"
        >
          🎨
        </button>
        {showColorPanel && (
          <div className="mt-2 p-3 rounded-md bg-white dark:bg-gray-800 shadow space-y-2">
            {particleColor.map((color, index) => (
              <input
                key={index}
                type="color"
                value={color}
                onChange={(e) => {
                  const updated = [...particleColor];
                  updated[index] = e.target.value;
                  setParticleColor(updated);
                }}
                className="w-8 h-8 border-none rounded-full cursor-pointer"
              />
            ))}
            <div className="flex gap-2 pt-1">
              <button
                onClick={() => setParticleColor([...particleColor, '#ffffff'])}
                className="text-sm text-blue-500 hover:underline"
              >
                +
              </button>
              {particleColor.length > 1 && (
                <button
                  onClick={() => setParticleColor(particleColor.slice(0, -1))}
                  className="text-sm text-red-500 hover:underline"
                >
                  -
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      <div className="relative z-10 flex min-h-screen min-w-page flex-col items-center backdrop-blur-sm bg-white/70 dark:bg-black/70">
        <header className="fixed left-0 right-0 top-0 flex h-16 w-full items-center px-4 z-20">
          <AppHeader />
        </header>

        {/* 显示当前会话信息 */}
        <div className="fixed top-16 left-4 z-20 bg-black/20 text-white px-3 py-1 rounded text-sm">
          Session: {currentSessionId?.slice(-8) || 'None'}
        </div>

        <main className="mb-48 mt-16 px-4 w-full max-w-page">
          <MessageHistoryView className="w-page" messages={messages} loading={responding} />
          <div ref={chatScrollAnchorRef} className="h-0" />
        </main>

        <footer
          className={cn(
            'fixed bottom-4 transition-transform duration-500 ease-in-out',
            messages.length === 0 ? 'w-[640px] translate-y-[-34vh]' : 'w-page'
          )}
        >
          {messages.length === 0 && (
            <div className="flex w-[640px] translate-y-[-32px] flex-col">
              <h3 className="mb-2 text-center text-3xl font-medium">Hello! What can I do for you?</h3>
              <div className="px-4 text-center text-lg text-gray-500 dark:text-gray-300">
                I am your intelligent agent, I can help you do anything.
                <br /> —— From BuptManus
              </div>
            </div>
          )}

          {/* 新建对话和历史记录按钮 */}
          <div className="flex justify-center gap-20 mb-4 px-4">
            <button
              className="flex items-center gap-2 px-3.5 py-2 rounded-full font-semibold text-white bg-gradient-to-r from-blue-500 to-blue-600 shadow-md hover:shadow-lg hover:from-blue-600 hover:to-blue-700 transform hover:scale-105 transition duration-200"
              onClick={handleNewChat}
            >
              <PlusIcon className="w-3.5 h-3.5 text-white" />
              NewChat
            </button>
            <button
              className="flex items-center gap-2 px-5 py-2 rounded-full font-semibold text-gray-800 bg-gray-200 dark:bg-gray-700 dark:text-white hover:bg-gray-300 dark:hover:bg-gray-600 shadow-sm hover:shadow-md transform hover:scale-105 transition duration-200"
              onClick={() => setShowHistoryModal(true)}
            >
              <ClockIcon className="w-3.5 h-3.5 text-gray-700 dark:text-white" />
              History
            </button>
          </div>

          <div className="flex flex-col items-center w-full max-w-page mb-2 px-4">
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              className="hidden"
              accept="image/*"
            />
            <div className="flex flex-col overflow-hidden rounded-[24px] border bg-white shadow-lg dark:bg-gray-900 dark:border-gray-700 w-full">
              <InputBox
                size={messages.length === 0 ? 'large' : 'normal'}
                responding={responding}
                onSend={handleSendMessage}
                onCancel={() => {
                  abortControllerRef.current?.abort();
                  abortControllerRef.current = null;
                }}
                fileInputRef={fileInputRef}
                selectedFile={selectedFile}
                onUploadClick={handleUploadButtonClick}
                onClearFile={handleClearFile}
              />
            </div>
          </div>

          <div className="absolute bottom-[-32px] h-8 w-page backdrop-blur-sm" />
        </footer>
      </div>

      {/* 历史记录模态框 */}
      {showHistoryModal && (
        <ChatHistoryModal
          onClose={() => setShowHistoryModal(false)}
          onSelectSession={handleHistorySelect}
        />
      )}
    </div>
  );
}