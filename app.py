"""철강 원자재 대시보드 - Streamlit 앱.

실행:
    streamlit run app.py
"""

from __future__ import annotations

import plotly.express as px
import streamlit as st

import ai
import database as db
from data_collector import collect_all

st.set_page_config(page_title="철강 원자재 대시보드", page_icon="🔩", layout="wide")

DISCLAIMER = (
    "본 대시보드는 공개된 데이터를 수집해 참고용으로 제공합니다. "
    "각 수치의 정확성은 원 출처를 확인하시기 바라며, 투자·매매 판단의 근거로 사용하지 마십시오. "
    "AI 요약은 자동 생성된 것으로 오류가 있을 수 있습니다."
)


def format_price(price: float, currency: str) -> str:
    if currency == "KRW":
        return f"{price:,.0f}"
    return f"{price:,.2f}"


# ── Dashboard ───────────────────────────────────────────────────────────

def render_price_card(item: str, name: str) -> None:
    latest = db.get_latest_price(item)

    if latest is None:
        st.metric(name, "—")
        st.caption("⚠️ 데이터 소스 확보 중")
        if item == "scrap":
            st.caption(
                "국내 철스크랩의 공개 시계열 API 를 찾지 못했습니다. "
                "`data/scrap_manual.csv` 에 출처와 함께 입력하면 표시됩니다."
            )
        return

    previous = db.get_previous_price(item, latest["date"])
    delta = None
    if previous:
        change = latest["price"] - previous["price"]
        delta = f"{change:+,.2f} ({previous['date']} 대비)"

    st.metric(
        name,
        f"{format_price(latest['price'], latest['currency'])} {latest['unit']}",
        delta=delta,
    )
    if latest["spec"]:
        st.caption(f"규격: {latest['spec']}")
    st.caption(f"기준일: **{latest['date']}**")
    badge = "✍️ 수기 입력" if latest["source_type"] == "manual" else "🔄 자동 수집"
    st.caption(f"{badge} · 출처: [{latest['source']}]({latest['source_url']})")


def render_dashboard() -> None:
    st.header("Dashboard")

    columns = st.columns(len(db.ITEMS))
    for column, (item, name) in zip(columns, db.ITEMS.items()):
        with column:
            render_price_card(item, name)

    st.divider()
    st.subheader("가격 추이")

    available = {
        item: name for item, name in db.ITEMS.items() if not db.get_price_history(item).empty
    }
    if not available:
        st.info("표시할 시계열 데이터가 없습니다. 사이드바에서 [데이터 수집]을 눌러주세요.")
        return

    selected_name = st.radio(
        "품목", list(available.values()), horizontal=True, label_visibility="collapsed"
    )
    selected_item = next(k for k, v in available.items() if v == selected_name)

    history = db.get_price_history(selected_item, limit=36)
    unit = history.iloc[-1]["unit"]

    figure = px.line(
        history, x="date", y="price", markers=True,
        labels={"date": "기준일", "price": unit},
    )
    figure.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=380, hovermode="x unified")
    st.plotly_chart(figure, width="stretch")

    first, last = history.iloc[0], history.iloc[-1]
    st.caption(
        f"기간: {first['date']:%Y-%m-%d} ~ {last['date']:%Y-%m-%d} · "
        f"{len(history)}개 시점 · 출처: [{last['source']}]({last['source_url']}) · "
        f"수집: {last['collected_at']}"
    )


# ── News ────────────────────────────────────────────────────────────────

def render_news() -> None:
    st.header("News")
    news = db.get_news(limit=60)

    if news.empty:
        st.info("수집된 뉴스가 없습니다. 사이드바에서 [데이터 수집]을 눌러주세요.")
        return

    sources = sorted(news["source"].dropna().unique())
    chosen = st.multiselect("출처 필터", sources, default=[], placeholder="전체 출처")
    if chosen:
        news = news[news["source"].isin(chosen)]

    st.caption(f"{len(news)}건 · 제목·날짜·출처·원문 링크만 표시합니다 (본문 미수록)")
    st.divider()

    for _, row in news.iterrows():
        date = row["published_at"] or "날짜 미상"
        st.markdown(f"**[{row['title']}]({row['url']})**")
        st.caption(f"{date} · {row['source']}")


# ── AI Summary ──────────────────────────────────────────────────────────

def render_summary() -> None:
    st.header("AI Summary")

    provider = ai.detect_provider()
    if provider is None:
        st.warning(
            "LLM API 키가 설정되지 않아 요약을 생성할 수 없습니다. "
            "Dashboard 와 News 는 정상 동작합니다.\n\n"
            "- 로컬 실행: `.env.example` 을 `.env` 로 복사하고 `OPENAI_API_KEY` 입력\n"
            "- Streamlit Cloud: 앱 **Settings → Secrets** 에 "
            "`OPENAI_API_KEY = \"sk-...\"` 추가"
        )
        return

    force = st.button("요약 다시 생성", help="캐시를 무시하고 모델을 다시 호출합니다")
    with st.spinner("요약 생성 중..."):
        result = ai.summarize(force=force)

    if result["status"] == "no_data":
        st.info("요약할 데이터가 없습니다. 사이드바에서 [데이터 수집]을 먼저 눌러주세요.")
        return
    if result["status"] == "error":
        st.error(f"요약 생성에 실패했습니다: {result['reason']}")
        return

    st.markdown(f"> {result['text']}")
    badge = "캐시됨" if result.get("cached") else "새로 생성"
    st.caption(
        f"ⓘ {result['model']} · {result['generated_at']} · {badge} · "
        "아래 근거 데이터만 사용해 생성되었습니다."
    )

    with st.expander("요약의 근거가 된 데이터 보기"):
        st.json(result["context"])


# ── 앱 ──────────────────────────────────────────────────────────────────

PAGES = {
    "Dashboard": render_dashboard,
    "News": render_news,
    "AI Summary": render_summary,
}


@st.cache_resource(show_spinner=False)
def bootstrap() -> dict | None:
    """DB 가 비어 있으면 최초 1회 자동 수집한다.

    Streamlit Cloud 처럼 steel.db 없이 배포되는 환경에서, 처음 접속한
    사람이 빈 화면을 보지 않도록 하기 위한 것이다.
    cache_resource 라 앱 인스턴스당 한 번만 돌고, 이후 방문자는 그대로 본다.
    """
    db.init_db()
    if db.get_last_collected_at() is not None:
        return None
    return collect_all()


def main() -> None:
    db.init_db()

    if db.get_last_collected_at() is None:
        with st.spinner("최초 데이터를 수집하고 있습니다. 30초 정도 걸립니다..."):
            first_run = bootstrap()
        if first_run and first_run["errors"] and first_run["prices"] == 0 and first_run["news"] == 0:
            st.error("데이터 수집에 실패했습니다. 사이드바에서 [데이터 수집]을 다시 눌러주세요.")
            for error in first_run["errors"]:
                st.caption(error)

    st.sidebar.title("🔩 철강 원자재")
    page = st.sidebar.radio("화면", list(PAGES), label_visibility="collapsed")
    st.sidebar.divider()

    if st.sidebar.button("데이터 수집", width="stretch"):
        with st.spinner("수집 중... (30초 정도 걸립니다)"):
            outcome = collect_all()
        st.sidebar.success(f"가격 {outcome['prices']}건 · 뉴스 {outcome['news']}건")
        for error in outcome["errors"]:
            st.sidebar.error(error)

    last = db.get_last_collected_at()
    st.sidebar.caption(f"마지막 수집: {last}" if last else "아직 수집 이력이 없습니다.")

    PAGES[page]()

    st.divider()
    st.caption(DISCLAIMER)


if __name__ == "__main__":
    main()
