'use client';

import { nanoid } from 'nanoid';
import { useCallback, useEffect, useRef, useState } from 'react';

import { sendMessage, useStore } from '~/core/store';
import { fetchSessions, fetchMessages, createSession } from '~/core/api/sessions';
import { useSessionStore } from '~/core/store/session';
import { cn } from '~/core/utils';

import { AppHeader } from './_components/AppHeader';
import { InputBox } from './_components/InputBox';
import { MessageHistoryView } from './_components/MessageHistoryView';
import ParticleBgBackground from './_components/ParticlesBackground';
import { UserGuide } from './_components/UserGuide';
import ChatHistoryModal from './_components/ChatHistoryModal';

export default function HomePage() {
  const abortControllerRef = useRef<AbortController | null>(null);
  const messages = useStore((state) => state.messages);
  const responding = useStore((state) => state.responding);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { sessions, currentSessionId, setSessions, setCurrentSessionId } = useSessionStore();

  const [particleColor, setParticleColor] = useState<string[]>(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('langmanus.particleColor');
      return stored ? JSON.parse(stored) : ['#ffcc00'];
    }
    return ['#ffcc00'];
  });
  const [showColorPanel, setShowColorPanel] = useState(false);

  const [showHistoryModal, setShowHistoryModal] = useState(false);

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

  const handleSendMessage = useCallback(
    async (
      text: string,
      config: { deepThinkingMode: boolean; searchBeforePlanning: boolean }
    ) => {
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

      // 🔥 确保使用当前会话ID，不要改变
      console.log('📤 Sending message to session:', currentSessionId);

      await sendMessage(
        messageToSend,
        { ...config, sessionId: currentSessionId! },
        { abortSignal: abortController.signal }
      );

      abortControllerRef.current = null;
    },
    [selectedFile, currentSessionId]
  );

  const chatScrollAnchorRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (chatScrollAnchorRef.current) {
      chatScrollAnchorRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  useEffect(() => {
    async function init() {
      // 从URL中获取session ID
      const urlParams = new URLSearchParams(window.location.search);
      const sessionIdFromUrl = urlParams.get('session');

      const sessionList = await fetchSessions();
      setSessions(sessionList);

      if (sessionIdFromUrl) {
        // 如果URL中有session ID，先验证该session是否存在
        const sessionExists = sessionList.find(s => s.id === sessionIdFromUrl);
        if (sessionExists) {
          setCurrentSessionId(sessionIdFromUrl);
          const messages = await fetchMessages(sessionIdFromUrl);
          useStore.setState({ messages });
          console.log('🔄 Loaded session from URL:', sessionIdFromUrl);
          return;
        } else {
          // 如果session不存在，清除URL参数
          window.history.replaceState({}, '', '/');
        }
      }

      // 如果没有URL参数或session不存在，创建新session
      if (sessionList.length > 0) {
        const firstId = sessionList[0].id;
        setCurrentSessionId(firstId);
        const messages = await fetchMessages(firstId);
        useStore.setState({ messages });
        console.log('🔄 Loaded first session:', firstId);
      } else {
        const newSession = await createSession();
        setCurrentSessionId(newSession.id);
        console.log('🆕 Created new session:', newSession.id);
      }
    }
    init();
  }, [setSessions, setCurrentSessionId]);

  const handleNewChat = async () => {
    const session = await createSession();
    setCurrentSessionId(session.id);
    useStore.setState({ messages: [] });
    // 🔥 修复：不要刷新页面，直接更新URL
    window.history.pushState({}, '', `/?session=${session.id}`);
    console.log('🆕 Created new chat session:', session.id);
  };

  // 🔥 新增：处理历史记录选择的函数
  const handleHistorySelect = async (sessionId: string) => {
    console.log('📜 Switching to session:', sessionId);

    try {
      // 1. 设置当前会话ID
      setCurrentSessionId(sessionId);

      // 2. 加载该会话的消息
      const messages = await fetchMessages(sessionId);
      useStore.setState({ messages });

      // 3. 更新URL但不刷新页面
      window.history.pushState({}, '', `/?session=${sessionId}`);

      // 4. 关闭历史记录模态框
      setShowHistoryModal(false);

      console.log('✅ Successfully switched to session:', sessionId, 'Messages:', messages.length);
    } catch (error) {
      console.error('❌ Error switching to session:', error);
      alert('切换会话失败，请重试');
    }
  };

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

        {/* 🔥 显示当前会话信息 */}
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
          <div className="flex justify-center gap-4 mb-4 px-4">
            <button
              className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
              onClick={handleNewChat}
            >
              NewChat
            </button>
            <button
              className="bg-gray-200 text-black px-4 py-2 rounded hover:bg-gray-300"
              onClick={() => setShowHistoryModal(true)}
            >
              HistoryChat
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

      {/* 🔥 修复：传递回调函数给历史记录模态框 */}
      {showHistoryModal && (
        <ChatHistoryModal
          onClose={() => setShowHistoryModal(false)}
          onSelectSession={handleHistorySelect}
        />
      )}
    </div>
  );
}
