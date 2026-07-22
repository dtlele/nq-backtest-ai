from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.goto("http://localhost:5173", wait_until="networkidle")
        page.wait_for_timeout(2000) # wait for data to load
        page.screenshot(path="dashboard_screenshot.png", full_page=True)
        browser.close()

if __name__ == "__main__":
    run()
