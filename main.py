import typer
from scraper.engine import run_crawl
import asyncio
from scraper.db import init_db, get_session_factory
from scraper.exporter import export_to_csv
from scraper.exporter import export_to_excel

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
        
@app.command()
def export_csv(
    crawl_job_id: int,
    output_file: str = typer.Option("crawl_results.csv", "--output", "-o", help="Output CSV file path"),
):
    print(f"Exporting crawl job {crawl_job_id} results to {output_file}")
    asyncio.run(export_main(crawl_job_id, output_file))

async def export_main(crawl_job_id, output_file):
    await init_db()
    session_factory = get_session_factory()
    async with session_factory() as session:
        await export_to_csv(session, crawl_job_id, output_file)

@app.command()
def export_xlsx(
    crawl_job_id: int,
    output_file: str = typer.Option("crawl_results.xlsx", "--output", "-o", help="Output Excel file path"),
):
    print(f"Exporting crawl job {crawl_job_id} results to {output_file}")
    asyncio.run(export_excel_main(crawl_job_id, output_file))

async def export_excel_main(crawl_job_id, output_file):
    await init_db()
    session_factory = get_session_factory()
    async with session_factory() as session:
        await export_to_excel(session, crawl_job_id, output_file)

if __name__ == "__main__":
    app()