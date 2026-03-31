"""
WebCrawler Dashboard — Streamlit
Requires: streamlit, sqlalchemy, aiosqlite, pandas, openpyxl
Run: streamlit run dashboard.py
"""

import asyncio
import io
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
import streamlit as st
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from scraper.models import Base, CrawlJob, Link, Page

# ─── Config ──────────────────────────────────────────────────────────────────


DB_URL = "postgresql+asyncpg://crawler:crawler@localhost:5432/crawler"

st.set_page_config(
    page_title="WebCrawler Dashboard",
    page_icon="🕷️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Styling ─────────────────────────────────────────────────────────────────

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Syne:wght@400;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Syne', sans-serif;
    }
    code, .stDataFrame, .monospace {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Root palette */
    :root {
        --bg:       #0d0f12;
        --surface:  #13161b;
        --border:   #1e2330;
        --accent:   #00e5a0;
        --danger:   #ff4b6e;
        --warn:     #ffb547;
        --muted:    #4a5568;
        --text:     #e2e8f0;
    }

    .stApp { background: var(--bg); color: var(--text); }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: var(--surface);
        border-right: 1px solid var(--border);
    }
    [data-testid="stSidebar"] * { color: var(--text) !important; }

    /* Metric cards */
    [data-testid="stMetric"] {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 1.1rem 1.4rem;
    }
    [data-testid="stMetricLabel"] { color: var(--muted) !important; font-size: .8rem; letter-spacing: .08em; text-transform: uppercase; }
    [data-testid="stMetricValue"] { color: var(--accent) !important; font-family: 'JetBrains Mono', monospace; font-size: 2rem !important; }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 4px; border-bottom: 1px solid var(--border); }
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        color: var(--muted);
        border-radius: 6px 6px 0 0;
        font-size: .85rem;
        letter-spacing: .06em;
        padding: .5rem 1.1rem;
    }
    .stTabs [aria-selected="true"] {
        background: var(--border);
        color: var(--accent) !important;
        border-bottom: 2px solid var(--accent);
    }

    /* Dataframe */
    [data-testid="stDataFrame"] { border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }

    /* Buttons */
    .stDownloadButton > button, .stButton > button {
        background: transparent;
        border: 1px solid var(--accent);
        color: var(--accent);
        border-radius: 8px;
        font-family: 'JetBrains Mono', monospace;
        font-size: .8rem;
        letter-spacing: .05em;
        transition: all .15s;
    }
    .stDownloadButton > button:hover, .stButton > button:hover {
        background: var(--accent);
        color: #000;
    }

    /* Selectbox / inputs */
    .stSelectbox > div > div {
        background: var(--surface);
        border: 1px solid var(--border);
        color: var(--text);
        border-radius: 8px;
    }

    /* Section headers */
    h1, h2, h3 { font-family: 'Syne', sans-serif; }
    h1 { font-size: 1.6rem; font-weight: 800; letter-spacing: -.02em; }
    h3 { color: var(--muted); font-size: .75rem; text-transform: uppercase; letter-spacing: .12em; font-weight: 600; }

    /* Status badge helpers (applied via column_config) */
    </style>
    """,
    unsafe_allow_html=True,
)

# ─── Async helpers ────────────────────────────────────────────────────────────


@st.cache_resource
def get_engine():
    return create_async_engine(DB_URL, echo=False, poolclass=NullPool)


def get_session_factory():
    engine = get_engine()
    return sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def fetch_jobs() -> list[CrawlJob]:
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(CrawlJob).order_by(CrawlJob.started_at.desc())
        )
        return result.scalars().all()


async def fetch_metrics(job_id: int) -> dict:
    factory = get_session_factory()
    async with factory() as session:
        total = await session.scalar(
            select(func.count()).select_from(Page).where(Page.job_id == job_id)
        )
        errors = await session.scalar(
            select(func.count())
            .select_from(Page)
            .where(Page.job_id == job_id, Page.error.isnot(None))
        )
        js_pages = await session.scalar(
            select(func.count())
            .select_from(Page)
            .where(Page.job_id == job_id, Page.is_javascript.is_(True))
        )
        avg_load = await session.scalar(
            select(func.avg(Page.load_time_ms)).where(
                Page.job_id == job_id, Page.load_time_ms.isnot(None)
            )
        )
        return {
            "total": total or 0,
            "errors": errors or 0,
            "js_pages": js_pages or 0,
            "static_pages": (total or 0) - (js_pages or 0),
            "avg_load_ms": round(avg_load, 1) if avg_load else None,
        }


async def fetch_pages_df(job_id: int) -> pd.DataFrame:
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(
                Page.url,
                Page.title,
                Page.status_code,
                Page.depth,
                Page.load_time_ms,
                Page.is_javascript,
                Page.crawled_at,
                Page.redirected_from,
            ).where(Page.job_id == job_id)
        )
        rows = result.fetchall()
    return pd.DataFrame(
        rows,
        columns=[
            "url",
            "title",
            "status_code",
            "depth",
            "load_time_ms",
            "is_javascript",
            "crawled_at",
            "redirected_from",
        ],
    )


async def fetch_errors_df(job_id: int) -> pd.DataFrame:
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(Page.url, Page.status_code, Page.error, Page.depth)
            .where(Page.job_id == job_id, Page.error.isnot(None))
            .order_by(Page.depth)
        )
        rows = result.fetchall()
    return pd.DataFrame(rows, columns=["url", "status_code", "error", "depth"])


async def fetch_export_data(job_id: int):
    """Returns (pages_df, links_df) with full columns for export."""
    factory = get_session_factory()
    async with factory() as session:
        page_result = await session.execute(
            select(
                Page.url,
                Page.title,
                Page.description,
                Page.status_code,
                Page.error,
                Page.body,
                Page.depth,
                Page.load_time_ms,
                Page.is_javascript,
                Page.crawled_at,
            ).where(Page.job_id == job_id)
        )
        link_result = await session.execute(
            select(Link.target_url, Link.anchor_text, Link.is_external).where(
                Link.source_page.has(Page.job_id == job_id)
            )
        )

    pages_df = pd.DataFrame(
        page_result.fetchall(),
        columns=[
            "url",
            "title",
            "description",
            "status_code",
            "error",
            "body",
            "depth",
            "load_time_ms",
            "is_javascript",
            "crawled_at",
        ],
    )
    pages_df["body"] = pages_df["body"].str.replace(r"\s+", " ", regex=True).str.strip()

    links_df = pd.DataFrame(
        link_result.fetchall(),
        columns=["target_url", "anchor_text", "is_external"],
    )
    links_df["anchor_text"] = (
        links_df["anchor_text"].str.replace(r"\s+", " ", regex=True).str.strip()
    )

    return pages_df, links_df


def run(coro):
    """Run an async coroutine from sync Streamlit context."""
    return asyncio.run(coro)


# ─── Export helpers ───────────────────────────────────────────────────────────


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False, lineterminator="\r\n").encode("utf-8")


def to_excel_bytes(pages_df: pd.DataFrame, links_df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        pages_df.to_excel(writer, sheet_name="Pages", index=False)
        links_df.to_excel(writer, sheet_name="Links", index=False)
    return buf.getvalue()


# ─── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## WebCrawler")
    st.markdown("---")

    jobs = run(fetch_jobs())

    if not jobs:
        st.warning("Nenhum crawl job encontrado na base de dados.")
        st.stop()

    job_labels = {f"#{j.id} — {j.domain} [{j.status}]": j for j in jobs}
    selected_label = st.selectbox("Crawl Job", list(job_labels.keys()))
    selected_job: CrawlJob = job_labels[selected_label]

    st.markdown("---")
    st.markdown("### Detalhes")
    st.caption(f"**Seed URL**")
    st.code(selected_job.seed_url, language=None)
    st.caption(
        f"**Iniciado:** {selected_job.started_at.strftime('%Y-%m-%d %H:%M') if selected_job.started_at else '—'}"
    )
    st.caption(
        f"**Terminado:** {selected_job.finished_at.strftime('%Y-%m-%d %H:%M') if selected_job.finished_at else '—'}"
    )
    st.caption(
        f"**Max depth:** {selected_job.max_depth} | **Max pages:** {selected_job.max_pages}"
    )

    st.markdown("---")
    st.markdown("### Exportar")

    pages_df_export, links_df_export = run(fetch_export_data(selected_job.id))

    col_a, col_b = st.columns(2)
    with col_a:
        st.download_button(
            "CSV",
            data=to_csv_bytes(pages_df_export),
            file_name=f"job_{selected_job.id}_pages.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with col_b:
        st.download_button(
            "Excel",
            data=to_excel_bytes(pages_df_export, links_df_export),
            file_name=f"job_{selected_job.id}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    st.download_button(
        "CSV — Links",
        data=to_csv_bytes(links_df_export),
        file_name=f"job_{selected_job.id}_links.csv",
        mime="text/csv",
        use_container_width=True,
    )

# ─── Main area ────────────────────────────────────────────────────────────────

st.markdown(f"# {selected_job.domain}")
st.markdown(
    f"**Job #{selected_job.id}** &nbsp;·&nbsp; status: `{selected_job.status}`",
    unsafe_allow_html=True,
)
st.markdown("---")

metrics = run(fetch_metrics(selected_job.id))

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Páginas crawladas", metrics["total"])
m2.metric("Erros", metrics["errors"], delta=None)
m3.metric("JS (Playwright)", metrics["js_pages"])
m4.metric("Estáticas", metrics["static_pages"])
m5.metric(
    "Tempo médio (ms)",
    f"{metrics['avg_load_ms']}" if metrics["avg_load_ms"] is not None else "—",
)

st.markdown("")

tab_pages, tab_errors = st.tabs(["Páginas", "Erros"])

# ── Tab: Páginas ──────────────────────────────────────────────────────────────
with tab_pages:
    pages_df = run(fetch_pages_df(selected_job.id))

    if pages_df.empty:
        st.info("Sem páginas registadas para este job.")
    else:
        # Filters row
        fc1, fc2, fc3 = st.columns([2, 1, 1])
        with fc1:
            search = st.text_input("Filtrar URL / título", placeholder="ex: /blog")
        with fc2:
            status_filter = st.multiselect(
                "Status code",
                options=sorted(pages_df["status_code"].dropna().unique().tolist()),
            )
        with fc3:
            js_filter = st.selectbox("Tipo", ["Todos", "Estáticas", "JavaScript"])

        df_view = pages_df.copy()
        if search:
            mask = df_view["url"].str.contains(search, case=False, na=False) | df_view[
                "title"
            ].str.contains(search, case=False, na=False)
            df_view = df_view[mask]
        if status_filter:
            df_view = df_view[df_view["status_code"].isin(status_filter)]
        if js_filter == "Estáticas":
            df_view = df_view[df_view["is_javascript"] == False]
        elif js_filter == "JavaScript":
            df_view = df_view[df_view["is_javascript"] == True]

        st.caption(f"{len(df_view)} resultado(s)")

        st.dataframe(
            df_view[
                [
                    "url",
                    "title",
                    "status_code",
                    "depth",
                    "load_time_ms",
                    "is_javascript",
                    "crawled_at",
                ]
            ],
            use_container_width=True,
            hide_index=True,
            column_config={
                "url": st.column_config.LinkColumn("URL", display_text="abrir"),
                "title": st.column_config.TextColumn("Título", width="medium"),
                "status_code": st.column_config.NumberColumn("Status", format="%d"),
                "depth": st.column_config.NumberColumn("Profundidade", format="%d"),
                "load_time_ms": st.column_config.NumberColumn(
                    "Load (ms)", format="%.1f"
                ),
                "is_javascript": st.column_config.CheckboxColumn("JS?"),
                "crawled_at": st.column_config.DatetimeColumn(
                    "Crawled at", format="YYYY-MM-DD HH:mm"
                ),
            },
        )

# ── Tab: Erros ────────────────────────────────────────────────────────────────
with tab_errors:
    errors_df = run(fetch_errors_df(selected_job.id))

    if errors_df.empty:
        st.success("Sem erros registados.")
    else:
        st.caption(f"{len(errors_df)} erro(s) encontrado(s)")

        err_search = st.text_input(
            "Filtrar por URL ou mensagem de erro", key="err_search"
        )
        df_err_view = errors_df.copy()
        if err_search:
            mask = df_err_view["url"].str.contains(
                err_search, case=False, na=False
            ) | df_err_view["error"].str.contains(err_search, case=False, na=False)
            df_err_view = df_err_view[mask]

        st.dataframe(
            df_err_view,
            use_container_width=True,
            hide_index=True,
            column_config={
                "url": st.column_config.LinkColumn("URL", display_text="abrir"),
                "status_code": st.column_config.NumberColumn("Status", format="%d"),
                "error": st.column_config.TextColumn("Erro", width="large"),
                "depth": st.column_config.NumberColumn("Profundidade", format="%d"),
            },
        )
