# Changelog

What changed in each release, so anyone pinned to a tag can tell whether a bump is safe.

This project is in beta. The version lives in `[project].version` in the root `pyproject.toml`, and
that is what gets tagged: merging to `main` tags exactly the number the file declares and cuts a
GitHub release for it. A merge that did not bump the version publishes nothing, so the bump is the
release decision and it belongs in the pull request that earns it.

To ship a change: bump `[project].version`, run `uv lock` so the lockfile records the same number,
and add a heading here for it with your bullets underneath. CI fails a pull request whose changelog
has no heading for the version being released. For a change with no user-visible effect, apply the
`skip-changelog` label instead of inventing a version for it.

The format is deliberately plain: one flat list of bullets per release, no Added / Changed / Fixed
subsections. Say what changed and why someone consuming this component would care.

Releases before this file was added are described in the
[GitHub releases](https://github.com/datarobot-community/af-component-evaluation/releases).

## 11.10.31 - 2026-08-19
- Upgraded the shared `datarobot-oss/github-actions` workflows from `0.0.18` to `0.0.24`. The backport
  workflow now refuses a pull request whose head branch lives in a fork and stops inheriting the
  repository's default token permissions, which matters because it runs on `pull_request_target` with
  write access and secrets. The Slack team mention and the digest's status icons moved out of the
  shared workflows and into this repo's own caller, where they are visible and editable.
- Releases are now cut from `[project].version` in `pyproject.toml` rather than by incrementing the
  latest tag. The tag, the declared version, and the lockfile now agree by construction. Previously
  the declared version sat at `0.1.0` from the initial commit while releases ran to `11.10.30`,
  because nothing read the file and nothing checked it.
- Added this changelog and a pull-request check requiring every change to file an entry under the
  version it releases. Waivable with a `skip-changelog` label, and skipped for bot-authored pull
  requests, since Dependabot can neither edit a changelog nor bump the version.
