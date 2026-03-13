"""
PyProspector — B2B Lead Prospecting Tool via Google Maps
=========================================================
Stack : Python · Playwright · playwright-stealth · Streamlit · Pandas · openpyxl

Scraping flow (2 phases):
  Phase 1 → Searches "{niche} {city}" on Maps, scrolls the feed and collects place URLs
  Phase 2 → Visits each URL individually and extracts the establishment details

Fitness score for web dev / digital marketing services:
  base  = (rating × 10) × (number_of_reviews / 100)
  final = base × 2.5   →  no website  (high priority 🔥)
  final = base          →  has website
"""

from __future__ import annotations

import io
import random
import re
import time
from urllib.parse import quote_plus, urljoin

import pandas as pd
import streamlit as st
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from playwright.sync_api import TimeoutError as PWTimeout
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

# ── Page configuration ───────────────────────────────────────────────────────
st.set_page_config(
    page_title="PyProspector – Leads B2B",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Constants ────────────────────────────────────────────────────────────────
MAPS_SEARCH_URL = "https://www.google.com/maps/search/"
MAPS_BASE_URL   = "https://www.google.com"

# Pool of real user-agents for rotation and reduced detection
USER_AGENTS = [
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/132.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) "
        "Gecko/20100101 Firefox/133.0"
    ),
]


# ══════════════════════════════════════════════════════════════════════════════
# UTILITIES
# ══════════════════════════════════════════════════════════════════════════════

def _delay(min_s: float = 0.8, max_s: float = 2.2) -> None:
    """Random pause to simulate human rhythm and avoid rate limiting."""
    time.sleep(random.uniform(min_s, max_s))


def _parse_float(text: str) -> float:
    """Safely converts '4,6' or '4.6' to float."""
    cleaned = text.strip().replace(",", ".")
    m = re.search(r"\d+\.?\d*", cleaned)
    return float(m.group()) if m else 0.0


def _parse_int(text: str) -> int:
    """Extracts the first sequence of digits from a string."""
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else 0


def _safe_text(locator) -> str:
    """Returns inner_text of a Playwright locator or '' on error."""
    try:
        return locator.inner_text(timeout=3_000).strip()
    except Exception:
        return ""


def _safe_attr(locator, attr: str) -> str:
    """Returns an attribute of a Playwright locator or '' on error."""
    try:
        return (locator.get_attribute(attr, timeout=3_000) or "").strip()
    except Exception:
        return ""


# ══════════════════════════════════════════════════════════════════════════════
# SCRAPING — helper functions
# ══════════════════════════════════════════════════════════════════════════════

def _handle_consent(page) -> None:
    """Accepts Google cookie consent banners if present."""
    for text in ["Aceitar tudo", "Accept all", "Concordo", "Agree"]:
        try:
            btn = page.get_by_role("button", name=re.compile(text, re.I)).first
            if btn.is_visible(timeout=2_000):
                btn.click()
                _delay(1.0, 2.0)
                return
        except Exception:
            pass


def _collect_place_urls(page, target: int) -> list[str]:
    """
    Scrolls the Maps results feed and collects unique place URLs.

    Strategy:
    - Finds anchors whose href contains '/maps/place/'
    - Strips tracking query parameters (keeps only the base path)
    - Stops scrolling when `target` URLs are reached or after 8 iterations with no new results

    Returns a list of absolute URLs (at most `target` items).
    """
    seen: set[str] = set()
    no_new_iters = 0

    while len(seen) < target and no_new_iters < 8:
        anchors = page.query_selector_all(
            "div[role='feed'] a[href*='/maps/place/']"
        )
        prev_len = len(seen)

        for anchor in anchors:
            href = anchor.get_attribute("href") or ""
            if not href:
                continue
            # Ensure the URL is absolute
            full_url = (
                href if href.startswith("http")
                else urljoin(MAPS_BASE_URL, href)
            )
            # Strip query string parameters (tracking, etc.)
            clean_url = re.split(r"\?", full_url)[0]
            seen.add(clean_url)

        if len(seen) == prev_len:
            no_new_iters += 1
        else:
            no_new_iters = 0

        # Scroll the feed to load more results
        try:
            page.evaluate(
                "document.querySelector(\"div[role='feed']\").scrollBy(0, 1200)"
            )
        except Exception:
            break

        _delay(1.5, 2.8)

    return list(seen)[:target]


def _extract_place_data(page) -> dict | None:
    """
    Extracts all relevant fields from a Google Maps place page.

    Uses multiple CSS selectors with fallbacks for resilience
    against Google Maps layout changes.

    Returns a dict with the fields or None if the name cannot be extracted.
    """
    # Wait for the main title to load
    try:
        page.wait_for_selector("h1", timeout=10_000)
    except PWTimeout:
        return None

    # ── Name ──────────────────────────────────────────────────────────────────
    name = _safe_text(page.locator("h1").first)
    if not name:
        return None

    # ── Category ──────────────────────────────────────────────────────────────
    category = ""
    for sel in [
        "button.DkEaL",
        "span.YkuOqf",
        "div.LBgpqf button",
        "[class*='fontBodyMedium'] button",
    ]:
        try:
            el = page.query_selector(sel)
            if el:
                category = el.inner_text().strip()
                break
        except Exception:
            pass

    # ── Rating and Reviews ─────────────────────────────────────────────────────
    # The 'F7nice' block typically contains: span(4.6) + span((1,234))
    rating  = 0.0
    reviews = 0
    try:
        nice_block = page.query_selector("div.F7nice")
        if nice_block:
            for sp in nice_block.query_selector_all("span"):
                txt = sp.inner_text().strip()
                if re.match(r"^\d[,\.]\d$", txt):
                    rating = _parse_float(txt)
                elif re.search(r"\([\d\s\.,]+\)", txt):
                    reviews = _parse_int(re.sub(r"[^\d]", "", txt))
    except Exception:
        pass

    # ── Address ───────────────────────────────────────────────────────────────
    address = ""
    try:
        # data-item-id="address" is the most stable selector
        addr_btn = page.query_selector("button[data-item-id='address']")
        if addr_btn:
            address = addr_btn.inner_text().strip().split("\n")[0]
        else:
            for lbl in ["Endereço", "Address"]:
                try:
                    el = page.get_by_label(re.compile(lbl, re.I)).first
                    raw = _safe_attr(el, "aria-label") or _safe_text(el)
                    address = re.sub(r"^[Ee]ndere[çc]o[:\s]*", "", raw).strip()
                    if address:
                        break
                except Exception:
                    pass
    except Exception:
        pass

    # ── Phone ─────────────────────────────────────────────────────────────────
    phone = ""
    try:
        # data-item-id starts with 'phone:tel:' on Maps
        phone_btn = page.query_selector("button[data-item-id^='phone:tel:']")
        if phone_btn:
            phone = phone_btn.inner_text().strip().split("\n")[0]
        else:
            for lbl in ["Telefone", "Phone number", "Call phone"]:
                try:
                    el = page.get_by_label(re.compile(lbl, re.I)).first
                    raw = _safe_attr(el, "aria-label") or _safe_text(el)
                    phone = re.sub(r"^[Tt]elefone[:\s]*", "", raw).strip()
                    if phone:
                        break
                except Exception:
                    pass
    except Exception:
        pass

    # ── Website ───────────────────────────────────────────────────────────────
    website = ""
    try:
        # data-item-id="authority" is the link to the external website
        web_a = page.query_selector("a[data-item-id='authority']")
        if web_a:
            website = _safe_attr(web_a, "href") or _safe_text(web_a)
        else:
            for sel in [
                "a[aria-label*='site' i][href*='http']",
                "a[aria-label*='website' i][href*='http']",
                "a[aria-label*='web' i][href*='http']",
            ]:
                try:
                    el = page.query_selector(sel)
                    if el:
                        website = _safe_attr(el, "href")
                        break
                except Exception:
                    pass
    except Exception:
        pass

    return {
        "name":     name,
        "category": category,
        "address":  address,
        "phone":    phone,
        "website":  website,
        "rating":   rating,
        "reviews":  reviews,
    }


# ══════════════════════════════════════════════════════════════════════════════
# SCRAPING — main function
# ══════════════════════════════════════════════════════════════════════════════

def scrape_google_maps(
    niche: str,
    city: str,
    max_results: int = 50,
    min_rating: float = 0.0,
    progress_callback=None,
) -> list[dict]:
    """
    Scrapes establishments from Google Maps using Playwright + stealth.

    Two-phase flow:
      1. Opens the search, scrolls the feed and collects place URLs.
      2. Visits each URL individually and extracts name, category, address,
         phone, website, rating and number of reviews.

    Args:
        niche:             Business segment (e.g. "dentists").
        city:              Location (e.g. "São Paulo, Brasil").
        max_results:       Maximum number of leads to extract.
        min_rating:        Minimum rating filter (0.0 = no filter).
        progress_callback: Callable(current: int, total: int) for progress.

    Returns:
        List of dicts, one per lead found.
    """
    leads: list[dict] = []
    query      = f"{niche} {city}"
    search_url = MAPS_SEARCH_URL + quote_plus(query)
    ua         = random.choice(USER_AGENTS)

    with sync_playwright() as pw:
        # Command-line arguments to reduce automation fingerprints
        browser = pw.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--disable-extensions",
                "--window-size=1366,768",
            ],
        )

        ctx = browser.new_context(
            user_agent=ua,
            viewport={"width": 1366, "height": 768},
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
        )
        page = ctx.new_page()

        # Apply stealth patches (removes navigator.webdriver, etc.)
        Stealth().apply_stealth_sync(page)

        # Block images and fonts to reduce bandwidth usage and latency
        page.route(
            re.compile(r"\.(png|jpg|jpeg|gif|webp|svg|woff2?|ttf|otf)(\?|$)", re.I),
            lambda route, _req: route.abort(),
        )

        try:
            # ── PHASE 1: Collect place URLs ────────────────────────────────────
            page.goto(search_url, wait_until="domcontentloaded", timeout=30_000)
            _delay(2.5, 4.0)
            _handle_consent(page)

            try:
                page.wait_for_selector("div[role='feed']", timeout=20_000)
            except PWTimeout:
                st.warning(
                    "The results panel did not load. "
                    "Check the niche/city or try again in a moment."
                )
                return leads

            place_urls = _collect_place_urls(page, max_results)
            if not place_urls:
                st.warning("No results found for this search.")
                return leads

            # ── PHASE 2: Visit each place and extract details ─────────────────
            for i, url in enumerate(place_urls):
                if i > 0:
                    _delay(1.2, 2.8)   # be respectful between requests

                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=25_000)
                    _delay(1.5, 3.0)

                    data = _extract_place_data(page)
                    if data is None:
                        continue

                    # Apply minimum rating filter if configured
                    if min_rating > 0.0 and data["rating"] < min_rating:
                        continue

                    leads.append(data)

                    if progress_callback:
                        progress_callback(len(leads), len(place_urls))

                except PWTimeout:
                    continue   # page took too long → skip
                except Exception:
                    continue   # any other error → skip

        except Exception as exc:
            st.error(f"Unexpected error during scraping: {exc}")

        finally:
            ctx.close()
            browser.close()

    return leads


# ══════════════════════════════════════════════════════════════════════════════
# DATA PROCESSING
# ══════════════════════════════════════════════════════════════════════════════

def process_data(raw: list[dict]) -> pd.DataFrame:
    """
    Converts the raw leads list into an enriched DataFrame.

    Operations:
    - Type normalisation (rating → float, reviews → int)
    - has_website column (bool)
    - Fitness score calculation for web dev / digital marketing
    - Descending sort by score

    Score:
        base  = (rating × 10) × (reviews / 100)
        final = base × 2.5  →  NO website (🔥 high priority)
        final = base         →  has website
    """
    if not raw:
        return pd.DataFrame(
            columns=[
                "name", "category", "address", "phone",
                "website", "has_website", "rating", "reviews", "score",
            ]
        )

    df = pd.DataFrame(raw)

    # Normalise types
    df["rating"]  = pd.to_numeric(df["rating"],  errors="coerce").fillna(0.0)
    df["reviews"] = (
        pd.to_numeric(df["reviews"], errors="coerce").fillna(0).astype(int)
    )
    df["website"] = df.get("website", "").fillna("").str.strip()

    # Digital presence indicator
    df["has_website"] = df["website"].str.len() > 0

    # Score calculation using the specified formula
    base = (df["rating"] * 10) * (df["reviews"] / 100)
    df["score"] = base.where(df["has_website"], base * 2.5).round(2)

    # Sort by score (highest priority first)
    df = df.sort_values("score", ascending=False).reset_index(drop=True)

    # Column display order
    ordered = [
        "name", "category", "address", "phone",
        "website", "has_website", "rating", "reviews", "score",
    ]
    return df[[c for c in ordered if c in df.columns]]


# ══════════════════════════════════════════════════════════════════════════════
# EXPORT
# ══════════════════════════════════════════════════════════════════════════════

# Column name mapping for the output language
_COL_LABELS = {
    "name":        "Nome",
    "category":    "Categoria",
    "address":     "Endereço",
    "phone":       "Telefone",
    "website":     "Website",
    "has_website": "Tem Website?",
    "rating":      "Rating (★)",
    "reviews":     "Nº Avaliações",
    "score":       "Score",
}


def generate_excel(df: pd.DataFrame) -> bytes:
    """
    Generates a formatted Excel (.xlsx) file with openpyxl.

    Formatting:
    - Header: blue background (#2E75B6) + bold + white text
    - Rows WITHOUT a website: light green background (#C6EFCE) — signals opportunity
    - Header frozen at row 1
    - Column widths auto-adjusted to content
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Leads B2B"

    header_fill  = PatternFill("solid", fgColor="2E75B6")
    header_font  = Font(bold=True, color="FFFFFF", size=11)
    no_site_fill = PatternFill("solid", fgColor="C6EFCE")   # no website
    c_align      = Alignment(horizontal="center", vertical="center", wrap_text=True)
    l_align      = Alignment(horizontal="left",   vertical="center", wrap_text=True)

    headers = [_COL_LABELS.get(c, c) for c in df.columns]

    # Header row
    for col_i, header in enumerate(headers, 1):
        cell            = ws.cell(row=1, column=col_i, value=header)
        cell.fill       = header_fill
        cell.font       = header_font
        cell.alignment  = c_align

    # Data rows
    for row_i, row in enumerate(df.itertuples(index=False), 2):
        has_site  = getattr(row, "has_website", True)
        row_fill  = None if has_site else no_site_fill

        for col_i, val in enumerate(row, 1):
            cell           = ws.cell(row=row_i, column=col_i, value=val)
            cell.alignment = l_align
            if row_fill:
                cell.fill = row_fill

    # Auto-adjust column widths
    for col in ws.columns:
        max_w = max(
            (len(str(c.value)) for c in col if c.value is not None),
            default=10,
        )
        ws.column_dimensions[col[0].column_letter].width = min(max_w + 4, 60)

    ws.freeze_panes = "A2"   # freeze header when scrolling

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def generate_tsv(df: pd.DataFrame) -> bytes:
    """Generates TSV (tab-separated values) content with translated headers."""
    return (
        df.rename(columns=_COL_LABELS)
        .to_csv(sep="\t", index=False)
        .encode("utf-8")
    )


# ══════════════════════════════════════════════════════════════════════════════
# STREAMLIT INTERFACE
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    # ── Header ────────────────────────────────────────────────────────────────
    c_logo, c_title = st.columns([1, 9])
    with c_logo:
        st.markdown("## 🎯")
    with c_title:
        st.title("PyProspector")
        st.caption(
            "Prospecção de Leads B2B via Google Maps · "
            "Playwright + Streamlit · Scraping Ético"
        )
    st.divider()

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.header("⚙️ Parâmetros de Busca")
        st.markdown("---")

        niche = st.text_input(
            "🏷️ Nicho / Segmento",
            placeholder="ex: dentistas, clínicas, advogados",
            help="Tipo de negócio que deseja prospectar.",
        )
        city = st.text_input(
            "📍 Cidade / País",
            placeholder="ex: São Paulo, Brasil",
            help="Localização para a busca no Google Maps.",
        )
        max_results = st.slider(
            "🔢 Máx. de resultados",
            min_value=5,
            max_value=100,
            value=50,
            step=5,
        )
        min_rating = st.slider(
            "⭐ Rating mínimo  (0 = todos)",
            min_value=0.0,
            max_value=5.0,
            value=0.0,
            step=0.5,
        )

        st.markdown("---")
        run = st.button(
            "🚀 Prospectar Leads",
            type="primary",
            use_container_width=True,
            disabled=not (niche.strip() and city.strip()),
        )
        if not (niche.strip() and city.strip()):
            st.caption("⬆ Preencha o nicho e a cidade para ativar.")

    # ── Results area ──────────────────────────────────────────────────────────
    if run:
        niche = niche.strip()
        city  = city.strip()

        info_box = st.info(
            f"🔍 Buscando **{niche}** em **{city}** "
            f"— até **{max_results}** resultados…"
        )
        progress = st.progress(0, text="Iniciando scraping…")
        status   = st.empty()

        collected: list[dict] = []

        def on_progress(current: int, total: int) -> None:
            pct = min(current / max(total, 1), 1.0)
            progress.progress(pct, text=f"{current}/{total} leads coletados…")
            if collected:
                status.caption(f"Último coletado: **{collected[-1]['name']}**")

        # Run the scraper (may take a few minutes)
        try:
            collected = scrape_google_maps(
                niche=niche,
                city=city,
                max_results=max_results,
                min_rating=min_rating,
                progress_callback=on_progress,
            )
        except Exception as exc:
            st.error(f"Erro crítico: {exc}")
            st.stop()
        finally:
            progress.empty()
            status.empty()
            info_box.empty()

        if not collected:
            st.warning(
                "No leads were collected. Suggestions:\n"
                "- Check the spelling of the niche and city\n"
                "- Lower the minimum rating\n"
                "- Google Maps may have temporarily throttled requests — try again"
            )
            st.stop()

        # Process and display
        df = process_data(collected)

        # ── Quick metrics ─────────────────────────────────────────────────────
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("📋 Leads coletados",  len(df))
        m2.metric("🚫 Sem website",      int((~df["has_website"]).sum()))
        m3.metric("⭐ Rating médio",      f"{df['rating'].mean():.1f}")
        m4.metric("🏆 Top score",         f"{df['score'].max():.1f}")

        st.success(f"✅ {len(df)} leads processados e ordenados por score!")
        st.divider()

        # ── Interactive table ──────────────────────────────────────────────────
        st.subheader("📊 Resultados (ordenados por score)")

        max_score = df["score"].max() or 1.0
        col_cfg = {
            "name":        st.column_config.TextColumn("Nome",       width="medium"),
            "category":    st.column_config.TextColumn("Categoria",  width="small"),
            "address":     st.column_config.TextColumn("Endereço",   width="large"),
            "phone":       st.column_config.TextColumn("Telefone",   width="small"),
            "website":     st.column_config.LinkColumn("Website",    width="medium"),
            "has_website": st.column_config.CheckboxColumn("Tem Site?"),
            "rating":      st.column_config.NumberColumn("★ Rating", format="%.1f"),
            "reviews":     st.column_config.NumberColumn("Avaliações"),
            "score":       st.column_config.ProgressColumn(
                               "Score", max_value=max_score, format="%.1f"
                           ),
        }

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config=col_cfg,
            height=520,
        )

        # ── Download buttons ───────────────────────────────────────────────────
        st.divider()
        st.subheader("⬇️ Exportar dados")

        slug = (
            f"leads_{niche.replace(' ', '_')}_"
            f"{city.split(',')[0].strip().replace(' ', '_')}"
        )

        dl1, dl2 = st.columns(2)

        with dl1:
            st.download_button(
                label="📥 Baixar Excel (.xlsx)",
                data=generate_excel(df),
                file_name=f"{slug}.xlsx",
                mime=(
                    "application/vnd.openxmlformats-officedocument"
                    ".spreadsheetml.sheet"
                ),
                use_container_width=True,
            )

        with dl2:
            st.download_button(
                label="📄 Baixar Texto Tabulado (.tsv)",
                data=generate_tsv(df),
                file_name=f"{slug}.tsv",
                mime="text/tab-separated-values",
                use_container_width=True,
            )

        # ── Score explanation ──────────────────────────────────────────────────
        with st.expander("ℹ️ Como o Score é calculado?"):
            st.markdown(
                """
                **Fórmula de adequação para web dev / marketing digital:**
                ```
                score_base  = (rating × 10) × (nº_avaliações / 100)
                score_final = score_base × 2.5   →  SEM website (🔥 alta prioridade)
                score_final = score_base           →  COM website
                ```
                Leads **sem website** que têm bom rating e alto volume de avaliações
                representam negócios consolidados com lacuna digital — os melhores
                candidatos para criação de sites, SEO e marketing digital.

                > **Dica:** foque nos leads verdes na planilha Excel — são os que
                > não têm presença digital e aparecem primeiro na lista.
                """
            )

    else:
        # ── Welcome / home screen ────────────────────────────────────────────────
        st.markdown(
            """
            ### Como usar o PyProspector

            | Etapa | Ação |
            |:-----:|------|
            | 1️⃣ | Preencha o **nicho** na barra lateral (ex: *escritórios de advocacia*) |
            | 2️⃣ | Informe a **cidade/país**  (ex: *Belo Horizonte, Brasil*) |
            | 3️⃣ | Ajuste a quantidade máxima e o rating mínimo |
            | 4️⃣ | Clique em **🚀 Prospectar Leads** e aguarde |

            ---

            **Casos de uso ideais:**
            - Agências de web design prospectando PMEs sem presença digital
            - Freelancers de SEO / tráfego pago buscando novos clientes
            - Consultores de marketing digital em busca de oportunidades locais
            - Equipes de vendas realizando prospecção outbound B2B

            ---

            > ⚠️ **Uso responsável:** utilize esta ferramenta com moderação e
            > respeite os [Termos de Uso do Google Maps](https://maps.google.com/help/terms_maps/).
            > Este projeto tem fins educacionais e de automação ética.
            """
        )


if __name__ == "__main__":
    main()
