import { ArrowUpOutlined, GlobalOutlined } from "@ant-design/icons";
import { type KeyboardEvent, useCallback, useEffect, useState } from "react";

import { Atom } from "~/core/icons";
import { cn } from "~/core/utils";

export function InputBox({
  className,
  size,
  responding,
  onSend,
  onCancel,
  onUploadClick,
  fileInputRef,
  selectedFile,
  onClearFile,
}: {
  className?: string;
  size?: "large" | "normal";
  responding?: boolean;
  onSend?: (
    message: string,
    options: { deepThinkingMode: boolean; searchBeforePlanning: boolean },
  ) => void;
  onCancel?: () => void;
  onUploadClick?: () => void;
  fileInputRef?: React.RefObject<HTMLInputElement>;
  selectedFile?: File | null;
  onClearFile?: () => void;
}) {
  const [message, setMessage] = useState("");
  const [deepThinkingMode, setDeepThinkMode] = useState(false);
  const [searchBeforePlanning, setSearchBeforePlanning] = useState(false);
  const [imeStatus, setImeStatus] = useState<"active" | "inactive">("inactive");

  const saveConfig = useCallback(() => {
    localStorage.setItem(
      "langmanus.config.inputbox",
      JSON.stringify({ deepThinkingMode, searchBeforePlanning }),
    );
  }, [deepThinkingMode, searchBeforePlanning]);

  useEffect(() => {
    const config = localStorage.getItem("langmanus.config.inputbox");
    if (config) {
      const { deepThinkingMode, searchBeforePlanning } = JSON.parse(config);
      setDeepThinkMode(deepThinkingMode);
      setSearchBeforePlanning(searchBeforePlanning);
    }
  }, []);

  useEffect(() => {
    saveConfig();
  }, [deepThinkingMode, searchBeforePlanning, saveConfig]);

  const handleSendMessage = useCallback(() => {
    if (responding) {
      onCancel?.();
    } else {
      if (message.trim() === "") return;
      onSend?.(message, { deepThinkingMode, searchBeforePlanning });
      setMessage("");
    }
  }, [responding, onCancel, message, onSend, deepThinkingMode, searchBeforePlanning]);

  const handleKeyDown = useCallback(
    (event: KeyboardEvent<HTMLTextAreaElement>) => {
      if (responding) return;
      if (
        event.key === "Enter" &&
        !event.shiftKey &&
        !event.metaKey &&
        !event.ctrlKey &&
        imeStatus === "inactive"
      ) {
        event.preventDefault();
        handleSendMessage();
      }
    },
    [responding, imeStatus, handleSendMessage],
  );

  return (
    <div className={cn(className)}>
      <div className="w-full">
        <textarea
          className={cn(
            "m-0 w-full resize-none border-none px-4 py-3 text-lg",
            "text-gray-900 dark:text-white",
            "placeholder-gray-400 dark:placeholder-gray-500",
            "bg-transparent focus:outline-none",
            size === "large" ? "min-h-32" : "min-h-4"
          )}
          placeholder="What can I do for you?"
          value={message}
          onCompositionStart={() => setImeStatus("active")}
          onCompositionEnd={() => setImeStatus("inactive")}
          onKeyDown={handleKeyDown}
          onChange={(event) => {
            setMessage(event.target.value);
          }}
        />
      </div>

      {/* ✅ 选中文件展示 */}
      {selectedFile && (
        <div className="text-sm text-gray-500 dark:text-gray-300 px-4 pb-1 truncate flex items-center justify-between">
          📎 {selectedFile.name} ({Math.round(selectedFile.size / 1024)} KB)
          <button
            onClick={onClearFile}
            className="ml-2 text-red-400 hover:text-red-600"
            title="移除"
          >
            ×
          </button>
        </div>
      )}

      <div className="flex items-center px-4 py-2">
        <div className="flex flex-grow items-center gap-2">
          <button
            className={cn(
              "flex h-8 items-center gap-2 rounded-2xl border px-4 text-sm transition-shadow hover:shadow",
              deepThinkingMode
                ? "border-primary bg-primary/15 text-primary"
                : "border border-gray-300 text-gray-700 bg-white hover:bg-gray-100 dark:bg-gray-800 dark:text-white dark:border-gray-600 dark:hover:bg-gray-700",
            )}
            onClick={() => {
              setDeepThinkMode(!deepThinkingMode);
            }}
          >
            <Atom className="h-4 w-4" />
            <span>Deep Think</span>
          </button>

          <button
            className={cn(
              "flex h-8 items-center rounded-2xl border px-4 text-sm transition-shadow hover:shadow",
              searchBeforePlanning
                ? "border-primary bg-primary/15 text-primary"
                : "border border-gray-300 text-gray-700 bg-white hover:bg-gray-100 dark:bg-gray-800 dark:text-white dark:border-gray-600 dark:hover:bg-gray-700",
            )}
            onClick={() => {
              setSearchBeforePlanning(!searchBeforePlanning);
            }}
          >
            <GlobalOutlined className="h-6 w-6" />
            <span>Search</span>
          </button>
        </div>

        {/* ✅ 上传 + 发送按钮组 */}
        <div className="flex items-center gap-2">
          <input
            type="file"
            ref={fileInputRef}
            onChange={(e) => fileInputRef?.current?.dispatchEvent(new Event('change', { bubbles: true }))}
            className="hidden"
            accept="image/*"
          />
          <button
            type="button"
            onClick={onUploadClick}
            className="h-10 w-10 rounded-full bg-gray-300 dark:bg-gray-700 text-black dark:text-white hover:bg-gray-400 dark:hover:bg-gray-600 transition"
            title="上传图片"
          >
            +
          </button>

          <button
            className={cn(
              "h-10 w-10 rounded-full text-white transition-shadow hover:shadow",
              responding ? "bg-red-400" : "bg-button hover:bg-button-hover"
            )}
            title={responding ? "Cancel" : "Send"}
            onClick={handleSendMessage}
          >
            {responding ? (
              <div className="flex h-10 w-10 items-center justify-center">
                <div className="h-4 w-4 rounded bg-white" />
              </div>
            ) : (
              <ArrowUpOutlined />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
