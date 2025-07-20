'use client';

import { nanoid } from 'nanoid';
import { useCallback, useEffect, useRef, useState } from 'react';

import { sendMessage, useStore } from '~/core/store';
import { cn } from '~/core/utils';

import { AppHeader } from './_components/AppHeader';
import { InputBox } from './_components/InputBox';
import { MessageHistoryView } from './_components/MessageHistoryView';
import ParticlesBackground from './_components/ParticlesBackground';
import { UserGuide } from './_components/UserGuide';

export default function HomePage() {
  const abortControllerRef = useRef<AbortController | null>(null);
  const messages = useStore((state) => state.messages);
  const responding = useStore((state) => state.responding);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [particleColor, setParticleColor] = useState<string[]>(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('langmanus.particleColor');
      return stored ? JSON.parse(stored) : ['#ffcc00'];
    }
    return ['#ffcc00'];
  });

  const [showColorPanel, setShowColorPanel] = useState(false);

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
      content: string,
      config: { deepThinkingMode: boolean; searchBeforePlanning: boolean }
    ) => {
      let imageBase64: string | null = null;

      if (selectedFile) {
        imageBase64 = await new Promise<string | null>((resolve) => {
          const reader = new FileReader();
          reader.onloadend = () => {
            const base64 = reader.result as string;
            resolve(base64);
          };
          reader.onerror = () => resolve(null);
          reader.readAsDataURL(selectedFile);
        });
        handleClearFile();
      }

      const abortController = new AbortController();
      abortControllerRef.current = abortController;

      await sendMessage(
        {
          id: nanoid(),
          role: 'user',
          type: imageBase64 ? 'multimodal' : 'text',
          content,
          image: imageBase64,
        },
        config,
        { abortSignal: abortController.signal }
      );

      abortControllerRef.current = null;
    },
    [selectedFile]
  );

  const chatScrollAnchorRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (chatScrollAnchorRef.current) {
      chatScrollAnchorRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  return (
    <div className="relative w-full min-h-screen flex flex-col items-center justify-center bg-transparent">
      <ParticlesBackground color={particleColor} />
      <UserGuide />

      {/* 🎨 粒子颜色按钮 + 控制面板 */}
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
        <header className="fixed left-0 right-0 top-0 flex h-16 w-full items-center px-4">
          <AppHeader />
        </header>

        <main className="mb-48 mt-16 px-4">
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
                I am your intelligent agent, I can help you do anything. —— From BUPT
              </div>
            </div>
          )}

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
    </div>
  );
}
