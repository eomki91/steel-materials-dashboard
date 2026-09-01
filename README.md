# 🔩 철강 원자재 대시보드

철강업계 실무자가 스크랩·철광석·석탄 가격과 관련 뉴스를 한 화면에서 빠르게 확인하기 위한 Streamlit MVP.

- **Dashboard** — 가격 카드 3종(최신값·증감·기준일·출처) + Plotly 추이 차트
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

브라우저가 열리면 **사이드바의 [데이터 수집]** 을 한 번 눌러주세요. 첫 수집은 30초 정도 걸립니다.

> API 키가 없어도 앱은 실행됩니다. AI Summary 화면만 안내 문구로 대체되고 Dashboard·News 는 정상 동작합니다.

## 데이터 출처

모든 수치는 아래 출처에서 실제로 수집한 값입니다. **임의로 생성한 가격 데이터는 한 건도 없습니다.**

| 항목 | 출처 | 주기 | 비고 |
|---|---|---|---|
| 뉴스 | [스틸데일리 공식 RSS](https://www.steeldaily.co.kr/rss/allArticle.xml) | 수시 | 제목·날짜·링크만 저장, 본문 미수록 |
| 뉴스(보강) | Google News RSS | 수시 | 철광석/원료탄/철스크랩 키워드 |
| 철광석 | [World Bank Pink Sheet](https://www.worldbank.org/en/research/commodity-markets) | 월간 | `Iron ore, cfr spot` · 62% Fe, CFR China · USD/dmtu |
| 석탄 | World Bank Pink Sheet | 월간 | `Coal, Australian` · FOB Newcastle 6,000kcal/kg · USD/mt |
| 철스크랩 | `data/scrap_manual.csv` (수기 입력) | 수동 | 아래 참고 |

### 수집 원칙

- **스틸데일리**: `robots.txt` 는 `/admin/` 만 차단하며, 사용하는 RSS 는 배포 목적의 공식 피드입니다. 저작권을 고려해 제목·발행일·출처·원문 링크만 저장하고 기사 본문은 복제하지 않습니다. 가격표는 구독 영역이므로 수집하지 않습니다.
- 요청 사이에 1초 지연을 두고 `User-Agent` 를 명시합니다.
- 소스 하나가 실패해도 나머지는 정상 수집됩니다. 실패는 사이드바에 표시됩니다.

### 철스크랩에 대하여

국내 철스크랩의 **무료·공개 시계열 API 를 찾지 못했습니다.** 없는 API 를 가정하는 대신, 출처를 확인한 실제 공표 가격만 `data/scrap_manual.csv` 에 직접 입력하는 방식을 씁니다.

```csv
date,price,currency,unit,spec,source,source_url
2026-08-31,435000,KRW,KRW/t,생철A 중량A 도착도,환영철강 매입가격 공지,https://example.co.kr/notice/123
```

- `source` 와 `source_url` 이 없는 행은 저장되지 않습니다.
- 입력된 값은 Dashboard 에 **"✍️ 수기 입력"** 배지와 함께 표시되어 자동 수집분과 구분됩니다.
- 파일이 비어 있으면 카드에 **"데이터 소스 확보 중"** 이 표시됩니다. 임의의 값은 절대 넣지 마세요.

나중에 실제 소스를 확보하면 `data_collector.py` 의 `collect_scrap()` 본문만 교체하면 됩니다. 나머지 코드는 그대로 동작합니다.

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
└── data/
    ├── steel.db            # 자동 생성 (git 제외)
    └── scrap_manual.csv    # 스크랩 수기 입력
```

### 테이블

**prices** — `item`, `item_name`(상품명), `price`(가격), `currency`(통화), `unit`(단위), `spec`(규격), `date`(기준일), `source`(출처), `source_url`(출처 URL), `source_type`(auto/manual), `collected_at`
`UNIQUE(item, date, source)` 로 재수집 시 중복 없이 갱신됩니다.

**news** — `title`, `published_at`, `source`, `url`(UNIQUE), `collected_at`

**summaries** — `input_hash`(UNIQUE), `text`, `model`, `generated_at`
가격·뉴스가 그대로면 같은 해시가 나와 모델을 다시 호출하지 않습니다. 강제로 다시 만들려면 AI Summary 화면의 **[요약 다시 생성]** 을 누르세요.

## LLM 설정

`ai.py` 는 키가 있는 쪽을 자동으로 고릅니다 (OpenAI 우선).

| 환경변수 | 기본 모델 | 추가 설치 |
|---|---|---|
| `OPENAI_API_KEY` | `gpt-4o-mini` (`OPENAI_MODEL` 로 변경) | — |
| `ANTHROPIC_API_KEY` | `claude-opus-5` (`ANTHROPIC_MODEL` 로 변경) | `pip install anthropic` |

요약 프롬프트에는 **수집이 끝난 데이터만** 들어가며, 제공되지 않은 수치를 언급하지 않도록 시스템 프롬프트로 제한합니다. 근거 데이터는 화면의 "요약의 근거가 된 데이터 보기" 에서 그대로 확인할 수 있습니다.

## 명령줄에서 수집만 실행

```bash
python data_collector.py
```

## 문제 해결

**World Bank 수집이 404로 실패할 때** — 엑셀 URL 경로에 연도 코드가 포함되어 매년 바뀝니다. [Commodity Markets 페이지](https://www.worldbank.org/en/research/commodity-markets)에서 "Monthly prices (XLS)" 최신 링크를 복사해 `.env` 의 `WORLDBANK_XLSX_URL` 에 넣으세요.

**엑셀 열을 찾지 못한다는 오류** — Pink Sheet 양식이 바뀐 경우입니다. `data_collector.py` 의 `WORLDBANK_SERIES` 에 있는 열 이름(`Iron ore, cfr spot`, `Coal, Australian`)을 실제 시트 헤더와 맞춰주세요.

**AI Summary가 계속 같은 내용** — 캐시입니다. 데이터가 바뀌지 않으면 재호출하지 않습니다. [요약 다시 생성]을 누르세요.

## 면책

본 대시보드는 공개된 데이터를 수집해 참고용으로 제공합니다. 각 수치의 정확성은 원 출처를 확인하시기 바라며, 투자·매매 판단의 근거로 사용하지 마십시오. AI 요약은 자동 생성된 것으로 오류가 있을 수 있습니다.
