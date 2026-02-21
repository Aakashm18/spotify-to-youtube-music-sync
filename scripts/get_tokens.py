"""
scripts/get_tokens.py
======================
One-time interactive helper that walks you through obtaining:
  1. A Spotify refresh token  (user-library-read scope)
  2. A YouTube / Google refresh token (youtube scope)

Run this ONCE on your local machine.  The tokens are printed to the console
so you can paste them as GitHub Actions Secrets.  They are NEVER written to
disk or logged — treat them like passwords.

Usage:
    pip install spotipy google-auth-oauthlib
    python scripts/get_tokens.py
"""

from __future__ import annotations

import os
import webbrowser

# ──────────────────────────────────────────────────────────────────────────────
# SPOTIFY TOKEN
# ──────────────────────────────────────────────────────────────────────────────


def get_spotify_refresh_token() -> None:
    """Interactive flow to obtain a Spotify refresh token."""
    try:
        from spotipy.oauth2 import SpotifyOAuth
    except ImportError:
        print("Please install spotipy:  pip install spotipy")
        return

    print("\n" + "=" * 60)
    print("  STEP 1 — Spotify Refresh Token")
    print("=" * 60)
    print(
        "\nYou'll need a Spotify app from https://developer.spotify.com/dashboard\n"
        "  • Create an app\n"
        "  • Add  http://localhost:8888/callback  as a Redirect URI\n"
        "  • Copy the Client ID and Client Secret\n"
    )

    client_id = input("Spotify Client ID     : ").strip()
    client_secret = input("Spotify Client Secret : ").strip()

    auth = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri="http://localhost:8888/callback",
        scope="user-library-read",
        open_browser=False,
    )

    url = auth.get_authorize_url()
    print(f"\nOpen this URL in your browser:\n  {url}\n")
    webbrowser.open(url)

    redirected = input(
        "After authorising, paste the FULL redirect URL here\n"
        "(it starts with http://localhost:8888/callback?code=…)\n> "
    ).strip()

    code = auth.parse_response_code(redirected)
    token_info = auth.get_access_token(code, as_dict=True)

    print("\n✅ Spotify Refresh Token (save this as SPOTIFY_REFRESH_TOKEN):")
    print(f"   {token_info['refresh_token']}\n")


# ──────────────────────────────────────────────────────────────────────────────
# YOUTUBE TOKEN
# ──────────────────────────────────────────────────────────────────────────────


def get_youtube_refresh_token() -> None:
    """Interactive OAuth2 flow to obtain a YouTube refresh token."""
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore
    except ImportError:
        print("Please install google-auth-oauthlib:  pip install google-auth-oauthlib")
        return

    print("\n" + "=" * 60)
    print("  STEP 2 — YouTube (Google) Refresh Token")
    print("=" * 60)
    print(
        "\nYou'll need a Google Cloud project from https://console.cloud.google.com/\n"
        "  1. Create (or select) a project\n"
        "  2. Enable the YouTube Data API v3\n"
        "  3. Go to APIs & Services → Credentials\n"
        "  4. Create OAuth 2.0 Client ID — Application type: Desktop App\n"
        "  5. Note your Client ID and Client Secret\n"
        "  6. Add yourself as a Test User in OAuth Consent Screen\n"
    )

    client_id = input("Google Client ID     : ").strip()
    client_secret = input("Google Client Secret : ").strip()

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
        }
    }

    flow = InstalledAppFlow.from_client_config(
        client_config,
        scopes=["https://www.googleapis.com/auth/youtube"],
    )

    creds = flow.run_local_server(port=0)

    print("\n✅ YouTube Refresh Token (save this as YOUTUBE_REFRESH_TOKEN):")
    print(f"   {creds.refresh_token}\n")

    print("   Also save:")
    print(f"     YOUTUBE_CLIENT_ID     = {client_id}")
    print(f"     YOUTUBE_CLIENT_SECRET = {client_secret}\n")


# ──────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────────────────────────────────────


def main() -> None:
    print("\n" + "=" * 60)
    print("  Spotify ↔ YouTube Token Setup Helper")
    print("=" * 60)
    print(
        "\nThis script will help you obtain the refresh tokens needed for\n"
        "the GitHub Actions secrets.  Run this ONCE on your local machine.\n"
        "\nThe tokens will be printed to your terminal ONLY — never written\n"
        "to any file.  Treat them as passwords.\n"
    )

    get_spotify_refresh_token()
    get_youtube_refresh_token()

    print("=" * 60)
    print("  All tokens obtained.  Follow the README to add them as")
    print("  GitHub Actions Secrets in your repository settings.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
