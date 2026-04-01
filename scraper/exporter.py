import pandas as pd
import re
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from scraper.models import Page
from scraper.models import Link
import io


async def get_data_for_export(session: AsyncSession, crawl_job_id: int):
    page_query = await session.execute(
        select(
            Page.url,
            Page.title,
            Page.description,
            Page.status_code,
            Page.error,
            Page.body,
        ).where(Page.job_id == crawl_job_id)
    )
    link_query = await session.execute(
        select(Link.target_url, Link.anchor_text).where(
            Link.source_page.has(Page.job_id == crawl_job_id)
        )
    )
    page_data = page_query.fetchall()
    link_data = link_query.fetchall()
    df = pd.DataFrame(
        page_data,
        columns=["page_url", "title", "description", "status_code", "error", "body"],
    )
    df.loc[:, "body"] = df["body"].str.replace(r"\s+", " ", regex=True).str.strip()
    link_df = pd.DataFrame(link_data, columns=["target_url", "anchor_text"])
    link_df.loc[:, "anchor_text"] = (
        link_df["anchor_text"].str.replace(r"\s+", " ", regex=True).str.strip()
    )

    return df, link_df


async def export_to_csv(
    session: AsyncSession, crawl_job_id: int, output_file: str
) -> None:
    df, link_df = await get_data_for_export(session, crawl_job_id)
    df.to_csv(output_file, index=False, lineterminator="\r\n")
    link_df.to_csv(
        output_file.replace(".csv", "_links.csv"), index=False, lineterminator="\r\n"
    )
    print(f"Exported crawl results to {output_file}")


async def export_to_excel(
    session: AsyncSession, crawl_job_id: int, output_file: str
) -> None:
    df, link_df = await get_data_for_export(session, crawl_job_id)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        clean_illegal_chars(df).to_excel(writer, sheet_name="Pages", index=False)
        clean_illegal_chars(link_df).to_excel(writer, sheet_name="Links", index=False)
    print(f"Exported crawl results to {output_file}")


def clean_illegal_chars(df: pd.DataFrame) -> pd.DataFrame:
    return df.map(
        lambda x: (
            re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", x) if isinstance(x, str) else x
        )
    )
