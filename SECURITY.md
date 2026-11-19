# Security Policy

This file covers `abuzucom/agents` itself. `SECURITY.md.example` remains the
template for adopting repositories.

## Supported Versions

| Version | Supported |
|---------|-----------|
| Latest stable release | Yes |
| Pre-releases | No |
| Untagged `main` commits | No |
| Older stable releases | No |

A published non-pre-release GitHub release marks a stable version. A
pre-release or an untagged `main` commit marks a development build. Fixes land
on `main` under a new version. No fix reaches an older stable release.

## Scope

Scope includes code and configuration in this repository. Scope includes the
release workflow `.github/workflows/release.yml` and `scripts/release.py`.
Scope includes the release files, `SHA256SUMS.txt`, and the Sigstore
attestation bundles. Scope includes third-party vulnerabilities when a
selected version, pin, configuration, permission, or integration causes the
defect. Route purely upstream defects to the upstream maintainers.

Scope excludes social engineering. Scope excludes physical attacks. Scope
excludes repository settings outside version control. The tag ruleset, the
`release` environment, and immutable releases count as such settings.

## Reporting a Vulnerability

Report vulnerabilities through GitHub private vulnerability reporting. Open
the Security tab. Select Report a vulnerability. Never open a public issue for
a vulnerability report.

Response timing: acknowledgment within 7 days.

Remediation target: a fix within 30 days.

## Disclosure Policy

Coordinate disclosure with the maintainers. Keep the report private before a
disclosure event. A shipped fix defines one disclosure event. Passage of 90
days after the report defines another disclosure event. Use the earlier
event.

A fix ships as a new tagged version. The advisory names the affected versions
and the fixed version.

## Release integrity

Each release carries `SHA256SUMS.txt` and a Sigstore attestation bundle.
Verify a release file with:

`gh attestation verify <file> --repo abuzucom/agents --signer-workflow abuzucom/agents/.github/workflows/release.yml`

`docs/gate-threat-model.md` lists what the attestation proves and what it
leaves unproven.
