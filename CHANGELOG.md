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

## 11.10.40 - 2026-09-02
- Raise the minimum `pypdf` version from `>=6.15.0` to `>=6.16.1`.
- Raise the minimum `tornado` version from `>=6.5.7` to `>=6.5.8`.
- Raise the minimum `transformers` version from `>=5.5.0` to `>=5.10.0`.

## 11.10.39 - 2026-09-02
- Add a minimum version for `hydra-core`: `>=1.3.4`.

## 11.10.38 - 2026-09-01
- Raise the minimum `nltk` version from `>=3.10.2` to `>=3.10.3`.

## 11.10.37 - 2026-09-01
- Move the cve-sync workflow onto the shared reusable workflows in
  `datarobot-oss/cve-sync`, so a fix to the automation reaches this repo on its next
  scheduled run instead of needing a pull request here.
- `.taskfiles/cve-sync.yml` is now generated from upstream and refreshed automatically,
  so it can no longer drift. Do not edit it by hand.

## 11.10.36 - 2026-08-31
- Raise the `nltk` floor from `>=3.10.0` to `>=3.10.2`.
- Regenerate `template/*/uv.lock` from the updated template so a rendered component picks the new
  minimums up.

## 11.10.35 - 2026-08-28
- Re-sync cve-sync and remove dependencies that aren't used.

## 11.10.34 - 2026-08-24
- Raise the `pip` floor from `>=26.1.2` to `>=26.2`.
- Regenerate `template/*/uv.lock` from the updated template so a rendered component picks the new
  minimums up.

## 11.10.33 - 2026-08-20
- Upgrade automation policies

## 11.10.32 - 2026-08-20
- Add automated cve-sync monitoring policies

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
