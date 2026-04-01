from bs4 import BeautifulSoup
from urllib.parse import urlparse
from .models import CrawlJob, Queue
from .robots import is_allowed
from .spiders.static import crawl_static_page
from .spiders.js import crawl_js_page
from .spiders.links import extract_links, save_links
import httpx
from sqlalchemy import select
import asyncio
import playwright.async_api as pw
from .db import get_session_factory
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import DBAPIError
from sqlalchemy import func


def is_js_rendered(html: str) -> bool:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(strip=True)
    if len(text) < 500:
        return True
    return "data-reactroot" in html or "data-vue-meta" in html


async def initialize_crawl(seed_url: str, session) -> CrawlJob:
    try:
        domain = urlparse(seed_url).netloc
        crawl_job = CrawlJob(
            domain=domain,
            seed_url=seed_url,
            status="pending",
        )
        session.add(crawl_job)
        await session.flush()  # To get crawl_job.id
        queue_item = Queue(
            url=seed_url, depth=0, status="pending", crawl_job_id=crawl_job.id
        )
        session.add(queue_item)
        await session.flush()  # To get queue_item.id
        await session.commit()
    except Exception as e:
        print(f"Invalid URL: {seed_url} - {e}")
        await session.rollback()
        return None
    return crawl_job


async def worker(
    name: str,
    job: CrawlJob,
    session_factory,
    browser,
    async_client: httpx.AsyncClient,
    delay: float,
    pages_crawled: dict,
):
    consecutive_empty_checks = 0

    async with session_factory() as session:
        while True:
            queue_item = await get_and_lock_queue_item(session, job.id)
            if queue_item is None:
                consecutive_empty_checks += 1
                print(f"{name} queue empty, retry {consecutive_empty_checks}/60")
                if (
                    consecutive_empty_checks >= 60
                ):  # 60 tries with no items before exiting
                    break
                await asyncio.sleep(0.5)
                continue
            consecutive_empty_checks = 0
            job_url = queue_item.url
            print(f"{name} processing: {job_url} at depth {queue_item.depth}")

            if pages_crawled["count"] >= job.max_pages:
                break
            pages_crawled["count"] += 1

            if not await is_allowed(job_url):
                print(f"URL disallowed by robots.txt: {job_url}")
                queue_item.status = "failed"
                session.add(queue_item)
                await session.commit()
                continue

            crawl_delay = delay
            await asyncio.sleep(crawl_delay)

            try:
                response = await async_client.get(job_url, timeout=10.0)
                if response.status_code != 200:
                    print(
                        f"Failed to fetch {job_url} - Status code: {response.status_code}"
                    )
                    queue_item.status = "failed"
                    session.add(queue_item)
                    await session.commit()
                    continue

                if is_js_rendered(response.text):
                    page = await crawl_js_page(
                        job_url, session, job.id, queue_item.depth, browser
                    )
                else:
                    page = await crawl_static_page(
                        job_url, session, job.id, queue_item.depth, async_client
                    )

                links = extract_links(response.text, job_url)
                await save_links(session, page.id, links, urlparse(job_url).netloc)
                new_depth = queue_item.depth + 1
                queue_item.status = "completed"
                if new_depth <= job.max_depth:
                    sorted_links = sorted(
                        set(
                            link_url
                            for link_url, _ in links
                            if urlparse(link_url).netloc == job.domain
                        )
                    )

                    for link_url in sorted_links:
                        for attempt in range(3):  # 3 tries
                            try:
                                stmt = (
                                    insert(Queue)
                                    .values(
                                        url=link_url,
                                        depth=new_depth,
                                        status="pending",
                                        crawl_job_id=job.id,
                                    )
                                    .on_conflict_do_nothing(
                                        index_elements=["crawl_job_id", "url"]
                                    )
                                )
                                await session.execute(stmt)
                                break  # success, leaves retry loop
                            except DBAPIError:
                                await session.rollback()
                                await asyncio.sleep(0.1 * attempt)  # backoff
                                continue
                    await session.commit()
                else:
                    print(f"Max depth reached for {job_url}")
                session.add(queue_item)
                await session.commit()

            except Exception as e:
                print(f"Error crawling {job_url}: {e}")
                await session.rollback()
                queue_item.status = "failed"
                session.add(queue_item)
                await session.commit()


async def get_and_lock_queue_item(session, job_id: int) -> Queue:
    result = await session.execute(
        select(Queue)
        .where(Queue.crawl_job_id == job_id, Queue.status == "pending")
        .order_by(Queue.id.asc())
        .with_for_update(skip_locked=True)
    )

    item = result.scalars().first()

    if item:
        item.status = "processing"
        session.add(item)
        await session.commit()

    return item


async def run_crawl(
    seed_url: str,
    session,
    max_depth: int,
    num_workers: int,
    delay: float,
    max_pages: int,
) -> None:
    job = await initialize_crawl(seed_url, session)
    if job is None:
        print("Failed to initialize crawl job.")
        return
    job.status = "running"
    job.max_depth = max_depth  # Set the maximum depth for the crawl job
    job.max_pages = max_pages  # Set the maximum pages for the crawl job
    session.add(job)
    await session.commit()
    playwright = await pw.async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)
    async_client = httpx.AsyncClient(
        verify=False,
        follow_redirects=True,
        timeout=10.0,
        headers={
            "User-Agent": "GsCrawler/1.0 (https://github.com/GoncaloMarquesSerrano/WebCrawler; contact: gs42contact@gmail.com)",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    pages_crawled = {"count": 0}

    tasks = [
        asyncio.create_task(
            worker(
                f"Worker-{i + 1}",
                job,
                get_session_factory(),
                browser,
                async_client,
                delay=delay,
                pages_crawled=pages_crawled,
            )
        )
        for i in range(num_workers)  # Number of concurrent workers
    ]

    await asyncio.gather(*tasks)

    await browser.close()
    await playwright.stop()
    await async_client.aclose()

    job.status = "completed"
    session.add(job)
    await session.commit()
