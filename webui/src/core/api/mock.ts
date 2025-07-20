import { nanoid } from "nanoid";

import { type Message } from "../messaging";
import { timeout } from "../utils";

import { type ChatEvent } from "./types";

export async function* mockChatStream(_userMessage: Message): AsyncIterable<ChatEvent> {
  console.log("Forcing a simple fake AI response in mockChatStream (triggered by ?mock).");

  await timeout(1500);

  const agentId = nanoid() + "_mock_agent_1";

  yield {
    type: "start_of_agent",
    data: { agent_name: "mock-ai", agent_id: agentId } // ✅ 这个类型是合法的！
  };

  const fakeReplyContent = "这是一条假回复，因为我还没有连接后端，所以你先凑合一下";

  for (const char of fakeReplyContent) {
    yield {
      type: "message",
      data: {
        message_id: nanoid(),
        delta: { content: char }
      }
    };
    await timeout(50);
  }

  yield {
    type: "end_of_llm",
    data: { agent_name: "mock-ai" }
  };

  yield {
    type: "end_of_agent",
    data: { agent_id: agentId } // ✅ 修复重点：移除 agent_name
  };
}
