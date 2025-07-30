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


// 扩展联合类型
export type Message = TextMessage | WorkflowMessage | MultimodalMessage;

export interface MultimodalContent {
  text?: string;
  image?: string;
}

export interface MultimodalContentItem {
  type: "text" | "image_url";
  text?: string;
  image_url?: {
    url: string;
  };
}

// 多模态消息可以支持两种格式
export interface MultimodalMessage
  extends GenericMessage<
    "multimodal",
    MultimodalContent | MultimodalContentItem[] | string
  > {}