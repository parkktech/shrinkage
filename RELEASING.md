# Releasing & versioning (for humans and AI agents)

The single source of truth for "what version is this" and "what changed" is
**`.claude-plugin/plugin.json` (`version`)** + **`CHANGELOG.md`**, backed by a
matching **git tag**. Claude Code reads `plugin.json` `version` to decide when
users get an update, so the version field is what actually ships — the tag is
for humans browsing the repo.

## Every release MUST do all five, in order

Skipping any one is the usual cause of "the repo/tags don't show the new
version." Do them together, every time:

1. **Bump** `.claude-plugin/plugin.json` `"version"` (semver).
2. **Add a `CHANGELOG.md` entry** at the top for that version.
3. **Commit** with the message starting `vX.Y.Z: <summary>`.
4. **Tag**: `git tag vX.Y.Z` on that commit.
5. **Push commit AND tag**: `git push origin main --tags`.

A commit without a tag, or a tag never pushed, leaves the repo looking stale
even though the code landed. `--tags` is not optional.

## Verify it actually landed

```bash
git ls-remote --tags origin        # the new vX.Y.Z is listed
git ls-remote origin HEAD          # HEAD == the release commit
git show HEAD:.claude-plugin/plugin.json | grep version   # matches the tag
```

## Tags vs GitHub Releases (why a tag can "not show")

GitHub's repo homepage sidebar shows **Releases**, which are a *separate*
concept from **git tags**. This project pushes tags; it does not auto-create
Releases (that needs the `gh` CLI or the API, which the CI token lacks). So:

- **Tags** are at `github.com/parkktech/shrinkage/tags` — all versions appear here.
- **Releases** (the sidebar box) stay empty unless someone promotes a tag to a
  Release in the GitHub UI (Releases → Draft a new release → pick the tag).

If the homepage looks like nothing shipped, check the **Tags** page, not the
Releases box — or promote the latest tag to a Release for visibility.

## Never force-push this repo

Force-pushing rewrites commit SHAs and breaks every client's cached plugin
clone (Claude Code pins the install to a SHA), turning a normal update into a
stuck-cache reinstall. Always fast-forward. If history ever must change, tell
users to run `/srk-update` (which clears the cache) and then reinstall.

## How users get the new version

`/plugin marketplace update parkktech` refreshes the catalog but leaves the
installed copy pinned — and `/plugin update` / `/reload-plugins` do NOT clear
Claude Code's on-disk plugin cache (upstream bug: issues #14061, #16866,
#29074). A TUI-only uninstall/reinstall therefore often re-loads the SAME stale
version. The reliable reset (Linux client with shell) deletes the cache:

    # 1. Quit Claude Code completely (commands load only at process startup)
    rm -rf ~/.claude/plugins/marketplaces/parkktech ~/.claude/plugins/cache/parkktech
    # 2. Relaunch, then in Claude Code:
    #      /plugin marketplace add parkktech/shrinkage
    #      /plugin install shrinkage@parkktech
    # 3. Quit and relaunch once more, then /srk to confirm.

For the `srk`→`shrinkage` rename, `marketplace.json` carries a top-level
`renames` map so Claude Code v2.1.193+ auto-migrates a stale `srk@parkktech`
enabled entry to `shrinkage@parkktech`. Older clients clear the dead entry via
`/plugin` → Errors → Enter to resolve.

## Version history

See `CHANGELOG.md`. Tags exist for every release from v0.6.0 onward
(v0.5.0 predates tagging and was the initial skill).
