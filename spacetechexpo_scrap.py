from playwright.sync_api import sync_playwright
import pandas as pd
import time
import random
from datetime import datetime, UTC
from urllib.parse import urljoin
import os, re
START_URL = "https://www.spacetechexpo-europe.com/exhibitor-list"


def sanitize_filename(text):
    return re.sub(r"[^a-zA-Z0-9_-]", "_", text)

def main():
    rows = []

    with sync_playwright() as p:
        browser = p.chromium.launch()#(headless=False, slow_mo=1000)
        context = browser.new_context()
        page = context.new_page()
        page.goto(START_URL, wait_until="domcontentloaded")
        try:
            page.wait_for_selector("div.exhibitor-slide")
            child_divs = page.locator("div.slide-list > div")
            total_child_divs = child_divs.count()
            print(f"Found {total_child_divs} child divs")
            for i in range(total_child_divs):
                print(f"reading the {i}th child div")
                child_div = child_divs.nth(i)
                name = child_div.locator("h4.exhibitor-name a").inner_text()

                # Booth Number (remove label)
                booth_text = child_div.locator("p.exhibitor-booth").inner_text()
                booth = booth_text.replace("Booth Number:", "").strip()

                # Category
                category = child_div.locator("div.exhibitor-slide__cats p").inner_text().strip()
                print(name, booth, category)

                # Goes to details page.
                
                # --- Get detail link WITHOUT clicking ---
                href = child_div.locator("h4.exhibitor-name a").get_attribute("href")
                detail_url = "https://www.spacetechexpo-europe.com" + href

                # --- Open new tab ---
                detail_page = context.new_page()
                detail_page.goto(detail_url, wait_until="domcontentloaded", timeout=30000)

                # Close cookie popup if exists
                cookie_btn = detail_page.locator("button:has-text('Accept all')")
                if cookie_btn.is_visible():
                    cookie_btn.click()

                # Wait until loading spinner disappears
                spinner = detail_page.locator("svg.spinner, .loading-spinner, .react__spinner, .loader")
                try:
                    spinner.wait_for(state="detached", timeout=5000)
                except:
                    pass  # ignore if spinner never appears


                # ---- scrape detail page ----
                # 2️⃣ wait for guaranteed element
                detail_page.wait_for_selector("h1")
                # ---- Website ----
                website = ""
                website_el = detail_page.locator(".meta-info-col__contact-list a")
                if website_el.count() > 0:
                    website = website_el.nth(0).get_attribute("href")

                # ---- Address blocks ----
                address = ""
                addr_lines = detail_page.locator(".meta-info-col__address p strong")
                total = addr_lines.count()

                address_parts = []
                for j in range(total):
                    text = addr_lines.nth(j).inner_text().strip()
                    address_parts.append(text)

                address = " ".join(address_parts)
                detail_page.close()
                rows.append([name, booth, category, website, address])

        except Exception as e:
            print("ERROR:", e)
            try:
                safe_name = sanitize_filename(name)
                detail_page.screenshot(path=f"errors/{safe_name}_{i}.png")
            except:
                pass
            raise

        browser.close()

    # df = pd.DataFrame(rows)
    # df.to_csv("homewyse_miami_sample.csv", index=False)
    pd.DataFrame(rows, columns=["Name", "Booth", "Category", "Website", "Address"]).to_csv("expo.csv", index=False)

    # print("\nSaved sample CSV: homewyse_miami_sample.csv")
    # print("Rows scraped:", len(df))


if __name__ == "__main__":
    os.makedirs("errors", exist_ok=True)
    main()
