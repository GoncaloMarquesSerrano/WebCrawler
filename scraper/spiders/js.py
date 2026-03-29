from ..models import Page
from bs4 import BeautifulSoup
import time


async def crawl_js_page(url: str, session, job_id: int, depth: int, browser) -> Page:
    page = await browser.new_page()
    try:
        t0 = time.monotonic()
        response = await page.goto(url, timeout=10000)
        await page.wait_for_load_state("networkidle")
        load_time_ms = (time.monotonic() - t0) * 1000
        html_content = await page.content()
        soup = BeautifulSoup(html_content, "html.parser")
        title = soup.title.get_text(strip=True) if soup.title else None
        description = soup.find("meta", attrs={"name": "description"})
        for tag in soup(
            ["script", "style", "noscript", "nav", "header", "footer", "aside"]
        ):
            tag.decompose()
        body = soup.get_text(separator="\n").strip()
        if response.url != url:
            url = response.url
        redirected = response.request.redirected_from
        crawl_page = Page(
            job_id=job_id,
            url=url,
            status_code=response.status if response else None,
            title=title,
            description=description["content"].strip() if description else None,
            body=body,
            depth=depth,
            redirected_from=redirected.url if redirected else None,
            error=None,
            is_javascript=True,
            load_time_ms=load_time_ms,
        )
        session.add(crawl_page)
        await session.flush()  
        return crawl_page
    except Exception as e:
        crawl_page = Page(job_id=job_id, url=url, depth=depth, error=str(e))
        session.add(crawl_page)
        await session.flush()
        return crawl_page
    finally:
        await page.close()
