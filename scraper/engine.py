from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from .models import CrawlJob, Queue 
from .robots import is_allowed, get_crawl_delay
from .spiders.static import crawl_static_page
from .spiders.js import crawl_js_page
from .spiders.links import extract_links, save_links
import httpx
from sqlalchemy import select
import asyncio
import playwright.async_api as pw


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
            url=seed_url,
            depth=0,
            status="pending",
            crawl_job_id=crawl_job.id
        )
        session.add(queue_item)
        await session.flush()  # To get queue_item.id
        await session.commit()
    except Exception as e:
        print(f"Invalid URL: {seed_url} - {e}")
        await session.rollback()
        return None
    return crawl_job

async def run_crawl(seed_url: str, session, max_depth: int) -> None:
    job = await initialize_crawl(seed_url, session)
    if job is None:
        print("Failed to initialize crawl job.")
        return
    job.status = "running"
    job.max_depth = max_depth  # Set the maximum depth for the crawl job
    job_id = job.id
    session.add(job)
    await session.commit()
    playwright = await pw.async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)
    async_client = httpx.AsyncClient(verify=False, follow_redirects=True)
    
    
    while not await is_queue_empty(session, job_id):
        queue_item = await get_queue_item(session, job_id)
        if queue_item is None:
            break
        job_url = queue_item.url
        queue_item.status = "processing"
        session.add(queue_item)
        await session.commit()
        
        
        if not await is_allowed(job_url):
            print(f"URL disallowed by robots.txt: {job_url}")
            queue_item.status = "failed"
            session.add(queue_item)
            await session.commit()
            continue
        
        
        crawl_delay = await get_crawl_delay(job_url)
        await asyncio.sleep(crawl_delay)
        
        try:
            response = await async_client.get(job_url, timeout=10.0)
            if response.status_code != 200:
                print(f"Failed to fetch {job_url} - Status code: {response.status_code}")
                queue_item.status = "failed"
                session.add(queue_item)
                await session.commit()
                continue
            
            if is_js_rendered(response.text):
                page = await crawl_js_page(job_url, session, job_id, queue_item.depth, browser)
            else:
                page = await crawl_static_page(job_url, session, job_id, queue_item.depth, async_client)
                
            links = extract_links(response.text, job_url)
            await save_links(session, page.id, links, urlparse(job_url).netloc)
            new_depth = queue_item.depth + 1
            queue_item.status = "completed"
            if new_depth <= job.max_depth:
                for link_url, _ in links:
                    if urlparse(link_url).netloc != job.domain:
                        continue
                    if not await is_url_in_queue(session, job_id, link_url):
                        new_queue_item = Queue(
                            url=link_url,
                            depth=new_depth,
                            status="pending",
                            crawl_job_id=job_id
                        )
                        session.add(new_queue_item)
                await session.commit()
            else:
                print(f"Max depth reached for {job_url}")
            session.add(queue_item)
            await session.commit()
                        
        except Exception as e:
            print(f"Error crawling {job_url}: {e}")
            queue_item.status = "failed"
            session.add(queue_item)
            await session.commit()
            
            
    await browser.close()
    await playwright.stop()
    await async_client.aclose()
    
    job.status = "completed"
    session.add(job)
    await session.commit()
        
    
async def is_queue_empty(session, job_id: int) -> bool:
    result = await session.execute(
        select(Queue)
        .where(Queue.crawl_job_id == job_id, Queue.status == "pending")
    )
    return result.scalars().first() is None 

async def get_queue_item(session, job_id: int) -> Queue:
    result = await session.execute(
        select(Queue)
        .where(Queue.crawl_job_id == job_id, Queue.status == "pending")
        .order_by(Queue.id.asc())
    )
    return result.scalars().first()

async def is_url_in_queue(session, job_id: int, url: str) -> bool:
    result = await session.execute(
        select(Queue)
        .where(Queue.crawl_job_id == job_id, Queue.url == url)
    )
    return result.scalars().first() is not None