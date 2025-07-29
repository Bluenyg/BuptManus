import Markdown from "react-markdown";
import { type Message } from "~/core/messaging";
import { cn } from "~/core/utils";
import { LoadingAnimation } from "./LoadingAnimation";
import { WorkflowProgressView } from "./WorkflowProgressView";

export function MessageHistoryView({
  className,
  messages,
  loading,
}: {
  className?: string;
  messages: Message[];
  loading?: boolean;
}) {
  return (
    <div className={cn(className)}>
      {messages.map((message) => (
        <MessageView key={message.id} message={message} />
      ))}
      {loading && <LoadingAnimation className="mt-8" />}
    </div>
  );
}

function MessageView({ message }: { message: Message }) {
  console.log("🔍 Rendering message:", message);

  if (message.type === "text" && message.content) {
    return (
      <MessageBubble role={message.role}>
        <Markdown
          components={{
            a: ({ href, children }) => (
              <a href={href} target="_blank" rel="noopener noreferrer">
                {children}
              </a>
            ),
          }}
        >
          {message.content}
        </Markdown>
      </MessageBubble>
    );
  } else if (message.type === "multimodal") {
    // 🔥 关键修复：正确处理多模态消息
    return (
      <MessageBubble role={message.role}>
        <div className="space-y-2">
          {/* 处理存储格式 [{"type": "text", "text": "..."}, {"type": "image_url", "image_url": {"url": "..."}}] */}
          {Array.isArray(message.content) ? (
            // 如果content是数组格式（从数据库加载的格式）
            message.content.map((item: any, index: number) => {
              if (item.type === "text" && item.text) {
                return (
                  <div key={`text-${index}`}>
                    <Markdown>{item.text}</Markdown>
                  </div>
                );
              } else if (item.type === "image_url" && item.image_url?.url) {
                return (
                  <img
                    key={`image-${index}`}
                    src={item.image_url.url}
                    alt={`User uploaded image ${index + 1}`}
                    className="max-w-xs rounded-lg shadow-md border"
                    onError={(e) => {
                      console.error("Failed to load image:", item.image_url.url);
                      e.currentTarget.style.display = 'none';
                    }}
                  />
                );
              }
              return null;
            })
          ) : (
            // 如果content是对象格式（原有的格式）
            <>
              {message.content.text && (
                <div>
                  <Markdown>{message.content.text}</Markdown>
                </div>
              )}
              {message.content.image && (
                <img
                  src={message.content.image}
                  alt="User uploaded image"
                  className="max-w-xs rounded-lg shadow-md border"
                  onError={(e) => {
                    console.error("Failed to load image:", message.content.image);
                    e.currentTarget.style.display = 'none';
                  }}
                />
              )}
            </>
          )}
        </div>
      </MessageBubble>
    );
  } else if (message.type === "workflow") {
    return (
      <WorkflowProgressView
        className="mb-8 max-h-[400px] min-h-[400px] min-w-[928px] max-w-[928px]"
        workflow={message.content.workflow}
      />
    );
  }

  // 兜底处理
  console.warn("Unknown message type or invalid content:", message);
  return (
    <MessageBubble role={message.role}>
      <div className="text-gray-500 italic">
        [无法显示此消息类型]
      </div>
    </MessageBubble>
  );
}

function MessageBubble({
  role,
  children,
}: {
  role: "user" | "assistant";
  children: React.ReactNode;
}) {
  return (
    <div className={cn("flex", role === "user" && "justify-end")}>
      <div
        className={cn(
          "relative mb-8 w-fit max-w-[560px] rounded-2xl px-4 py-3 shadow-sm",
          role === "user" && "rounded-ee-none bg-primary text-white",
          role === "assistant" && "rounded-es-none bg-white text-gray-900 dark:bg-gray-100 dark:text-black"
        )}
      >
        {children}
      </div>
    </div>
  );
}
