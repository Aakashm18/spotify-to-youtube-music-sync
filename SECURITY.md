# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| `main` branch | ✅ Active |
| Older releases | ❌ No longer maintained |

## Reporting a Vulnerability

**Please do NOT open a public GitHub Issue to report security vulnerabilities.**

If you discover a security issue (e.g., token leakage, insecure OAuth handling, secrets exposure), please report it responsibly:

1. Open a [GitHub Security Advisory](https://github.com/Aakashm18/spotify-to-youtube-music-sync/security/advisories/new) (preferred — keeps it private until patched).
2. Alternatively, describe the issue in a private message to the maintainer.

Include:
- A description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested fix (optional but appreciated)

We aim to acknowledge all reports within **48 hours** and provide a fix or mitigation within **7 days** for critical issues.

## Security Design

This project is built with security as a priority:

| Practice | Implementation |
|----------|----------------|
| **Zero hard-coded secrets** | All credentials are read from environment variables only |
| **GitHub Secrets** | OAuth tokens stored as encrypted GitHub Actions Secrets — never in source code or logs |
| **Refresh tokens only** | The sync uses refresh tokens; access tokens are never persisted |
| **Minimal OAuth scopes** | Spotify: `user-library-read` only. YouTube: `youtube` (write required for playlist insert) |
| **No disk writes of tokens** | `get_tokens.py` prints tokens to terminal only; never writes to files |
| **Atomic state writes** | `processed_tracks.json` is written via rename to prevent corruption |
| **Dependabot enabled** | Dependency updates are automated to catch vulnerable package versions |

## What This Tool Does NOT Do

- It does **not** store your Spotify or YouTube passwords
- It does **not** access your Spotify playlists (only Liked Songs)
- It does **not** read, modify, or delete YouTube videos — only adds to a specific playlist you control
- It does **not** send your data to any third-party service

## Keeping Your Deployment Secure

- Rotate your OAuth refresh tokens periodically (re-run `python scripts/get_tokens.py`)
- Review and restrict which GitHub Actions have access to repository secrets
- Never share your forked repo's secrets with untrusted contributors
- If you suspect a token has been compromised, revoke it immediately:
  - Spotify: [Spotify Account → Apps](https://www.spotify.com/account/apps/)
  - Google/YouTube: [Google Account → Security → Third-party access](https://myaccount.google.com/permissions)
