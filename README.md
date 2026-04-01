# WebCrawler

A Python web crawler built for exploration purposes. It crawls websites within a given domain, stores structured data in a database, and provides both a CLI and an interactive dashboard for inspection and export.

---

## Features

* **Domain-restricted crawling** — stays within the seed domain to avoid runaway traversal
* **Configurable depth** — control how deep the crawler goes via CLI flag
* **Configurable concurrency** — multi-worker async crawling with queue locking
* **robots.txt compliance** — respects crawl delays and disallow rules using `Protego`
* **JS detection heuristics** — identifies pages that require JavaScript rendering
* **Playwright support** — renders JS-heavy pages when needed
* **Hybrid crawling** — automatically switches between static and JS rendering
* **Async engine** — built on `asyncio` + `httpx` with a shared `AsyncClient` for efficiency
* **Persistent queue system** — database-backed queue with row-level locking (`FOR UPDATE SKIP LOCKED`)
* **Persistent storage** — SQLAlchemy 2.0 async with PostgreSQL
* **Export** — results exportable to CSV or Excel (`.xlsx`) per crawl job
* **Streamlit dashboard** — visual interface to browse and inspect crawl results
* **Error tracking** — stores crawl failures and HTTP errors for inspection

---

## Project Structure

```
WebCrawler/
├── scraper/
│   ├── engine.py        # Core crawl logic (workers, queue, orchestration)
│   ├── db.py            # DB init and session factory (SQLAlchemy async)
│   ├── models.py        # ORM models (Page, Link, Queue, CrawlJob)
│   ├── exporter.py      # CSV and Excel export
│   ├── spiders/         # Crawling strategies (static + JS)
│   └── ...
├── dashboard/
│   └── app.py           # Streamlit dashboard
├── main.py              # CLI entrypoint (Typer)
├── requirements.txt
└── .gitignore
```

---

## Installation

```bash
git clone https://github.com/GoncaloMarquesSerrano/WebCrawler.git
cd WebCrawler
pip install -r requirements.txt
```

> Python 3.11+ recommended.

---

## Database Setup (PostgreSQL + Docker)

This project uses PostgreSQL running in Docker.

### 1. Run PostgreSQL container

```bash
docker run --name crawler-db \ 
  -e POSTGRES_PASSWORD=crawler \
  -e POSTGRES_DB=crawler \
  -e POSTGRES_USER=crawler \
  -p 5432:5432 \
  -d postgres
```

---

### 2. Connection string

Default connection used in the project:

```bash
postgresql+asyncpg://crawler:crawler@localhost:5432/crawler
```

You can change it in:

```
scraper/db.py
dashboard/app.py
```

---

### 3. Initialize database

Tables are created automatically on first run:

```python
init_db()
```

---

## Usage

### Crawl a website

```bash
python main.py crawl https://example.com --depth 3 --workers 5
```

| Option      | Short | Default | Description                  |
| ----------- | ----- | ------- | ---------------------------- |
| `--depth`   | `-d`  | `3`     | Maximum crawl depth          |
| `--workers` | `-w`  | `5`     | Number of concurrent workers |
| `--delay` | `-dl` | `1.0`   | Delay between requests in seconds |
| `--max-pages` | `-mp` | `10000`   | Maximum number of pages to crawl |

---

### Export results

```bash
# Export to CSV
python main.py export-csv <crawl_job_id> --output results.csv

# Export to Excel
python main.py export-xlsx <crawl_job_id> --output results.xlsx
```

---

### Launch the dashboard

```bash
streamlit run dashboard/app.py
```

---

## Tech Stack

| Layer        | Library                                     |
| ------------ | ------------------------------------------- |
| CLI          | Typer + Rich                                |
| HTTP         | httpx (async)                               |
| JS rendering | Playwright                                  |
| HTML parsing | BeautifulSoup4                              |
| robots.txt   | Protego                                     |
| Database     | SQLAlchemy 2.0 async + asyncpg (PostgreSQL) |
| Export       | pandas + openpyxl                           |
| Dashboard    | Streamlit                                   |

---

## Roadmap

* [x] Async concurrency with multiple workers
* [x] PostgreSQL migration
* [x] Streamlit dashboard
* [ ] Full-text search over crawled pages
* [ ] Inverted index / indexing pipeline
* [ ] Relevance scoring

---

## License

MIT
