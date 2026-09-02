import { agentLabel, isSharedDir } from '../lib/api';
import amp from '@lobehub/icons-static-svg/icons/amp-color.svg';
import antigravity from '@lobehub/icons-static-svg/icons/antigravity-color.svg';
import claudeCode from '@lobehub/icons-static-svg/icons/claudecode-color.svg';
import cline from '@lobehub/icons-static-svg/icons/cline.svg';
import codebuddy from '@lobehub/icons-static-svg/icons/codebuddy-color.svg';
import codex from '@lobehub/icons-static-svg/icons/codex-color.svg';
import copilot from '@lobehub/icons-static-svg/icons/copilot-color.svg';
import cursor from '@lobehub/icons-static-svg/icons/cursor.svg';
import deepseek from '@lobehub/icons-static-svg/icons/deepseek-color.svg';
import geminiCli from '@lobehub/icons-static-svg/icons/geminicli-color.svg';
import goose from '@lobehub/icons-static-svg/icons/goose.svg';
import hermes from '@lobehub/icons-static-svg/icons/hermesagent.svg';
import junie from '@lobehub/icons-static-svg/icons/junie-color.svg';
import kilo from '@lobehub/icons-static-svg/icons/kilocode.svg';
import kimi from '@lobehub/icons-static-svg/icons/kimi-color.svg';
import kiro from '@lobehub/icons-static-svg/icons/kiro-color.svg';
import mcp from '@lobehub/icons-static-svg/icons/mcp.svg';
import mistral from '@lobehub/icons-static-svg/icons/mistral-color.svg';
import openclaw from '@lobehub/icons-static-svg/icons/openclaw-color.svg';
import opencode from '@lobehub/icons-static-svg/icons/opencode.svg';
import openhands from '@lobehub/icons-static-svg/icons/openhands-color.svg';
import qoder from '@lobehub/icons-static-svg/icons/qoder-color.svg';
import qwen from '@lobehub/icons-static-svg/icons/qwen-color.svg';
import roo from '@lobehub/icons-static-svg/icons/roocode.svg';
import trae from '@lobehub/icons-static-svg/icons/trae-color.svg';
import windsurf from '@lobehub/icons-static-svg/icons/windsurf.svg';
import zencoder from '@lobehub/icons-static-svg/icons/zencoder-color.svg';

/* Brand marks for the tools the reporter knows (keys mirror
 * reporter/adapters/tool_table.py). Logos come from lobehub's MIT icon set —
 * the same source qufei1993/skills-hub uses — so a tool reads at a glance
 * instead of by parsing a coloured word. Tools the set has no mark for fall
 * back to two initials on a neutral tile; a shared directory gets a folder
 * glyph, because it is not a tool. */
const LOGO: Record<string, string> = {
  'amp': amp, 'antigravity': antigravity, 'claude-code': claudeCode, 'cline': cline,
  'codebuddy': codebuddy, 'codex': codex, 'github-copilot': copilot, 'cursor': cursor,
  'deepseek-harness': deepseek, 'gemini-cli': geminiCli, 'goose': goose,
  'hermes-agent': hermes, 'junie': junie, 'kilo-code': kilo, 'kimi-cli': kimi,
  'kiro-cli': kiro, 'mcpjam': mcp, 'mistral-vibe': mistral,
  'openclaw': openclaw, 'clawdbot': openclaw, 'moltbot': openclaw,
  'opencode': opencode, 'openhands': openhands, 'qoder': qoder, 'qoderwork': qoder,
  'qwen-code': qwen, 'roo-code': roo, 'trae': trae, 'trae-cn': trae,
  'windsurf': windsurf, 'zencoder': zencoder,
};

function initials(label: string): string {
  return label.split(/[\s_-]+/).filter(Boolean).map((p) => p[0]).join('')
    .slice(0, 2).toUpperCase();
}

export function toolLogo(agent: string): string | undefined {
  return LOGO[agent];
}

export function ToolIcon({ agent, size = 16, className = '' }: {
  agent: string; size?: number; className?: string;
}) {
  const px = { width: size, height: size };
  if (isSharedDir(agent)) {
    return (
      <span aria-hidden className={`inline-flex shrink-0 items-center justify-center ${className}`} style={px}>
        <svg viewBox="0 0 16 16" width={size} height={size} className="fill-none stroke-current" strokeWidth={1.4}>
          <path d="M1.5 4.5a1 1 0 0 1 1-1h3l1.5 1.5h6.5a1 1 0 0 1 1 1v6.5a1 1 0 0 1-1 1h-11a1 1 0 0 1-1-1z" />
        </svg>
      </span>
    );
  }
  const logo = LOGO[agent];
  if (logo) {
    return <img src={logo} alt="" draggable={false} aria-hidden style={px}
                className={`shrink-0 rounded-sm ${className}`} />;
  }
  return (
    <span aria-hidden
          className={`inline-flex shrink-0 items-center justify-center rounded-sm bg-foreground/10 font-semibold leading-none ${className}`}
          style={{ ...px, fontSize: Math.max(8, Math.round(size * 0.5)) }}>
      {initials(agentLabel(agent))}
    </span>
  );
}
