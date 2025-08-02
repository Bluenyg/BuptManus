import { DownOutlined, UpOutlined } from "@ant-design/icons";
import { parse } from "best-effort-json-parser";
import { useMemo, useState } from "react";

import { Atom } from "~/core/icons";
import { cn } from "~/core/utils";
import {
  type WorkflowStep,
  type Workflow,
  type ThinkingTask,
} from "~/core/workflow";

import { Markdown } from "./Markdown";
import { ToolCallView } from "./ToolCallView";

export function WorkflowProgressView({
  className,
  workflow,
}: {
  className?: string;
  workflow: Workflow;
}) {
  // 安全检查
  if (!workflow) {
    return (
      <div className={cn("p-4 bg-red-50 border border-red-200 rounded-md", className)}>
        <div className="text-red-600">⚠️ Workflow数据为空</div>
      </div>
    );
  }

  const safeSteps = Array.isArray(workflow.steps) ? workflow.steps : [];

  if (safeSteps.length === 0) {
    return (
      <div className={cn("p-4 bg-yellow-50 border border-yellow-200 rounded-md", className)}>
        <div className="text-yellow-600">📝 暂无工作流步骤</div>
      </div>
    );
  }

  const steps = useMemo(() => {
    return safeSteps.filter((step) => step.agentName !== "reporter");
  }, [safeSteps]);

  const reportStep = useMemo(() => {
    return safeSteps.find((step) => step.agentName === "reporter");
  }, [safeSteps]);

  return (
    <div className="p-4 bg-white text-gray-900 dark:bg-gray-100 dark:text-black rounded-md shadow-md">
      <div className={cn("flex overflow-hidden rounded-2xl border", className)}>
        <aside className="flex w-[220px] flex-shrink-0 flex-col border-r bg-[rgba(0,0,0,0.02)]">
          <div className="flex-shrink-0 px-4 py-4 font-medium">Flow</div>
          <ol className="flex flex-grow list-disc flex-col gap-4 px-4 py-2">
            {/* 🔥 添加了 key */}
            {steps.map((step, index) => (
              <li
                key={`step-nav-${step.id || index}`}
                className="flex cursor-pointer items-center gap-2"
                onClick={() => {
                  const element = document.getElementById(step.id);
                  if (element) {
                    element.scrollIntoView({
                      behavior: "smooth",
                      block: "center",
                    });
                  }
                }}
              >
                <div className="flex h-2 w-2 rounded-full bg-gray-400"></div>
                <div>{getStepName(step)}</div>
              </li>
            ))}
          </ol>
        </aside>
        <main className="flex-grow overflow-auto bg-white p-4">
          <ul className="flex flex-col gap-4">
            {/* 🔥 添加了 key */}
            {steps.map((step, stepIndex) => (
              <li key={`step-main-${step.id || stepIndex}`} className="flex flex-col gap-2">
                <h3 id={step.id} className="ml-[-4px] text-lg font-bold">
                  Step {stepIndex + 1}: {getStepName(step)}
                </h3>
                <ul className="flex flex-col gap-2">
                  {/* 🔥 添加了 key，并确保 tasks 数组存在 */}
                  {(step.tasks || [])
                    .filter(
                      (task) =>
                        !(
                          task.type === "thinking" &&
                          !task.payload?.text &&
                          !task.payload?.reason
                        ),
                    )
                    .map((task, taskIndex) =>
                      task.type === "thinking" &&
                      step.agentName === "planner" ? (
                        <PlanTaskView
                          key={`plan-task-${task.id || `${stepIndex}-${taskIndex}`}`}
                          task={task}
                        />
                      ) : (
                        <li key={`task-${task.id || `${stepIndex}-${taskIndex}`}`} className="flex">
                          {task.type === "thinking" ? (
                            <Markdown
                              className="pl-6 opacity-70"
                              style={{
                                fontSize: "smaller",
                              }}
                            >
                              {task.payload?.text || ""}
                            </Markdown>
                          ) : (
                            <ToolCallView task={task} />
                          )}
                        </li>
                      ),
                    )}
                </ul>
                {/* 🔥 添加条件检查避免最后一个元素显示分隔线 */}
                {stepIndex < steps.length - 1 && <hr className="mb-4 mt-8" />}
              </li>
            ))}
          </ul>
        </main>
      </div>
      {/* 🔥 添加安全检查 */}
      {reportStep && reportStep.tasks && reportStep.tasks.length > 0 && (
        <div className="flex flex-col gap-4 p-4">
          <Markdown>
            {reportStep.tasks[0]?.type === "thinking"
              ? reportStep.tasks[0].payload?.text || ""
              : ""}
          </Markdown>
        </div>
      )}
    </div>
  );
}

function PlanTaskView({ task }: { task: ThinkingTask }) {
  const plan = useMemo<{
    title?: string;
    steps?: { title?: string; description?: string }[];
  }>(() => {
    if (!task.payload?.text) {
      return {};
    }

    try {
      const text = task.payload.text.trim();

      // 如果文本为空，返回空对象
      if (!text) {
        return {};
      }

      // 尝试找到JSON部分
      const jsonMatch = text.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        const jsonStr = jsonMatch[0];
        try {
          // 先尝试使用标准JSON解析
          return JSON.parse(jsonStr);
        } catch (standardError) {
          // 如果标准解析失败，使用best-effort-json-parser
          console.warn("Standard JSON parse failed, using best-effort parser:", standardError);
          return parse(jsonStr);
        }
      }

      // 如果没找到JSON格式，尝试直接解析整个文本
      try {
        return JSON.parse(text);
      } catch (directError) {
        console.warn("Direct JSON parse failed, using best-effort parser:", directError);
        return parse(text);
      }

    } catch (error) {
      // 静默处理错误，不在控制台显示
      console.warn("Failed to parse plan text, returning empty object:", {
        error: error.message,
        text: task.payload?.text?.substring(0, 100) + "..." // 只显示前100个字符用于调试
      });
      return {};
    }
  }, [task.payload?.text]);

  const [showReason, setShowReason] = useState(true);
  const reason = task.payload?.reason;

  // 安全地构建 markdown，处理可能为空的字段
  const markdown = useMemo(() => {
    const title = plan.title || "Planning";
    const steps = Array.isArray(plan.steps) ? plan.steps : [];

    if (steps.length === 0) {
      return `## ${title}\n\n_No steps available_`;
    }

    const stepsMarkdown = steps
      .map((step, index) => {
        const stepTitle = step?.title || `Step ${index + 1}`;
        const stepDescription = step?.description || "";
        return `- **${stepTitle}**\n\n${stepDescription}`;
      })
      .join("\n\n");

    return `## ${title}\n\n${stepsMarkdown}`;
  }, [plan]);

  return (
    <li className="flex flex-col">
      {reason && (
        <div>
          <div>
            <button
              className="mb-1 flex h-8 items-center gap-2 rounded-2xl border bg-button px-4 text-sm text-button hover:bg-button-hover hover:text-button-hover"
              onClick={() => setShowReason(!showReason)}
            >
              <Atom className="h-4 w-4" />
              <span>Deep Thought</span>
              {showReason ? (
                <UpOutlined className="text-xs" />
              ) : (
                <DownOutlined className="text-xs" />
              )}
            </button>
          </div>
          <div className={cn(showReason ? "block" : "hidden")}>
            <Markdown className="border-l-2 pl-6 text-sm opacity-70">
              {reason}
            </Markdown>
          </div>
        </div>
      )}
      <div>
        <Markdown className="pl-6">{markdown}</Markdown>
      </div>
    </li>
  );
}

function getStepName(step: WorkflowStep) {
  switch (step.agentName) {
    case "browser":
      return "Browsing Web";
    case "coder":
      return "Coding";
    case "file_manager":
      return "File Management";
    case "planner":
      return "Planning";
    case "researcher":
      return "Researching";
    case "supervisor":
      return "Thinking";
    default:
      return step.agentName || "Unknown";
  }
}
