from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

from ..models import Link


def extract_links(html: str, base_url: str):
    soup = BeautifulSoup(html, "html.parser")
    link_pairs = set()
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        anchor_text = a_tag.get_text().strip()
        if href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        if not href.startswith("http"):
            href = urljoin(base_url, href)
        link_pairs.add((href, anchor_text))
    return link_pairs

async def save_links(session, page_id: int, links: set[tuple[str, str]], base_domain: str):
    for target_url, anchor_text in links:
        is_external = urlparse(target_url).netloc != base_domain
        link = Link(
            source_page_id=page_id,
            target_url=target_url,
            anchor_text=anchor_text,
            is_external=is_external,
        )
        session.add(link)
    await session.commit()