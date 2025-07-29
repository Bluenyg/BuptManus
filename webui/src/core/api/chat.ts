import { env } from "~/env";
import { type Message } from "../messaging";
import { fetchStream } from "../sse";
import { type ChatEvent } from "./types";

export function chatStream(
  userMessage: Message,
  state: { messages: Message[] },
  params: {
    deepThinkingMode: boolean;
    searchBeforePlanning: boolean;
    conversationId?: string;
  },
  options: { abortSignal?: AbortSignal } = {}
) {
  // 🔥 修复：正确序列化多模态消息
  const serializeMessage = (msg: Message) => {
    if (msg.type === "multimodal") {
      // 根据你的存储格式 [{"type": "text", "text": "..."}, {"type": "image_url", "image_url": {"url": "..."}}]
      // 构建正确的多模态格式
      const content = [];

      // 添加文本内容
      if (msg.content.text) {
        content.push({
          type: "text",
          text: msg.content.text
        });
      }

      // 添加图片内容
      if (msg.content.image) {
        content.push({
          type: "image_url",
          image_url: {
            url: msg.content.image
          }
        });
      }

      return {
        role: msg.role,
        content: content // 直接发送数组格式
      };
    } else if (msg.type === "text") {
      return {
        role: msg.role,
        content: msg.content,
      };
    } else if (msg.type === "workflow") {
      // 工作流消息通常不需要发送到后端
      return null;
    } else {
      return {
        role: msg.role,
        content: JSON.stringify(msg.content),
      };
    }
  };

  // 过滤掉 null 值
  const serializedMessages = [...state.messages, userMessage]
    .map(serializeMessage)
    .filter(msg => msg !== null);

  const requestBody: any = {
    messages: serializedMessages,
    deep_thinking_mode: params.deepThinkingMode,
    search_before_planning: params.searchBeforePlanning,
    debug:
      typeof window !== 'undefined' &&
      location.search.includes("debug") &&
      !location.search.includes("debug=false"),
  };

  if (params.conversationId) {
    requestBody.conversationId = params.conversationId;
    console.log("🔥 Sending message to existing session:", params.conversationId);
  } else {
    console.log("🔥 No conversationId provided, will create new session");
  }

  console.log("🔥 Request body:", requestBody);

  return fetchStream<ChatEvent>(env.NEXT_PUBLIC_API_URL + "/chat/stream", {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(requestBody),
    signal: options.abortSignal,
  });
}
