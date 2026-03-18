"""
push_git.py — Roneat Studio Pro
==============================
Automate the process of pushing changes to GitHub.

Usage:
    python push_git.py "Your commit message"
    (If no message is provided, it defaults to "minor updates")
"""

import subprocess
import sys
import os

def run_git():
    # 1. Get commit message
    if len(sys.argv) > 1:
        commit_msg = sys.argv[1]
    else:
        commit_msg = input("Enter commit message [minor updates]: ").strip()
        if not commit_msg:
            commit_msg = "minor updates"

    print(f"\n--- Starting GitHub Update: '{commit_msg}' ---")

    try:
        # Check if it's a git repo
        if not os.path.exists(".git"):
            print("[ERROR] .git folder not found. Is this a git repository?")
            return

        # git add .
        print("> git add .")
        subprocess.run(["git", "add", "."], check=True)

        # git commit -m "..."
        print(f"> git commit -m \"{commit_msg}\"")
        subprocess.run(["git", "commit", "-m", commit_msg], check=True)

        # git push
        print("> git push")
        subprocess.run(["git", "push"], check=True)

        print("\n✅ Successfully pushed to GitHub!")

    except subprocess.CalledProcessError as e:
        print(f"\n❌ Git command failed: {e}")
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")

if __name__ == "__main__":
    run_git()
