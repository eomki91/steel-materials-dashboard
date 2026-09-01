# 🔩 철강 원자재 대시보드

철강업계 실무자가 철광석·석탄 가격과 관련 뉴스를 한 화면에서 빠르게 확인하기 위한 Streamlit MVP.

- **Dashboard** — 가격 카드(최신값·증감·기준일·출처) + Plotly 추이 차트
- **News** — 철강/원자재 최신 뉴스 (제목·날짜·출처·원문 링크)
- **AI Summary** — 수집된 가격·뉴스만 근거로 한 3~5문장 시황 요약

## 실행

```bash
pip install -r requirements.txt
```

```bash
cp .env.example .env
```

`.env` 에 `OPENAI_API_KEY` 를 채운 뒤:

```bash
streamlit run app.py
```

**버튼을 누를 필요는 없습니다.** 데이터가 없거나 6시간이 지났으면 화면을 열 때 알아서 수집합니다
(처음 한 번은 30초 내외). 즉시 다시 받고 싶으면 사이드바의 **[지금 새로고침]** 을 누르세요.

> API 키가 없어도 앱은 실행됩니다. AI Summary 화면만 안내 문구로 대체되고 Dashboard·News 는 정상 동작합니다.

## 데이터 출처

모든 수치는 아래 출처에서 실제로 수집한 값입니다. **임의로 생성한 가격 데이터는 한 건도 없습니다.**

| 항목 | 출처 | 주기 | 비고 |
|---|---|---|---|
| 뉴스 | [스틸데일리 공식 RSS](https://www.steeldaily.co.kr/rss/allArticle.xml) | 수시 | 제목·날짜·링크만 저장, 본문 미수록 |
| 뉴스(보강) | Google News RSS | 수시 | 철광석/원료탄/철스크랩 키워드 |
| 철광석 | [World Bank Pink Sheet](https://www.worldbank.org/en/research/commodity-markets) | 월간 | `Iron ore, cfr spot` · 62% Fe, CFR China · USD/dmtu |
| 석탄 | World Bank Pink Sheet | 월간 | `Coal, Australian` · FOB Newcastle 6,000kcal/kg · USD/mt |

### 수집 원칙

- **스틸데일리**: `robots.txt` 는 `/admin/` 만 차단하며, 사용하는 RSS 는 배포 목적의 공식 피드입니다. 저작권을 고려해 제목·발행일·출처·원문 링크만 저장하고 기사 본문은 복제하지 않습니다. 가격표는 구독 영역이므로 수집하지 않습니다.
- 요청 사이에 1초 지연을 두고 `User-Agent` 를 명시합니다.
- 소스 하나가 실패해도 나머지는 정상 수집됩니다.

### 철스크랩이 없는 이유

국내 철스크랩은 **무료·공개 시계열 소스를 확보하지 못해 품목에서 제외했습니다.** 없는 데이터를 지어내지 않기 위한 결정입니다.

소스를 확보하면 되살리기 쉽게 만들어 뒀습니다.

1. `database.py` 의 `ITEMS` 에 `"scrap": "철스크랩"` 추가
2. `data_collector.py` 에 `prices` 스키마와 같은 형태의 `dict` 리스트를 반환하는 수집 함수 작성
3. `collect_all()` 에서 호출

나머지 화면·차트·요약 코드는 그대로 동작합니다. 참고로 값을 구할 수 있는 곳은 제강사 홈페이지의 철스크랩 매입가격 공지(현대제철/동국제강/환영철강 등)와 업계지 기사에 공표된 가격입니다.

## 구조

```
.
├── app.py              # Streamlit UI (3화면)
├── database.py         # SQLite 스키마 + 조회/저장
├── data_collector.py   # 가격·뉴스 수집기
├── ai.py               # LLM 요약 (OpenAI 우선, Anthropic 자동 감지)
├── requirements.txt
├── .env.example
├── .gitignore
├── .streamlit/
│   └── config.toml     # 테마
└── data/
    └── steel.db        # 자동 생성 (git 제외)
```

### 테이블

**prices** — `item`, `item_name`(상품명), `price`(가격), `currency`(통화), `unit`(단위), `spec`(규격), `date`(기준일), `source`(출처), `source_url`(출처 URL), `source_type`, `collected_at`
`UNIQUE(item, date, source)` 로 재수집 시 중복 없이 갱신됩니다.

**news** — `title`, `published_at`, `source`, `url`(UNIQUE), `collected_at`

**summaries** — `input_hash`(UNIQUE), `text`, `model`, `generated_at`
가격·뉴스가 그대로면 같은 해시가 나와 모델을 다시 호출하지 않습니다. 강제로 다시 만들려면 AI Summary 화면의 **[요약 다시 생성]** 을 누르세요.

## LLM 설정

`ai.py` 는 키가 있는 쪽을 자동으로 고릅니다 (OpenAI 우선). 로컬은 `.env`, 배포 환경은 `st.secrets` 를 읽습니다.

| 환경변수 | 기본 모델 | 추가 설치 |
|---|---|---|
| `OPENAI_API_KEY` | `gpt-4o-mini` (`OPENAI_MODEL` 로 변경) | — |
| `ANTHROPIC_API_KEY` | `claude-opus-5` (`ANTHROPIC_MODEL` 로 변경) | `pip install anthropic` |

요약 프롬프트에는 **수집이 끝난 데이터만** 들어가며, 제공되지 않은 수치를 언급하지 않도록 시스템 프롬프트로 제한합니다. 근거 데이터는 화면의 "요약의 근거가 된 데이터 보기" 에서 그대로 확인할 수 있습니다.

## 명령줄에서 수집만 실행

```bash
python data_collector.py
```

## Streamlit Community Cloud 배포

1. [share.streamlit.io](https://share.streamlit.io) 에서 **Sign in with GitHub**
2. **Create app → Deploy a public app from GitHub**
3. 입력값
   - Repository: `eomki91/steel-materials-dashboard`
   - Branch: `main`
   - Main file path: `app.py`
4. **Advanced settings → Secrets** 에 아래를 붙여넣기 (AI Summary 를 쓸 경우)

   ```toml
   OPENAI_API_KEY = "sk-..."
   ```

5. **Deploy**

`data/steel.db` 는 저장소에 없지만 첫 접속 시 앱이 자동으로 수집하므로 방문자가 빈 화면을 보지 않습니다.

> Secrets 를 비워두면 Dashboard 와 News 는 정상 동작하고 AI Summary 화면에만 안내가 표시됩니다.
> 배포 후에도 앱 메뉴의 **Settings → Secrets** 에서 언제든 추가/삭제할 수 있습니다.

## 문제 해결

**World Bank 수집이 404로 실패할 때** — 엑셀 URL 경로에 연도 코드가 포함되어 매년 바뀝니다. [Commodity Markets 페이지](https://www.worldbank.org/en/research/commodity-markets)에서 "Monthly prices (XLS)" 최신 링크를 복사해 `.env` 의 `WORLDBANK_XLSX_URL` 에 넣으세요.

**엑셀 열을 찾지 못한다는 오류** — Pink Sheet 양식이 바뀐 경우입니다. `data_collector.py` 의 `WORLDBANK_SERIES` 에 있는 열 이름(`Iron ore, cfr spot`, `Coal, Australian`)을 실제 시트 헤더와 맞춰주세요.

**AI Summary가 계속 같은 내용** — 캐시입니다. 데이터가 바뀌지 않으면 재호출하지 않습니다. [요약 다시 생성]을 누르세요.

## 면책

본 대시보드는 공개된 데이터를 수집해 참고용으로 제공합니다. 각 수치의 정확성은 원 출처를 확인하시기 바라며, 투자·매매 판단의 근거로 사용하지 마십시오. AI 요약은 자동 생성된 것으로 오류가 있을 수 있습니다.
