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

  // 安全地获取内容
  const safeContent = getSafeContent(message);
  console.log("🔍 Safe content:", safeContent);

  if (message.type === "text") {
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
          {safeContent}
        </Markdown>
      </MessageBubble>
    );
  }

  if (message.type === "multimodal") {
    return (
      <MessageBubble role={message.role}>
        <div className="space-y-3">
          {renderMultimodalContent(message.content)}
        </div>
      </MessageBubble>
    );
  }

  if (message.type === "workflow") {
    return (
      <WorkflowProgressView
        className="mb-8 max-h-[400px] min-h-[400px] min-w-[928px] max-w-[928px]"
        workflow={message.content.workflow}
      />
    );
  }

  // 兜底处理
  return (
    <MessageBubble role={message.role}>
      <div className="text-gray-500 italic">
        {safeContent || "[无法显示此消息]"}
      </div>
    </MessageBubble>
  );
}

// 🔥 关键函数：确保返回安全的字符串内容
function getSafeContent(message: any): string {
  try {
    const content = message.content;

    // 如果已经是字符串，直接返回
    if (typeof content === 'string') {
      return content;
    }

    // 如果是null或undefined
    if (!content) {
      return '';
    }

    // 如果是数组（多模态内容）
    if (Array.isArray(content)) {
      const textParts: string[] = [];
      content.forEach((item: any) => {
        if (item && typeof item === 'object') {
          if (item.type === 'text' && item.text) {
            textParts.push(String(item.text));
          }
        } else if (typeof item === 'string') {
          textParts.push(item);
        }
      });
      return textParts.join(' ');
    }

    // 如果是对象
    if (typeof content === 'object') {
      // 尝试提取text字段
      if (content.text) {
        return String(content.text);
      }
      // 如果有其他可能的文本字段
      if (content.message) {
        return String(content.message);
      }
      if (content.content) {
        return String(content.content);
      }
      // 最后的尝试 - 但不直接返回对象
      return '[复杂内容]';
    }

    // 其他情况，安全转换为字符串
    return String(content);

  } catch (error) {
    console.error("Error getting safe content:", error);
    return '[内容解析错误]';
  }
}

// 🔥 专门处理多模态内容渲染 - 修复版本
function renderMultimodalContent(content: any): React.ReactNode[] {
  const elements: React.ReactNode[] = [];

  try {
    console.log("🖼️ Rendering multimodal content:", content);

    // 处理数组格式
    if (Array.isArray(content)) {
      content.forEach((item: any, index: number) => {
        if (!item) return;

        console.log(`🔍 Processing item ${index}:`, item);

        if (typeof item === 'string') {
          elements.push(
            <div key={`text-${index}`} className="whitespace-pre-wrap">
              <Markdown>{item}</Markdown>
            </div>
          );
        } else if (typeof item === 'object') {
          // 处理文本内容
          if (item.type === "text" && item.text) {
            elements.push(
              <div key={`text-${index}`} className="whitespace-pre-wrap mb-3">
                <Markdown>{String(item.text)}</Markdown>
              </div>
            );
          }

          // 处理图片内容 - 修复版本
          if (item.type === "image_url") {
            const imageUrl = item.image_url?.url;
            if (imageUrl) {
              console.log("🖼️ Found image URL:", imageUrl.substring(0, 50) + "...");
              elements.push(
                <div key={`image-${index}`} className="my-3">
                  <img
                    src={imageUrl}
                    alt={`用户上传的图片 ${index + 1}`}
                    className="max-w-md max-h-96 rounded-lg shadow-md border object-contain"
                    style={{
                      maxWidth: '400px',
                      maxHeight: '300px',
                      width: 'auto',
                      height: 'auto'
                    }}
                    onLoad={(e) => {
                      console.log("✅ Image loaded successfully");
                    }}
                    onError={(e) => {
                      console.error("❌ Failed to load image:", imageUrl.substring(0, 50) + "...");
                      // 显示错误占位符
                      e.currentTarget.outerHTML = `
                        <div class="flex items-center justify-center w-64 h-32 bg-gray-100 border rounded-lg">
                          <span class="text-gray-500 text-sm">图片加载失败</span>
                        </div>
                      `;
                    }}
                  />
                </div>
              );
            } else {
              console.warn("⚠️ Image item found but no URL:", item);
            }
          }
        }
      });
    }
    // 处理对象格式
    else if (content && typeof content === 'object') {
      if (content.text) {
        elements.push(
          <div key="text" className="whitespace-pre-wrap">
            <Markdown>{String(content.text)}</Markdown>
          </div>
        );
      }
      if (content.image_url) {
        elements.push(
          <div key="image" className="my-3">
            <img
              src={String(content.image_url)}
              alt="图片"
              className="max-w-md max-h-96 rounded-lg shadow-md border object-contain"
              onError={(e) => {
                console.error("Failed to load image:", content.image_url);
                e.currentTarget.style.display = 'none';
              }}
            />
          </div>
        );
      }
    }
    // 处理字符串格式
    else if (typeof content === 'string') {
      elements.push(
        <div key="string-content" className="whitespace-pre-wrap">
          <Markdown>{content}</Markdown>
        </div>
      );
    }
  } catch (error) {
    console.error("Error rendering multimodal content:", error, content);
    elements.push(
      <div key="error" className="text-red-500 italic">
        渲染内容时出错
      </div>
    );
  }

  // 确保至少返回一个元素
  if (elements.length === 0) {
    elements.push(
      <div key="empty" className="text-gray-500 italic">
        暂无内容
      </div>
    );
  }

  console.log(`✅ Generated ${elements.length} elements for multimodal content`);
  return elements;
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
