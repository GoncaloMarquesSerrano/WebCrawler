# WebCrawler

A Python web crawler built for exploration purposes. It crawls websites within a given domain, stores structured data in a local database, and provides both a CLI and an interactive dashboard for inspection and export.

---

## Features

- **Domain-restricted crawling** — stays within the seed domain to avoid runaway traversal
- **Configurable depth** — control how deep the crawler goes via CLI flag
- **robots.txt compliance** — respects crawl delays and disallow rules using `Protego`
- **JS detection heuristics** — identifies pages that require JavaScript rendering
- **Playwright support** — renders JS-heavy pages when needed
- **Async engine** — built on `asyncio` + `httpx` with a shared `AsyncClient` for efficiency
- **Persistent storage** — SQLAlchemy 2.0 async (aiosqlite) for local SQLite storage
- **Export** — results exportable to CSV or Excel (`.xlsx`) per crawl job
- **Streamlit dashboard** — visual interface to browse and inspect crawl results

---

## Project Structure

```
WebCrawler/
├── scraper/
│   ├── engine.py        # Core crawl logic
│   ├── db.py            # DB init and session factory (SQLAlchemy async)
│   ├── models.py        # ORM models
│   ├── exporter.py      # CSV and Excel export
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

## Usage

### Crawl a website

```bash
python main.py crawl https://example.com --depth 3
```

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--depth` | `-d` | `3` | Maximum crawl depth |

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

| Layer | Library |
|---|---|
| CLI | [Typer](https://typer.tiangolo.com/) + [Rich](https://github.com/Textualize/rich) |
| HTTP | [httpx](https://www.python-httpx.org/) (async) |
| JS rendering | [Playwright](https://playwright.dev/python/) |
| HTML parsing | [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) |
| robots.txt | [Protego](https://github.com/scrapy/protego) |
| Database | SQLAlchemy 2.0 async + aiosqlite |
| Export | pandas + openpyxl |
| Dashboard | [Streamlit](https://streamlit.io/) |

---

## Roadmap

- [ ] Async concurrency with multiple workers
- [ ] Full-text search over crawled pages
- [ ] Inverted index / indexing pipeline
- [ ] Relevance scoring

---

## License

MIT
