import { useState } from 'react';
import { Button } from '@heroui/react';

/** Long absolute paths are the densest thing on this page and the hardest to
 * scan. Two substitutions carry most of the readability: a user's home becomes
 * `~`, and the skills library becomes `库`, so what remains is the part that
 * actually differs between entries. */
export function prettyPath(p: string, libraryRoot = ''): string {
  if (!p) return '';
  let out = p;
  if (libraryRoot && out.startsWith(libraryRoot)) {
    out = '库' + out.slice(libraryRoot.length);
  }
  out = out.replace(/^\/Users\/[^/]+/, '~').replace(/^\/home\/[^/]+/, '~');
  return out;
}

/** Path rendered so the tail — the part that identifies the entry — survives
 * a narrow column, with the full value available on hover and on copy. */
export function PathText({ path, libraryRoot, className = '' }: {
  path: string; libraryRoot?: string; className?: string;
}) {
  if (!path) return <span className="text-foreground/50">—</span>;
  return (
    <span
      title={path}
      className={`break-all font-mono text-xs text-foreground/70 ${className}`}
    >
      {prettyPath(path, libraryRoot)}
    </span>
  );
}

export function CopyButton({ text, label = '复制', size = 'sm' }: {
  text: string; label?: string; size?: 'sm' | 'md';
}) {
  const [done, setDone] = useState(false);
  if (!text) return null;
  return (
    <Button
      size={size}
      variant="ghost"
      onPress={() => {
        navigator.clipboard?.writeText(text).then(() => {
          setDone(true);
          setTimeout(() => setDone(false), 1500);
        });
      }}
    >
      {done ? '已复制' : label}
    </Button>
  );
}

/** A symlinked entry only makes sense as a chain: the entry the tool reads,
 * and the file it actually resolves to. Showing one without the other is what
 * made the old drawer unable to answer "where does this really live". */
export function PathChain({ from, to, libraryRoot }: {
  from: string; to: string; libraryRoot?: string;
}) {
  return (
    <div className="flex flex-col gap-0.5">
      <PathText path={from} libraryRoot={libraryRoot} />
      {to && (
        <div className="flex items-start gap-1.5 pl-3">
          <span className="select-none text-xs text-foreground/50">└→</span>
          <PathText path={to} libraryRoot={libraryRoot} />
        </div>
      )}
    </div>
  );
}
