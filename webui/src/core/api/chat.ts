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
    conversationId?: string; // 新增会话ID参数
  },
  options: { abortSignal?: AbortSignal } = {}
) {
  //序列化处理多模态消息
  const serializeMessage = (msg: Message) => {
    if (msg.type === "multimodal") {
      return {
        role: msg.role,
        content: `${msg.content.text}\n\n[image]: ${msg.content.image}`,
      };
    } else if (msg.type === "text") {
      return {
        role: msg.role,
        content: msg.content,
      };
    } else {
      return {
        role: msg.role,
        content: JSON.stringify(msg.content),
      };
    }
  };

  // 构建请求体
  const requestBody: any = {
    messages: [...state.messages, userMessage].map(serializeMessage),
    deep_thinking_mode: params.deepThinkingMode,
    search_before_planning: params.searchBeforePlanning,
    debug:
      location.search.includes("debug") &&
      !location.search.includes("debug=false"),
  };

  // 如果有会话ID，添加到请求体中
  if (params.conversationId) {
    requestBody.conversation_id = params.conversationId;
  }

  return fetchStream<ChatEvent>(env.NEXT_PUBLIC_API_URL + "/chat/stream", {
    body: JSON.stringify(requestBody),
    signal: options.abortSignal,
  });
}
