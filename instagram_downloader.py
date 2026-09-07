"""
Advanced Instagram Profile Downloader — built on Instaloader
=====================================================
Upgraded features:
  - Clean Folder Structure (/Photos and /Videos)
  - SQLite Database integration (replaces CSV, prevents duplicates)
  - CLI Arguments (argparse) for flexible running
  - Precise download counting 
  - Graceful exit handling on Ctrl+C
"""

import sys
import os
import time
import random
import getpass
import argparse
import sqlite3

import instaloader
from instaloader.exceptions import (
    ProfileNotExistsException,
    PrivateProfileNotFollowedException,
    TooManyRequestsException,
    ConnectionException,
    BadCredentialsException,
    TwoFactorAuthRequiredException,
    LoginRequiredException,
)

def build_loader(username: str) -> instaloader.Instaloader:
    L = instaloader.Instaloader(
        download_comments=False,
        save_metadata=False, 
        quiet=True,          
    )

    if not username:
        print("WARNING: Running anonymously. Instagram rate-limits this heavily.")
        return L

    session_file = f"session-{username}"
    try:
        L.load_session_from_file(username, filename=session_file)
        print(f"[*] Loaded saved session for {username}.")
        return L
    except FileNotFoundError:
        pass

    print(f"[*] No session found. Please log in.")
    password = getpass.getpass(f"Instagram password for {username}: ")
    try:
        L.login(username, password)
    except TwoFactorAuthRequiredException:
        code = input("Two-factor code: ").strip()
        L.two_factor_login(code)
    except BadCredentialsException:
        print("[!] Login failed: wrong username/password.")
        sys.exit(1)

    L.save_session_to_file(filename=session_file)
    print("[*] Logged in and saved session for next time.")
    return L


def download_one(L: instaloader.Instaloader, post: instaloader.Post, target_dir: str, max_retries: int) -> bool:
    for attempt in range(1, max_retries + 1):
        try:
            return L.download_post(post, target=target_dir)
        except TooManyRequestsException:
            wait = 60 * attempt
            print(f"  [!] Rate-limited (429). Waiting {wait}s (retry {attempt}/{max_retries})...")
            time.sleep(wait)
        except ConnectionException as e:
            wait = 30 * attempt
            print(f"  [!] Connection error ({e}). Waiting {wait}s (retry {attempt}/{max_retries})...")
            time.sleep(wait)
        except Exception as e:
            print(f"  [!] Unexpected error on {post.shortcode}: {e}. Skipping.")
            return False
            
    print(f"  [!] Giving up on {post.shortcode} after {max_retries} retries.")
    return False


def main():
    parser = argparse.ArgumentParser(description="Advanced Instagram Profile Downloader")
    parser.add_argument("target", help="Profile to download from (no @)")
    parser.add_argument("-u", "--username", default="", help="Your IG username for login")
    parser.add_argument("--photos", type=int, default=None, help="Max photo posts to download")
    parser.add_argument("--videos", type=int, default=None, help="Max video posts to download")
    parser.add_argument("--batch", type=int, default=20, help="Batch size before long pause")
    parser.add_argument("--sql", action="store_true", help="Save metadata to an SQLite database")
    args = parser.parse_args()

    L = build_loader(args.username)

    try:
        profile = instaloader.Profile.from_username(L.context, args.target)
    except ProfileNotExistsException:
        print(f"[!] Profile '{args.target}' doesn't exist.")
        return

    base_dir = profile.username
    os.makedirs(base_dir, exist_ok=True)
    
    photos_done = videos_done = processed = 0
    print(f"\n[*] Target: @{profile.username}")
    print(f"[*] Limits: {args.photos or 'Unlimited'} photos, {args.videos or 'Unlimited'} videos\n")

    # --- SQL DATABASE SETUP ---
    conn = None
    cursor = None
    if args.sql:
        db_path = os.path.join(base_dir, f"{profile.username}_data.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create the table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                shortcode TEXT PRIMARY KEY,
                date_utc TEXT,
                type TEXT,
                is_video BOOLEAN,
                likes INTEGER,
                comments INTEGER,
                location TEXT,
                caption TEXT
            )
        ''')
        conn.commit()
        print(f"[*] Connected to SQLite database: {db_path}")

    try:
        for post in profile.get_posts():
            photos_left = args.photos is None or photos_done < args.photos
            videos_left = args.videos is None or videos_done < args.videos
            
            if not photos_left and not videos_left:
                print("\n[*] Reached both photo and video limits. Stopping.")
                break

            is_video = post.is_video
            if (is_video and not videos_left) or (not is_video and not photos_left):
                continue

            label = "Video" if is_video else "Photo"
            sub_folder = "Videos" if is_video else "Photos"
            post_target_dir = os.path.join(base_dir, sub_folder)
            
            # Download media
            was_downloaded = download_one(L, post, post_target_dir, max_retries=3)
            
            # --- INSERT OR UPDATE SQL DATA ---
            if args.sql:
                cursor.execute('''
                    INSERT OR REPLACE INTO posts 
                    (shortcode, date_utc, type, is_video, likes, comments, location, caption)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    post.shortcode,
                    post.date_utc.strftime("%Y-%m-%d %H:%M:%S"),
                    post.typename,
                    is_video,
                    post.likes,
                    post.comments,
                    post.location.name if post.location else "None",
                    str(post.caption) if post.caption else ""
                ))
                conn.commit() # Save the changes immediately

            if was_downloaded:
                status = f"DOWNLOADED -> /{sub_folder}"
                if is_video: videos_done += 1
                else: photos_done += 1
            else:
                status = "SKIPPED (Exists)"

            print(f"[{processed + 1}] {label} {post.shortcode} | {status}")
            processed += 1

            if processed % args.batch == 0:
                print(f"  -- Pausing 120s to prevent rate limits --")
                time.sleep(120)
            else:
                time.sleep(random.uniform(5, 12))

    except KeyboardInterrupt:
        print("\n[!] Process interrupted by user. Saving and exiting cleanly...")
    except PrivateProfileNotFollowedException:
        print(f"[!] '{profile.username}' is private and isn't followed. Nothing to download.")
    except LoginRequiredException:
        print("[!] Instagram requires a login for this action. Use the -u flag.")
    finally:
        if conn:
            conn.close() # Safely close the database connection

    print(f"\n[*] Done. Downloaded {photos_done} new photo(s) and {videos_done} new video(s).")
    if args.sql:
        print(f"[*] Metadata safely stored in SQLite database.")

if __name__ == "__main__":
    main()