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
    return (
      <MessageBubble role={message.role}>
        <div className="space-y-2">
          {/* 显示文字 */}
          <Markdown>{message.content.text}</Markdown>
          {/* 显示图片 */}
          <img
            src={message.content.image}
            alt="用户上传图像"
            className="max-w-xs rounded-lg shadow-md border"
          />
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

  return null;
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
          role === "assistant" && "rounded-es-none bg-white"
        )}
      >
        {children}
      </div>
    </div>
  );
}
