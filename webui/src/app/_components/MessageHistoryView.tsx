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
      <div className="h-12" />
    </div>
  );
}

function MessageView({ message }: { message: Message }) {
  const safeContent = getSafeContent(message);

  if (message.type === "text") {
    return (
      <MessageBubble role={message.role}>
        <div className="prose prose-sm max-w-none leading-relaxed dark:prose-invert">
          <Markdown
            components={{
              a: ({ href, children }) => (
                <a
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 underline"
                >
                  {children}
                </a>
              ),
            }}
          >
            {safeContent}
          </Markdown>
        </div>
      </MessageBubble>
    );
  }

  if (message.type === "multimodal") {
    return (
      <MessageBubble role={message.role}>
        <div className="space-y-3">{renderMultimodalContent(message.content)}</div>
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

  return (
    <MessageBubble role={message.role}>
      <div className="text-gray-500 italic">{safeContent || "[Unable to display this message]"}</div>
    </MessageBubble>
  );
}

function getSafeContent(message: any): string {
  try {
    const content = message.content;
    if (typeof content === "string") return content;
    if (!content) return "";
    if (Array.isArray(content)) {
      const textParts: string[] = [];
      content.forEach((item: any) => {
        if (item && typeof item === "object" && item.type === "text" && item.text) {
          textParts.push(String(item.text));
        } else if (typeof item === "string") {
          textParts.push(item);
        }
      });
      return textParts.join(" ");
    }
    if (typeof content === "object") {
      if (content.text) return String(content.text);
      if (content.message) return String(content.message);
      if (content.content) return String(content.content);
      return "[Complex content]";
    }
    return String(content);
  } catch (error) {
    console.error("Error extracting content:", error);
    return "[Parsing error]";
  }
}

function renderMultimodalContent(content: any): React.ReactNode[] {
  const elements: React.ReactNode[] = [];
  try {
    if (Array.isArray(content)) {
      content.forEach((item: any, index: number) => {
        if (!item) return;

        if (typeof item === "string") {
          elements.push(
            <div key={`text-${index}`} className="whitespace-pre-wrap">
              <div className="prose prose-sm max-w-none dark:prose-invert">
                <Markdown>{item}</Markdown>
              </div>
            </div>
          );
        } else if (typeof item === "object") {
          if (item.type === "text" && item.text) {
            elements.push(
              <div key={`text-${index}`} className="whitespace-pre-wrap mb-3">
                <div className="prose prose-sm max-w-none dark:prose-invert">
                  <Markdown>{String(item.text)}</Markdown>
                </div>
              </div>
            );
          }
          if (item.type === "image_url") {
            const imageUrl = item.image_url?.url;
            if (imageUrl) {
              elements.push(
                <div key={`image-${index}`} className="my-3">
                  <img
                    src={imageUrl}
                    alt={`Image ${index + 1}`}
                    className="max-w-md max-h-96 rounded-lg shadow-md border object-contain"
                    style={{
                      maxWidth: "400px",
                      maxHeight: "300px",
                      width: "auto",
                      height: "auto",
                    }}
                    onError={(e) => {
                      console.error("Failed to load image:", imageUrl);
                      e.currentTarget.outerHTML = `
                        <div class="flex items-center justify-center w-64 h-32 bg-gray-100 border rounded-lg">
                          <span class="text-gray-500 text-sm">Failed to load image</span>
                        </div>
                      `;
                    }}
                  />
                </div>
              );
            }
          }
        }
      });
    } else if (typeof content === "object") {
      if (content.text) {
        elements.push(
          <div key="text" className="whitespace-pre-wrap">
            <div className="prose prose-sm max-w-none dark:prose-invert">
              <Markdown>{String(content.text)}</Markdown>
            </div>
          </div>
        );
      }
      if (content.image_url) {
        elements.push(
          <div key="image" className="my-3">
            <img
              src={String(content.image_url)}
              alt="Image"
              className="max-w-md max-h-96 rounded-lg shadow-md border object-contain"
              onError={(e) => {
                console.error("Failed to load image:", content.image_url);
                e.currentTarget.style.display = "none";
              }}
            />
          </div>
        );
      }
    } else if (typeof content === "string") {
      elements.push(
        <div key="string-content" className="whitespace-pre-wrap">
          <div className="prose prose-sm max-w-none dark:prose-invert">
            <Markdown>{content}</Markdown>
          </div>
        </div>
      );
    }
  } catch (error) {
    console.error("Multimodal render error:", error, content);
    elements.push(
      <div key="error" className="text-red-500 italic">
        Error rendering content
      </div>
    );
  }

  if (elements.length === 0) {
    elements.push(
      <div key="empty" className="text-gray-500 italic">
        No content
      </div>
    );
  }

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
          "relative mb-8 w-fit max-w-[640px] px-5 py-4 transition-all duration-200",
          role === "user" &&
            "ml-auto bg-blue-500 text-white rounded-xl rounded-ee-none shadow",
          role === "assistant" &&
            "bg-white text-black border border-gray-200 rounded-xl rounded-es-3xl shadow-md"
        )}
      >
        {children}
      </div>
    </div>
  );
}
