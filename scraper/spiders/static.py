from ..models import Page
import httpx
from bs4 import BeautifulSoup


async def crawl_static_page(url: str, session, job_id: int, depth: int):
    try:
        async_client = httpx.AsyncClient()
        async with async_client as client:
            html_response = await client.get(url, timeout=10.0)
        soup = BeautifulSoup(html_response.text, "html.parser")
        title = soup.title.get_text(strip=True) if soup.title else None
        description = soup.find("meta", attrs={"name": "description"})
        for tag in soup(
            ["script", "style", "noscript", "nav", "header", "footer", "aside"]
        ):
            tag.decompose()
        body = soup.get_text(separator="\n").strip()
        page = Page(
            job_id=job_id,
            url=url,
            status_code=html_response.status_code,
            title=title,
            description=description["content"].strip() if description else None,
            body=body,
            depth=depth,
            redirected_from=html_response.history[0].url
            if html_response.history
            else None,
            error=None,
            is_javascript=False,
            load_time_ms=html_response.elapsed.total_seconds() * 1000,
        )
        session.add(page)
        return page
    except Exception as e:
        page = Page(job_id=job_id, url=url, depth=depth, error=str(e))
        session.add(page)
        return page
