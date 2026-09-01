import { useState } from 'react';
import { Chip } from '@heroui/react';

/* The canonical explanation of every link state the dashboard reports.
 *
 * These four words (软链/仓库自带/散落实体/断链) appear on three pages, and
 * until now their meaning lived only in hover tooltips — invisible on touch,
 * undiscoverable by mouse, and silent on the question people actually have:
 * "do I need to do anything about this?" (Nielsen #10: help in context.)
 *
 * One source of truth here; the topology legend and any future page render it.
 * The dashboard stays read-only — every action below is a `skill` CLI command
 * for the user to run, per the management policy this project observes. */

export type LinkVerdict = 'ok' | 'attention' | 'fix' | 'env';

export const VERDICT_LABEL: Record<LinkVerdict, string> = {
  ok: '无需处理',
  attention: '建议归置',
  fix: '需要清理',
  env: '挂载即可',
};
export const VERDICT_CLASS: Record<LinkVerdict, string> = {
  ok: 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300',
  attention: 'bg-amber-500/15 text-amber-700 dark:text-amber-300',
  fix: 'bg-red-500/15 text-red-700 dark:text-red-300',
  env: 'bg-foreground/10 text-foreground/60',
};

export type LinkDoc = {
  key: string; label: string; color: string;
  verdict: LinkVerdict;
  what: string;      // 是什么、怎么来的
  action: string;    // 要不要处理、具体怎么做
};

export const LINK_DOC: LinkDoc[] = [
  {
    key: 'symlink', label: '软链', color: 'var(--sh-link-ok)', verdict: 'ok',
    what: '由 skill load 建立的符号链接，指向技能库里的真源。技能本体只有库里一份，'
      + '这里只是个入口。',
    action: '这就是目标状态：改库内真源，所有装了它的工具同时生效。',
  },
  {
    key: 'vendored', label: '仓库自带', color: 'var(--sh-link-vendored)', verdict: 'ok',
    what: '实体目录，但被所在项目的 git 仓库跟踪——不是你装的，是项目作者把技能'
      + '提交进了仓库，克隆时就带着（上游常同时放 .claude/skills 与 .agents/skills '
      + '两份以兼容多个工具）。',
    action: '不用清理、也不必收进库：它属于那个项目，在该仓库 git pull 就会跟着更新。',
  },
  {
    key: 'entity', label: '散落实体', color: '#ec835a', verdict: 'attention',
    what: '独立的目录拷贝：既不是软链、也不随任何仓库分发。通常来自手动复制安装、'
      + '某些安装器直接写入、或纳管之前的历史遗留。风险在于：改了库内真源它不会跟着变，'
      + '同名的几份副本各改各的就漂移了（看板按内容哈希在盯）。',
    action: '建议归置——库里已有同源的：删掉这份副本，需要就 skill load 换成软链；'
      + '库里还没有的：先复制入库，再换软链。',
  },
  {
    key: 'broken', label: '断链', color: '#d03b3b', verdict: 'fix',
    what: '软链还在、指向的目标没了——真源被移动、重命名或退役后，各工具目录里的'
      + '旧链接没跟着清理。判定时已确认目标所在的目录树还在——已排除「NAS 没挂载」'
      + '的情况，是这一条真的失效了。这个工具里该技能实际已经用不了。',
    action: '需要清理：先 skill doctor 复核；不再用的直接删掉该软链，'
      + '还要用的重新 skill load 指到新位置。',
  },
  {
    key: 'unrooted', label: '无法判定', color: 'var(--sh-link-unrooted, #8a8a90)', verdict: 'env',
    what: '软链目标连同它所在的整棵目录树都不可达——几乎总是网络盘（NAS）没挂载，'
      + '而不是技能出了问题。',
    action: '挂载后等下一次上报即可，技能本身什么都不用动。',
  },
];

/** Expandable explainer: a "说明" toggle where the legend lives, so the answer
 * sits next to the question instead of in a hover tooltip nobody finds. */
export function LinkDocPanel({ show = LINK_DOC.map((d) => d.key) }: { show?: string[] }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {LINK_DOC.filter((d) => show.includes(d.key)).map((d) => (
        <div key={d.key} className="rounded-lg border border-foreground/10 p-3">
          <div className="mb-1 flex items-center gap-2">
            <span className="h-2.5 w-5 shrink-0 rounded-sm" style={{ background: d.color }} />
            <span className="text-sm font-medium">{d.label}</span>
            <Chip size="sm" className={VERDICT_CLASS[d.verdict]}>{VERDICT_LABEL[d.verdict]}</Chip>
          </div>
          <p className="text-xs leading-relaxed text-foreground/75">{d.what}</p>
          <p className="mt-1.5 text-xs leading-relaxed">
            <span className="font-medium">怎么办：</span>
            <span className="text-foreground/75">{d.action}</span>
          </p>
        </div>
      ))}
    </div>
  );
}

export function LinkDocToggle() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="rounded-md border border-foreground/15 px-2 py-0.5 text-xs text-foreground/70 transition-colors hover:border-foreground/30 hover:text-foreground"
      >
        {open ? '收起说明' : '这些是什么？'}
      </button>
      {open && (
        <div className="w-full basis-full pt-1">
          <LinkDocPanel />
        </div>
      )}
    </>
  );
}
