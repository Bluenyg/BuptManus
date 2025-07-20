import { env } from "~/env";

import { type Message } from "../messaging";
import { fetchStream } from "../sse";

import { type ChatEvent } from "./types";

export function chatStream(
  userMessage: Message,
  state: { messages: Message[] },
  params: { deepThinkingMode: boolean; searchBeforePlanning: boolean },
  options: { abortSignal?: AbortSignal } = {}
) {
  //序列化处理多模态消息
  const serializeMessage = (msg: Message) => {
    if (msg.type === "multimodal") {
      return {
        role: msg.role,
        content: `${msg.content.text}\n\n[image]: ${msg.content.image}`, // ✅ 自定义处理方式
      };
    } else if (msg.type === "text") {
      return {
        role: msg.role,
        content: msg.content,
      };
    } else {
      // 默认 fallback
      return {
        role: msg.role,
        content: JSON.stringify(msg.content),
      };
    }
  };

  return fetchStream<ChatEvent>(env.NEXT_PUBLIC_API_URL + "/chat/stream", {
    body: JSON.stringify({
      messages: [...state.messages, userMessage].map(serializeMessage),
      deep_thinking_mode: params.deepThinkingMode,
      search_before_planning: params.searchBeforePlanning,
      debug:
        location.search.includes("debug") &&
        !location.search.includes("debug=false"),
    }),
    signal: options.abortSignal,
  });
}
