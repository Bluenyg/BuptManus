import ReactMarkdown, { type Options } from "react-markdown";

import { cn } from "~/core/utils";

export function Markdown({
  className,
  children,
  style,
  ...props
}: Options & { className?: string; style?: React.CSSProperties }) {
  return (
    <div className={cn(className, "markdown")} style={style}>
      <ReactMarkdown
        components={{
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noopener noreferrer">
              {children}
            </a>
          ),
        }}
        {...props}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
