from protego import Protego
import httpx
from urllib.parse import urlparse
import time
import asyncio

robots_cache = {}
robots_locks = {}


async def get_robots_parser(url: str) -> Protego:
    domain = urlparse(url).netloc

    if domain in robots_cache:
        return robots_cache[domain]

    robots_locks.setdefault(domain, asyncio.Lock())
    async with robots_locks[domain]:
        if domain in robots_cache:
            return robots_cache[domain]

        robots_url = f"https://{domain}/robots.txt"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(robots_url, timeout=5.0)
                if response.status_code == 200:
                    rp = Protego.parse(response.text)
                else:
                    rp = Protego.parse("")

        except Exception:
            rp = Protego.parse("")

        robots_cache[domain] = rp
        return rp


async def is_allowed(url: str, user_agent: str = "*") -> bool:
    rp = await get_robots_parser(url)
    return rp.can_fetch(url, user_agent)


async def get_crawl_delay(url: str, user_agent: str = "*") -> float:
    rp = await get_robots_parser(url)
    delay = rp.crawl_delay(user_agent)
    return delay if delay is not None else 0


async def apply_domain_rate_limit(url, delay, domain_last_request, domain_locks):
    domain = urlparse(url).netloc

    domain_locks.setdefault(domain, asyncio.Lock())

    async with domain_locks[domain]:
        now = time.monotonic()
        last_time = domain_last_request.get(domain, 0)

        wait_time = max(0, delay - (now - last_time))

        if wait_time > 0:
            await asyncio.sleep(wait_time)

        domain_last_request[domain] = time.monotonic()
