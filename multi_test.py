from pathlib import Path
from playwright.sync_api import sync_playwright
import time
import random

CHROME_DATA = Path.home() / ".config" / "google-chrome"

PROFILES = [
    "Default",
    "Profile 1",
    "Profile 2",
    "Profile 5",
    "Profile 6",
]

TEST_MESSAGES = [
    "Assalomu alaykum!",
    "Bugungi mavzu juda yaxshi ekan.",
    "Keyingi video qachon chiqadi?",
    "Rahmat, juda foydali bo‘ldi.",
    "Alloh rozi bo‘lsin 🤲",
]

def main():
    print("YouTube multi-account TEST")
    print("=" * 50)

    with sync_playwright() as p:

        contexts = []

        for profile in PROFILES:
            profile_path = CHROME_DATA / profile

            if not profile_path.exists():
                print(f"[SKIP] {profile} topilmadi")
                continue

            print(f"[OPEN] {profile}")

            context = p.chromium.launch_persistent_context(
                user_data_dir=str(profile_path),
                executable_path="/usr/bin/google-chrome",
                headless=False,
                args=[
                    "--disable-notifications",
                ],
            )

            contexts.append((profile, context))

        print()
        print(f"{len(contexts)} ta profil ochildi.")
        print()

        # TEST ONLY:
        # Xabarlar YouTube'ga yuborilmaydi.
        for profile, context in contexts:

            print(f"\n--- {profile} ---")

            for message in TEST_MESSAGES:

                delay = random.uniform(2, 5)
                time.sleep(delay)

                print(f"{profile}: {message}")

        print()
        print("=" * 50)
        print("TEST tugadi.")
        print("Browserlarni yopish uchun ENTER bosing.")

        input()

        for _, context in contexts:
            context.close()


if __name__ == "__main__":
    main()