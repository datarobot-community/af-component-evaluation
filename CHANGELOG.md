# Changelog

What changed in each release, so anyone pinned to a tag can tell whether a bump is safe.

This project is in beta. Releases are cut automatically: every merge to `main` tags the next patch
and publishes a GitHub release, so the version is not known while a pull request is open. Add your
bullets under "Unreleased" and they get a version heading when the release is cut.

The format is deliberately plain: one flat list of bullets per release, no Added / Changed / Fixed
subsections. Say what changed and why someone consuming this component would care.

Releases before this file was added are described in the
[GitHub releases](https://github.com/datarobot-community/af-component-evaluation/releases).

## Unreleased
- Upgraded the shared `datarobot-oss/github-actions` workflows from `0.0.18` to `0.0.24`, and added
  this changelog plus a pull-request check that requires it to be updated. The check is waivable with
  a `skip-changelog` label and is skipped for bot-authored pull requests.
