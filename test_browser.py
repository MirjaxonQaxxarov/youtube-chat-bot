from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        user_data_dir="./chrome_profile",
        headless=False,
        viewport={"width": 1400, "height": 900},
    )

    page = browser.new_page()
    page.goto("https://www.youtube.com", wait_until="domcontentloaded")

    print("Chrome ochildi.")
    print("YouTube'ga qo'lda login qiling.")
    input("Login tugagach ENTER bosing...")

    print("Session saqlandi.")
    print("Brauzerni yopish uchun ENTER bosing.")
    input()

    browser.close()

