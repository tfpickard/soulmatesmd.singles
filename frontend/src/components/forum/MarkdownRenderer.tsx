import ReactMarkdown from 'react-markdown';

interface Props {
  content: string;
  className?: string;
}

export function MarkdownRenderer({ content, className }: Props) {
  return (
    <div className={`forum-markdown ${className ?? ''}`}>
      <ReactMarkdown
        components={{
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noopener noreferrer" className="text-coral underline-offset-2 hover:underline">
              {children}
            </a>
          ),
          code: ({ children, className: cls }) => {
            const isBlock = cls?.includes('language-');
            return isBlock ? (
              <pre className="my-2 overflow-x-auto rounded-xl bg-black/30 px-4 py-3 font-mono text-sm text-stone-200">
                <code>{children}</code>
              </pre>
            ) : (
              <code className="rounded bg-black/30 px-1.5 py-0.5 font-mono text-xs text-coral">{children}</code>
            );
          },
          blockquote: ({ children }) => (
            <blockquote className="my-2 border-l-2 border-coral/40 pl-4 text-stone-300 italic">{children}</blockquote>
          ),
          h1: ({ children }) => <h1 className="mb-2 mt-4 font-display text-2xl text-paper">{children}</h1>,
          h2: ({ children }) => <h2 className="mb-1.5 mt-3 font-display text-xl text-paper">{children}</h2>,
          h3: ({ children }) => <h3 className="mb-1 mt-2 font-semibold text-paper">{children}</h3>,
          ul: ({ children }) => <ul className="my-2 list-disc space-y-1 pl-5 text-stone-200">{children}</ul>,
          ol: ({ children }) => <ol className="my-2 list-decimal space-y-1 pl-5 text-stone-200">{children}</ol>,
          p: ({ children }) => <p className="my-1.5 leading-relaxed">{children}</p>,
          hr: () => <hr className="my-3 border-white/10" />,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
