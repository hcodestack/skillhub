# Changelog

Notable changes to Skillmgmnt. This project does not tag releases yet, so
entries are grouped by date. Format follows [Keep a Changelog][kac].

[kac]: https://keepachangelog.com/en/1.1.0/

---

## 2026-09-18

### Changed

- **The repository moved to [`hcodestack/skillmgmnt`][repo]**, and the product
  is now called **Skillmgmnt**. It was `hcodestack/skillhub` and *Skillhub*.

  GitHub redirects the old name, so nothing is broken: the web page, `raw`
  URLs, tarballs and `git clone` all still resolve, and an existing clone keeps
  pulling. You do not need to do anything. To update a remote anyway:

  ```bash
  git remote set-url origin https://github.com/hcodestack/skillmgmnt.git
  ```

  The redirect lasts only while nobody creates a new repository under the old
  name, which is why the canonical URLs here were updated.

- **Some things deliberately kept the old name**, and should not be "fixed":
  the `skillhub_server` Python package, the `~/.skillhub` config directory,
  `skillhub.db`, the `skillhub` CLI, the launchd and systemd unit names, the
  Docker image, container and volume names, and the MCP registration name.
  Renaming any of them would orphan an existing install's configuration or its
  database in exchange for nothing a user can see.

### Deprecated

- **`SKILLHUB_*` environment variables are now `SKILLMGMNT_*`.** The old prefix
  still works. Every variable is read as `SKILLMGMNT_<name>` first and falls
  back to `SKILLHUB_<name>`, in the server and in the `skillhub` shell
  launcher, so existing compose files, unit files and shell profiles keep
  working untouched.

  The server prints one line at startup naming any old variable it is still
  reading. The fallback will be removed, but only in an entry that says it is
  being removed.

### Added

- **Skills served over MCP are now discovered and reported.** [SEP-2640][sep]
  made the Skills extension part of MCP on 2026-09-13. A skill served that way
  is never installed — the extension requires hosts to cache what they fetch
  outside every skill-discovery path — so a filesystem scanner cannot see it,
  and the dashboard would otherwise report a confident number while an agent
  ran skills it had no idea existed.

  A new **MCP** tab reads which servers each tool is configured to reach, asks
  the ones it can, and shows what they serve and what they cost in resident
  context. Only `initialize` and `skills/list` are ever sent, both read-only.
  Credentials in your MCP config are never read, stdio servers are never
  started, and loopback endpoints are never probed.

  Five governance findings come from reconciling the served view against the
  filesystem one: name collisions with a local skill, entries that cannot be
  content-bound, skills over the protocol's 512-file / 16 MiB limits,
  frontmatter requesting wider permissions, and servers configured but
  unreachable.

- **A references section** in both READMEs, citing the Skills extension sources
  and crediting the prior art this project builds on — [qufei1993/skills-hub][sh]
  for the tool directory table, the `SKILL.md` validity check and the
  content-hash approach, and [lobehub][lh] for the tool brand marks. Both are
  MIT and neither had been acknowledged.

### Fixed

- **Docker installs produced an empty catalog.** `deploy/Dockerfile` set
  `SKILLHUB_LIBRARY_INDEX`, overriding the unset default that means "scan the
  library directly". Every container therefore failed with *index not readable*
  unless the user happened to maintain an index file. The variable is gone and
  `SKILLMGMNT_LIBRARY_ROOT` is set instead.
- **A skill's library path was wrong for most layouts.** It was built by
  assuming one hardcoded folder name instead of resolving through the
  configured library bases, so the path shown in the drawer, the copy button
  and the evaluation prompt was wrong for anyone not using that one layout.

---

## 2026-09-02

### Added

- **Initial public release.** Read-only observability for AI-agent skills: a
  searchable catalog, a load topology across 47+ tools, usage parsed from the
  tools' own session logs, governance findings, a deterministic safety review,
  upstream update tracking, and a read-only MCP surface.
- **Bilingual interface, English by default.** The dashboard opens in English
  and switches to Simplified Chinese from the header, including the text the
  server composes — health findings, the exported governance report and the
  remediation script. Wording lives in one catalog per side with both strings
  in each entry, so a translation cannot drift from what it translates.
- **Tag filter** over domain tags, with per-tag counts and an explicit
  *untagged* row.
- **Cards view** on the overview, alongside the table.
- **Tool brand marks** in agent chips and on the hosts page.
- **Tab counts** on Health and Updates, taken from data the overview already
  fetches.

### Changed

- **The hosts page became a tools view**: each detected tool as a card with the
  directory it reads its global skills from and the projects it is loaded into,
  with undetected tools folded away.
- **Mutually exclusive views use segmented controls** rather than switches, and
  the theme control gained a *System* state that follows the OS live. The old
  switch could never return to following the OS once touched.
- **The remediation script no longer deletes a stray copy.** It moves it to a
  dated trash directory and relinks, so a wrong call is an undo rather than a
  loss. Override the location with `SKILLMGMNT_TRASH`.

[repo]: https://github.com/hcodestack/skillmgmnt
[sep]: https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2640
[sh]: https://github.com/qufei1993/skills-hub
[lh]: https://github.com/lobehub/lobe-icons
