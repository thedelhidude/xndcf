import asyncio
from playwright.async_api import async_playwright
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone

URL = "https://www.argusmedia.com/en/news-and-insights/latest-market-news?filter_language=en-gb"

# ---------------------------
# Scraping Function
# ---------------------------
async def scrape():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox"]
        )

        page = await browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
        )

        # FIX: Avoid networkidle (causes timeout)
        await page.goto(URL, wait_until="domcontentloaded", timeout=60000)

        # Give JS time to render
        await page.wait_for_timeout(5000)

        # Wait for articles
        try:
            await page.wait_for_selector(".qa-news-item", timeout=15000)
        except:
            print("No items found on page")
            await browser.close()
            return []

        # Extract data
        items = await page.evaluate("""
        () => {
            return Array.from(document.querySelectorAll('.qa-news-item')).map(el => ({
                title: el.querySelector('h3')?.innerText || "",
                link: el.querySelector('a')?.href || "",
                desc: el.querySelector('p.qa-item-summary')?.innerText || "",
                date: el.querySelector('p.qa-item-date')?.innerText || ""
            }));
        }
        """)

        await browser.close()

        print(f"Scraped {len(items)} items")
        return items


# ---------------------------
# RSS Generator
# ---------------------------
def generate_rss(items):
    fg = FeedGenerator()
    fg.title("Argus Market News")
    fg.link(href=URL)
    fg.description("Latest market news from Argus")

    for item in items:
        if not item["title"] or not item["link"]:
            continue

        fe = fg.add_entry()
        fe.title(item["title"])
        fe.link(href=item["link"])
        fe.description(item["desc"])

        if item["date"]:
            try:
                dt = datetime.strptime(item["date"], "%d/%m/%y")
                dt = dt.replace(tzinfo=timezone.utc)
                fe.pubDate(dt)
            except:
                pass

    fg.rss_file("feed.xml")
    print("RSS feed generated: feed.xml")


# ---------------------------
# Main Runner
# ---------------------------
if __name__ == "__main__":
    items = asyncio.run(scrape())

    if not items:
        print("No data scraped. Skipping RSS generation.")
    else:
        generate_rss(items)
