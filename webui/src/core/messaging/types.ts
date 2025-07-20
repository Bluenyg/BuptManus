import { type Workflow } from "../workflow";

export type MessageRole = "user" | "assistant";

interface GenericMessage<
  T extends string,
  C extends Record<string, unknown> | string
> {
  id: string;
  role: MessageRole;
  type: T;
  content: C;
}

// 文本消息
export interface TextMessage extends GenericMessage<"text", string> {}

// 工作流消息
export interface WorkflowMessage
  extends GenericMessage<"workflow", { workflow: Workflow }> {}

// 多模态消息（文本 + 图片Base64）新增
export interface MultimodalMessage
  extends GenericMessage<"multimodal", { text: string; image: string }> {}

// 扩展联合类型
export type Message = TextMessage | WorkflowMessage | MultimodalMessage;
