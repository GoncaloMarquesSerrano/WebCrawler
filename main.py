import typer
from scraper.engine import run_crawl
import asyncio
from scraper.db import init_db, get_session_factory

app = typer.Typer()

@app.command()
def crawl(
    url: str,
    depth: int = typer.Option(3, "--depth", "-d", help="Depth of crawling",),
):
    print(f"Crawling {url} with depth {depth}")
    asyncio.run(main(url, depth))
    
async def main(url, depth):
    await init_db()
    session_factory = get_session_factory()
    async with session_factory() as session:
        await run_crawl(url, session, depth)
    
if __name__ == "__main__":
    app()