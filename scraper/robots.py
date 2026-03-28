from protego import Protego
import httpx
from urllib.parse import urlparse

robots_cache = {}

async def get_robots_parser(url: str):
    domain = urlparse(url).netloc
    
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

async def is_allowed(url: str, user_agent: str = "*"):
    rp = await get_robots_parser(url)
    return rp.can_fetch(url, user_agent)

async def get_crawl_delay(url: str, user_agent: str = "*"):
    rp = await get_robots_parser(url)
    return rp.crawl_delay(user_agent) or 1.0

