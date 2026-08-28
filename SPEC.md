# Financial Reports Insight Engine — 完整規格文件

**版本：** 3.0.0  
**日期：** 2026-08-28
**系統：** Taiwan 上市櫃公司財務報表萃取與分析引擎

---

## 目錄

1. [系統概覽](#1-系統概覽)
2. [輸入規格 (Input)](#2-輸入規格-input)
3. [輸出規格 (Output)](#3-輸出規格-output)
4. [資料庫 Schema（17 張表）](#4-資料庫-schema17-張表)
5. [管道四階段詳細說明](#5-管道四階段詳細說明)
6. [Domain Models（Pydantic v2）](#6-domain-modelspydantic-v2)
7. [Canonical 欄位分類表](#7-canonical-欄位分類表)
8. [HTTP API 與外部資料來源](#8-http-api-與外部資料來源)
9. [驗證規則](#9-驗證規則)
10. [計算指標](#10-計算指標)
11. [事件偵測規則](#11-事件偵測規則)
12. [品質分數公式](#12-品質分數公式)
13. [CLI 指令完整參考](#13-cli-指令完整參考)
14. [專案目錄結構](#14-專案目錄結構)
15. [依賴套件](#15-依賴套件)

---

## 1. 系統概覽

本系統處理台灣上市公司的季度財務報表，將 XBRL、iXBRL、PDF 等格式的原始文件轉換為結構化資料、計算財務指標、產生洞察卡片，供 LLM Agent 進行自然語言分析。

**技術棧：**
- Python 3.10+
- PostgreSQL 16 + pgvector（容器化）
- SQLAlchemy Core
- asyncio-first 架構
- Pydantic v2

**管道流程：**
```
FilingIdentity → INGEST → EXTRACT → VALIDATE → INSIGHTS → insight_ready
```

---

## 2. 輸入規格 (Input)

### 2.1 CLI 單筆執行

```bash
# 完整四階段
uv run fr run <stock_code> <year> <quarter> [options]

# 單一階段
uv run fr ingest <stock_code> <year> <quarter>
uv run fr extract <stock_code> <year> <quarter>
uv run fr validate <stock_code> <year> <quarter>
uv run fr insights <stock_code> <year> <quarter>
```

**參數：**

| 參數 | 型別 | 範例 | 說明 |
|------|------|------|------|
| `stock_code` | string | `"2330"` | 台灣股票代碼 |
| `year` | int | `2025` | 西元年份 |
| `quarter` | string | `"Q1"` | Q1 / Q2 / Q3 / Q4 |

**選項：**

| 選項 | 預設值 | 說明 |
|------|--------|------|
| `--db` | `$FR_DATABASE_URL` | PostgreSQL 連線 URL |
| `--output-dir` | `data/raw` | 原始文件下載目錄 |
| `--stages` | 全部 | 逗號分隔階段，例如 `ingest,extract` |
| `--force` | `False` | 強制重新執行已完成的階段 |

### 2.2 批次執行 (Batch)

```bash
uv run fr batch <batch_file.json> [options]
```

**選項：**

| 選項 | 預設值 | 說明 |
|------|--------|------|
| `--concurrency` | `4` | 最大同時處理數 |
| `--db` | `data/financial.db` | 資料庫路徑 |

**批次 JSON 格式：**

```json
[
  {
    "stock_code": "2330",
    "company_name": "台積電",
    "year": 2024,
    "quarter": "Q1"
  },
  {
    "stock_code": "2317",
    "company_name": "鴻海",
    "year": 2024,
    "quarter": "Q2"
  }
]
```

**JSON 欄位規格：**

| 欄位 | 型別 | 必填 | 說明 |
|------|------|------|------|
| `stock_code` | string | ✓ | 台灣股票代碼（例如 `"2330"`） |
| `company_name` | string | ✗ | 中文公司名稱（僅供顯示） |
| `year` | int | ✓ | 西元年份，例如 `2024` |
| `quarter` | string | ✓ | `"Q1"` \| `"Q2"` \| `"Q3"` \| `"Q4"` |

### 2.3 查詢指令

```bash
# 顯示filing資料
uv run fr show <stock_code> <year> <quarter> [--format table|json|summary]

# 自然語言查詢（需安裝 --extra llm）
uv run fr ask "<question>" --stock <code> --year <year> --quarter <quarter>
```

### 2.4 原始文件來源

| 文件類型 | 來源 | 本地路徑格式 |
|----------|------|-------------|
| PDF | TWSE / 本地快取 | `data/financial_reports/{period_code}_{stock_code}_AI1.pdf` |
| XBRL | MOPS API | `data/raw/` |
| iXBRL | MOPS API | `data/raw/` |

**Period Code 對照：**
- Q1 → `{year}01`（例如 `202401`）
- Q2 → `{year}02`
- Q3 → `{year}03`  
- Q4 → `{year}04`

**PDF 範例：** `202401_2330_AI1.pdf` = 台積電 2024年第一季

### 2.5 環境變數

| 變數 | 必填 | 說明 |
|------|------|------|
| `OPENAI_API_KEY` | 僅 `fr ask` | OpenAI GPT 查詢 |
| `FINMIND_TOKEN` | ✗ | FinMind 付費 token（免費層不需要） |

---

## 3. 輸出規格 (Output)

### 3.1 PostgreSQL 資料庫

預設路徑：`data/financial.db`（WAL mode，支援並發讀寫）

詳細 Schema 見第 4 節。

### 3.2 CLI 顯示格式

#### `fr show` — Table 格式（預設）

Rich library 表格，顯示：
- Filing 狀態、quality score
- 財務事實（facts）
- 計算指標（metrics）
- YoY/QoQ 比較
- 洞察卡片（insight cards）

#### `fr show --format json`

```json
{
  "filing_key": "2330_2024Q1",
  "status": "insight_ready",
  "quality_score": 0.87,
  "facts": [
    {
      "field": "net_revenue",
      "value": 592640000.0,
      "unit": "TWD_thousands",
      "source_type": "finmind",
      "confidence": 0.95,
      "period_start": "2024-01-01",
      "period_end": "2024-03-31",
      "period_type": "duration"
    }
  ],
  "metrics": [
    {
      "metric_name": "gross_margin",
      "value": 0.5297,
      "formula": "gross_profit / net_revenue"
    }
  ],
  "comparisons": {
    "yoy": [
      {
        "field": "net_revenue",
        "current_value": 592640000.0,
        "prior_value": 508630000.0,
        "change_abs": 84010000.0,
        "change_pct": 16.52,
        "direction": "up",
        "significance": "large"
      }
    ],
    "qoq": []
  },
  "events": [
    {
      "event_type": "revenue_growth_acceleration",
      "severity": "info",
      "title": "營收高速成長",
      "description": "YoY 成長 16.52%，超過 10% 門檻"
    }
  ],
  "insight_cards": [
    {
      "card_type": "performance_summary",
      "title": "2330 2024Q1 財務摘要",
      "summary": "...",
      "sentiment": "positive",
      "confidence": 0.9,
      "data_points": {}
    }
  ],
  "validation": [
    {
      "rule_name": "balance_sheet_equation",
      "passed": true,
      "severity": "error",
      "message": "資產 = 負債 + 權益（誤差 0.02%）"
    }
  ]
}
```

#### `fr batch` — 批次結果

```
Filing        | ingest    | extract   | validate  | insights
──────────────┼───────────┼───────────┼───────────┼──────────
2330_2024Q1   | ✓ done    | ✓ done    | ✓ done    | ✓ done
2317_2024Q1   | ✓ done    | ✓ done    | ✓ done    | ✓ done
...
Summary: 20/20 succeeded, 0 failed
Facts: 402 total | Chunks: 53,622 total
```

#### `fr ask` — 自然語言查詢

```
[AI Answer]
台積電 2024 Q1 營收成長 16.52%，主要因為先進製程需求強勁...

[Relevant Text Evidence]
頁 5: "本季合併營業收入為新台幣 5,926 億元，較上年同期成長 16.5%..."
```

### 3.3 資料庫統計（20 筆 batch 典型結果）

| 表格 | 典型行數 |
|------|---------|
| filings | 20 |
| financial_facts | ~402（約每筆 20 個 facts） |
| financial_metrics | ~110（約每筆 5-6 個指標） |
| period_comparisons | 視前期資料而定 |
| detected_events | 視門檻而定 |
| insight_cards | ~78（每筆約 4-5 張） |
| document_pages | ~2,356 |
| document_chunks | ~53,622 |
| validation_results | ~140（每筆 7 條規則） |

---

## 4. 資料庫 Schema（17 張表）

**PRAGMA 設定：**
```sql
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
PRAGMA synchronous=NORMAL;
```

---

### 4.1 `companies` — 公司主表

```sql
CREATE TABLE IF NOT EXISTS companies (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code TEXT    NOT NULL UNIQUE,    -- 台灣股票代碼，例如 "2330"
    name_zh    TEXT,                        -- 中文公司名，例如 "台積電"
    name_en    TEXT,                        -- 英文公司名，例如 "TSMC"
    industry   TEXT,                        -- 產業分類
    market     TEXT,                        -- 市場類別（上市/上櫃）
    created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);
```

**Unique 約束：** `stock_code`

---

### 4.2 `filings` — 季度申報記錄

```sql
CREATE TABLE IF NOT EXISTS filings (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    filing_key    TEXT    NOT NULL UNIQUE,      -- "{stock_code}_{year}{quarter}"，例如 "2330_2024Q1"
    company_id    INTEGER NOT NULL REFERENCES companies(id),
    year          INTEGER NOT NULL,             -- 西元年份
    quarter       TEXT    NOT NULL,             -- "Q1"|"Q2"|"Q3"|"Q4"
    status        TEXT    NOT NULL DEFAULT 'pending',
    quality_score REAL,                         -- 0.0–1.0，validate 階段計算
    created_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);
```

**status 狀態機：**
```
pending → ingested → extracted → validated → insight_ready
                                          ↘ failed（任何階段皆可）
```

**Unique 約束：** `filing_key`

---

### 4.3 `source_documents` — 原始文件記錄

```sql
CREATE TABLE IF NOT EXISTS source_documents (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    filing_id     INTEGER NOT NULL REFERENCES filings(id),
    doc_type      TEXT    NOT NULL,    -- 'xbrl' | 'ixbrl' | 'pdf'
    local_path    TEXT,                -- 本地文件路徑
    url           TEXT,                -- 下載來源 URL
    file_size     INTEGER,             -- bytes
    checksum      TEXT,                -- MD5 或 SHA256
    downloaded_at TEXT,                -- ISO datetime
    parse_status  TEXT    NOT NULL DEFAULT 'pending'
                                       -- 'pending' | 'in_progress' | 'completed' | 'failed'
);
```

**doc_type 值：**
- `xbrl` — XBRL instance document（.xml）
- `ixbrl` — inline XBRL（.html）
- `pdf` — 財務報告 PDF

---

### 4.4 `financial_facts` — 財務事實（核心表）

```sql
CREATE TABLE IF NOT EXISTS financial_facts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    filing_id    INTEGER NOT NULL REFERENCES filings(id),
    field        TEXT    NOT NULL,              -- canonical 欄位名，例如 "net_revenue"
    value        REAL    NOT NULL,              -- 數值
    unit         TEXT    NOT NULL DEFAULT 'TWD_thousands',
                                                -- 'TWD_thousands' | 'TWD_per_share'
    period_start TEXT,                          -- YYYY-MM-DD（duration 的起始日）
    period_end   TEXT,                          -- YYYY-MM-DD（期末日）
    period_type  TEXT    NOT NULL DEFAULT 'duration',
                                                -- 'duration'（流量）| 'instant'（時點）
    source_type  TEXT    NOT NULL DEFAULT 'xbrl',
                                                -- 'xbrl' | 'ixbrl' | 'pdf_table' | 'pdf_text' | 'computed' | 'finmind'
    confidence   REAL    NOT NULL DEFAULT 1.0,  -- 0.0–1.0，自動 clamp
    xbrl_tag     TEXT,                          -- 原始 XBRL tag 名稱
    created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE(filing_id, field, source_type)       -- 同一 filing 同一 field 同一 source 只存一筆
);
```

**confidence 來源對照：**

| source_type | confidence |
|-------------|-----------|
| xbrl | 1.0 |
| ixbrl | 0.95 |
| finmind | 0.95 |
| pdf_table | 0.75 |
| pdf_text | 0.6 |
| computed | 1.0 |

**unit 值：**
- `TWD_thousands` — 新台幣千元（財務報表通用單位）
- `TWD_per_share` — 每股金額（EPS 用）

---

### 4.5 `fact_evidence` — 事實來源佐證

```sql
CREATE TABLE IF NOT EXISTS fact_evidence (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    fact_id           INTEGER NOT NULL REFERENCES financial_facts(id),
    doc_id            INTEGER REFERENCES source_documents(id),
    page_number       INTEGER,              -- PDF 頁碼（1-based）
    section_title     TEXT,                 -- 所在章節標題
    raw_text          TEXT,                 -- 原始文字片段
    extraction_method TEXT    NOT NULL DEFAULT 'xbrl'
                                           -- 'xbrl' | 'pdf_table' | 'pdf_text'
);
```

---

### 4.6 `document_pages` — 文件頁面內容

```sql
CREATE TABLE IF NOT EXISTS document_pages (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id       INTEGER NOT NULL REFERENCES source_documents(id),
    page_number  INTEGER NOT NULL,          -- 1-based
    text_content TEXT,                      -- pdfplumber 萃取的全頁文字
    char_count   INTEGER NOT NULL DEFAULT 0,
    has_tables   INTEGER NOT NULL DEFAULT 0, -- boolean (0/1)
    UNIQUE(doc_id, page_number)
);
```

---

### 4.7 `document_sections` — 文件章節

```sql
CREATE TABLE IF NOT EXISTS document_sections (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id       INTEGER NOT NULL REFERENCES source_documents(id),
    section_type TEXT    NOT NULL,          -- 見下方 section_type 列表
    title        TEXT,                      -- 偵測到的章節標題（最多 100 字）
    page_start   INTEGER NOT NULL,          -- 起始頁碼（1-based）
    page_end     INTEGER NOT NULL,          -- 結束頁碼（1-based）
    content      TEXT                       -- 章節全文
);
```

**section_type 值：**

| 值 | 說明 |
|----|------|
| `income_statement` | 損益表 / 綜合損益表 |
| `balance_sheet` | 資產負債表 / 財務狀況表 |
| `cash_flow` | 現金流量表 |
| `equity_statement` | 權益變動表 |
| `notes` | 財務報表附註 |
| `auditor` | 會計師查核報告 |
| `accounting_policy` | 重大會計政策 |
| `eps_note` | 每股盈餘附註 |
| `risk` | 風險管理 |
| `other` | 其他 / 未分類 |

---

### 4.8 `document_chunks` — RAG 文字片段

```sql
CREATE TABLE IF NOT EXISTS document_chunks (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id            INTEGER NOT NULL REFERENCES source_documents(id),
    section_id        INTEGER REFERENCES document_sections(id),
    page_number       INTEGER NOT NULL,
    chunk_index       INTEGER NOT NULL DEFAULT 0,   -- 同section內的序號
    content           TEXT    NOT NULL,              -- ~500-1000 字元
    char_offset_start INTEGER,                       -- 在章節全文中的起始偏移
    char_offset_end   INTEGER,
    contains_numbers  INTEGER NOT NULL DEFAULT 0,    -- 是否含4位以上數字
    contains_table    INTEGER NOT NULL DEFAULT 0,    -- 是否看似表格
    importance_score  REAL    NOT NULL DEFAULT 0.5,  -- 0.0–1.0
    created_at        TEXT    NOT NULL DEFAULT (datetime('now'))
);
```

**importance_score 基準值：**

| section_type | 基準分 |
|-------------|-------|
| income_statement | 0.90 |
| balance_sheet | 0.90 |
| cash_flow | 0.85 |
| eps_note | 0.85 |
| equity_statement | 0.70 |
| notes | 0.60 |
| risk | 0.60 |
| auditor | 0.50 |
| accounting_policy | 0.50 |
| other | 0.40 |

含6位以上數字加分 +0.05（上限 1.0）

---

### 4.9 `chunk_embeddings` — chunk 向量

由 `fr embed` 離線產生（需 `uv sync --extra vector`）。維度須與
`src/agent/embedding.py` 的 `EMBEDDING_DIM` 一致，encode 時會斷言檢查。

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS chunk_embeddings (
    chunk_id   INTEGER PRIMARY KEY REFERENCES document_chunks(id) ON DELETE CASCADE,
    model_name TEXT         NOT NULL,     -- 例如 "BAAI/bge-base-zh-v1.5"
    embedding  VECTOR(768)  NOT NULL,     -- L2 normalised
    created_at TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX idx_chunk_embeddings_hnsw
    ON chunk_embeddings USING hnsw (embedding vector_cosine_ops);
```

> 目前為佔位表，向量搜尋功能尚未整合。

---

### 4.10 `text_summaries` — 文字摘要

```sql
CREATE TABLE IF NOT EXISTS text_summaries (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    filing_id    INTEGER NOT NULL REFERENCES filings(id),
    summary_type TEXT    NOT NULL,   -- 'executive' | 'section' | 'risk'
    content      TEXT    NOT NULL,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);
```

---

### 4.11 `financial_metrics` — 計算財務指標

```sql
CREATE TABLE IF NOT EXISTS financial_metrics (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    filing_id   INTEGER NOT NULL REFERENCES filings(id),
    metric_name TEXT    NOT NULL,     -- 見指標清單
    value       REAL    NOT NULL,
    formula     TEXT,                 -- 公式描述，例如 "gross_profit / net_revenue"
    inputs_json TEXT,                 -- JSON dict，記錄輸入值，例如 {"gross_profit": 313.5, "net_revenue": 592.6}
    confidence  REAL    NOT NULL DEFAULT 1.0,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE(filing_id, metric_name)
);
```

**metric_name 清單：**

| metric_name | 公式 | 說明 |
|-------------|------|------|
| `gross_margin` | gross_profit / net_revenue | 毛利率 |
| `operating_margin` | operating_income / net_revenue | 營業利益率 |
| `net_margin` | net_income / net_revenue | 淨利率 |
| `current_ratio` | current_assets / current_liabilities | 流動比率 |
| `debt_to_equity` | total_liabilities / equity | 負債權益比 |
| `roe` | net_income / equity | 股東權益報酬率 |
| `roa` | net_income / total_assets | 總資產報酬率 |
| `book_value_per_share` | equity / (share_capital / 10) | 每股淨值 |
| `free_cash_flow` | operating_cash_flow - \|capex\| | 自由現金流（千元） |
| `cf_quality` | operating_cash_flow / net_income | 現金流品質 |

---

### 4.12 `period_comparisons` — 期間比較（YoY/QoQ）

```sql
CREATE TABLE IF NOT EXISTS period_comparisons (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    filing_id         INTEGER NOT NULL REFERENCES filings(id),
    compare_filing_id INTEGER REFERENCES filings(id),  -- 比較期 filing（可為 NULL）
    field             TEXT    NOT NULL,
    compare_type      TEXT    NOT NULL,   -- 'yoy' | 'qoq'
    current_value     REAL    NOT NULL,
    prior_value       REAL    NOT NULL,
    change_abs        REAL,               -- 絕對變化量（同單位）
    change_pct        REAL,               -- 百分比變化，例如 12.5 表示 +12.5%
    direction         TEXT,               -- 'up' | 'down' | 'flat'
    significance      TEXT,               -- 'large'(≥10%) | 'moderate'(≥3%) | 'small'
    interpretation    TEXT                -- 文字說明
);
```

**significance 判斷：**
- `large`：|change_pct| ≥ 10%
- `moderate`：3% ≤ |change_pct| < 10%
- `small`：|change_pct| < 3%

---

### 4.13 `detected_events` — 偵測到的財務事件

```sql
CREATE TABLE IF NOT EXISTS detected_events (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    filing_id           INTEGER NOT NULL REFERENCES filings(id),
    event_type          TEXT    NOT NULL,              -- 事件類型（見事件清單）
    severity            TEXT    NOT NULL DEFAULT 'info',
                                                        -- 'error' | 'warning' | 'info'
    title               TEXT,                           -- 事件標題
    description         TEXT,                           -- 詳細說明
    related_fields_json TEXT,                           -- JSON 陣列，相關欄位名稱
    confidence          REAL    NOT NULL DEFAULT 0.9,
    created_at          TEXT    NOT NULL DEFAULT (datetime('now'))
);
```

**event_type 清單：**

| event_type | severity | 觸發條件 |
|-----------|---------|---------|
| `revenue_growth_acceleration` | info | YoY 營收成長 > 30% |
| `revenue_decline` | warning | YoY 營收衰退 < -10% |
| `gross_margin_compression` | warning | YoY 毛利率下滑 < -3% |
| `fcf_negative` | warning | 自由現金流 < 0 |
| `inventory_buildup` | info | QoQ 存貨成長 > 20% 且營收低成長 |
| `cash_flow_quality_warning` | warning | OCF / NI < 0.7 |

---

### 4.14 `insight_cards` — 洞察卡片（Agent 消費）

```sql
CREATE TABLE IF NOT EXISTS insight_cards (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    filing_id    INTEGER NOT NULL REFERENCES filings(id),
    card_type    TEXT    NOT NULL,           -- 卡片類型（見清單）
    title        TEXT    NOT NULL,           -- 繁體中文標題
    summary      TEXT    NOT NULL,           -- 1-3 句摘要
    data_points  TEXT,                       -- JSON dict，支撐數據
    sentiment    TEXT,                       -- 'positive' | 'negative' | 'neutral'
    confidence   REAL    NOT NULL DEFAULT 0.8,
    generated_at TEXT    NOT NULL DEFAULT (datetime('now'))
);
```

**card_type 清單（10 種）：**

| card_type | 說明 |
|----------|------|
| `performance_summary` | 頂層財務概覽（營收、淨利、EPS、毛利率） |
| `revenue_growth` | 營收 YoY 分析 |
| `margin_change` | 毛利率/營業利益率/淨利率趨勢 |
| `profitability_change` | 淨利與 EPS 變化 |
| `cash_flow_quality` | 現金流品質（OCF vs NI） |
| `balance_sheet_strength` | 資產/負債/權益概覽 |
| `working_capital_change` | QoQ 流動性指標 |
| `capex_and_investment` | 資本支出趨勢 |
| `debt_and_liquidity` | 槓桿與流動比率 |
| `risk_and_commitments` | 驗證發現的風險因子 |

---

### 4.15 `insight_evidence` — 洞察佐證

```sql
CREATE TABLE IF NOT EXISTS insight_evidence (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id         INTEGER NOT NULL REFERENCES insight_cards(id),
    evidence_type   TEXT    NOT NULL,    -- 'fact' | 'chunk' | 'metric'
    ref_id          INTEGER,             -- 對應表的 id
    quote           TEXT,                -- 引用文字
    page_number     INTEGER,
    section_title   TEXT,
    relevance_score REAL    NOT NULL DEFAULT 0.5
);
```

---

### 4.16 `validation_results` — 驗證結果

```sql
CREATE TABLE IF NOT EXISTS validation_results (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    filing_id  INTEGER NOT NULL REFERENCES filings(id),
    rule_name  TEXT    NOT NULL,          -- 規則名稱（見驗證規則清單）
    passed     INTEGER NOT NULL DEFAULT 1, -- 1=通過 / 0=失敗
    severity   TEXT    NOT NULL DEFAULT 'info',
                                           -- 'error' | 'warning' | 'info'
    message    TEXT,                       -- 說明訊息
    checked_at TEXT    NOT NULL DEFAULT (datetime('now'))
);
```

---

### 4.17 `pipeline_runs` — 管道執行日誌

```sql
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    filing_key    TEXT    NOT NULL,
    stage         TEXT    NOT NULL,     -- 'ingest' | 'extract' | 'validate' | 'insights'
    status        TEXT    NOT NULL,     -- 'started' | 'completed' | 'failed' | 'skipped'
    started_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    finished_at   TEXT,                 -- NULL 表示尚未完成
    error_message TEXT                  -- 失敗時的錯誤訊息
);
```

---

## 5. 管道四階段詳細說明

### Stage 1: INGEST（下載）

**狀態轉換：** `pending` → `ingested`

**輸入：** FilingIdentity（stock_code, year, quarter）

**處理步驟：**
1. MOPS API 查詢公司基本資料（name_zh, industry, market）
2. Upsert `companies` 表
3. Upsert `filings` 表（status=pending）
4. 非同步並行下載（asyncio.gather）：
   - XBRL（MOPS API）
   - iXBRL（MOPS API）
   - PDF（TWSE，或本地快取 `data/financial_reports/`）
5. 儲存 `source_documents` 記錄
6. 更新 status → `ingested`

**輸出：**
```python
{
    "xbrl_path": "/path/to/file.xml",   # 或 None
    "ixbrl_path": "/path/to/file.html", # 或 None
    "pdf_path": "/path/to/file.pdf"     # 或 None
}
```

**幂等性：** 若 status 已 >= `ingested`，跳過（除非 force=True）

---

### Stage 2: EXTRACT（萃取）

**狀態轉換：** `ingested` → `extracted`

**輸入：** Stage 1 輸出的文件路徑

**處理步驟（依優先級）：**

1. **XBRL 解析**（`xbrl_parser.py`）
   - 解析 XBRL instance XML
   - 建立 context map（context_ref → period_start, period_end）
   - 萃取 ~100+ XBRL tags 的數值
   - confidence = 1.0

2. **iXBRL 解析**（`ixbrl_parser.py`，XBRL 不可用時）
   - 解析 HTML 中的 `ix:nonFraction` 元素
   - confidence = 0.95

3. **FinMind API 回退**（XBRL/iXBRL 均不可用時）
   - 查詢三個 dataset：TaiwanStockFinancialStatements、TaiwanStockBalanceSheet、TaiwanStockCashFlowsStatement
   - 過濾至目標季末日期
   - confidence = 0.95

4. **PDF 文字萃取**（pdfplumber，平行執行）
   - 萃取所有頁面 → `document_pages`
   - 偵測章節（含 `民國` 日期標記驗證）→ `document_sections`
   - 建立 RAG chunks（~600字/chunk，50字重疊）→ `document_chunks`
   - PDF table fallback（無 XBRL 時）→ 額外 facts

5. 正規化所有 facts（canonical field 對應、單位轉換）
6. 儲存至 `financial_facts`
7. 更新 status → `extracted`

**CPU 密集工作（PDF）在 ThreadPoolExecutor 執行（max_workers=2），避免阻塞 event loop**

**輸出：**
```python
{"facts_count": 21, "chunks_count": 2681, "status": "completed"}
```

---

### Stage 3: VALIDATE（驗證）

**狀態轉換：** `extracted` → `validated`

**處理步驟：**
1. 從 DB 載入 facts dict（`{field: value}`）
2. 執行 7 條驗證規則（見第 9 節）
3. 儲存結果至 `validation_results`
4. 多來源交叉比對（XBRL vs PDF vs FinMind）
5. 計算 quality_score（見第 12 節）
6. 更新 `filings.quality_score`
7. 更新 status → `validated`

**輸出：**
```python
{
    "score": 0.87,
    "passed": 6,
    "failed": 0,
    "warnings": 1,
    "status": "completed"
}
```

---

### Stage 4: INSIGHTS（洞察）

**狀態轉換：** `validated` → `insight_ready`

**處理步驟：**
1. 計算財務指標 → `financial_metrics`（10 項）
2. 取得去年同期資料 → 計算 YoY 比較 → `period_comparisons`
3. 取得上季資料 → 計算 QoQ 比較 → `period_comparisons`
4. 偵測財務事件 → `detected_events`（6 種規則）
5. 建立洞察卡片 → `insight_cards`（10 種）
6. 更新 status → `insight_ready`

**輸出：**
```python
{
    "metrics_count": 8,
    "insights_count": 6,
    "events_count": 0,
    "status": "completed"
}
```

---

## 6. Domain Models（Pydantic v2）

### FilingIdentity（frozen dataclass）
```python
@dataclass(frozen=True)
class FilingIdentity:
    stock_code: str   # "2330"
    year: int         # 2024
    quarter: str      # "Q1"|"Q2"|"Q3"|"Q4"

    @property
    def filing_key(self) -> str:
        return f"{self.stock_code}_{self.year}{self.quarter}"  # "2330_2024Q1"

    @property
    def period_code(self) -> str:
        q_map = {"Q1": "01", "Q2": "02", "Q3": "03", "Q4": "04"}
        return f"{self.year}{q_map[self.quarter]}"  # "202401"

    @property
    def pdf_filename(self) -> str:
        return f"{self.period_code}_{self.stock_code}_AI1.pdf"
```

### Filing
```python
class Filing(BaseModel):
    filing_key: str
    stock_code: str
    year: int
    quarter: str  # 驗證：必須為 Q1|Q2|Q3|Q4
    company_name_zh: str | None = None
    company_name_en: str | None = None
    industry: str | None = None
    status: str = "pending"  # 驗證：必須為有效狀態值
    quality_score: float | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

### Fact
```python
class Fact(BaseModel):
    filing_key: str
    field: str          # canonical 欄位名，例如 "net_revenue"
    value: float
    unit: str = "TWD_thousands"
    period_start: date | None = None
    period_end: date | None = None
    period_type: str = "duration"  # "duration" | "instant"
    source_type: str = "xbrl"
    # 有效值：{"xbrl", "ixbrl", "pdf_table", "pdf_text", "computed", "finmind"}
    confidence: float = 1.0  # 自動 clamp 至 [0.0, 1.0]
    xbrl_tag: str | None = None
```

### InsightCard
```python
class InsightCard(BaseModel):
    filing_key: str
    card_type: str
    title: str
    summary: str
    data_points: dict[str, Any] = Field(default_factory=dict)
    sentiment: str | None = None  # "positive"|"negative"|"neutral"
    confidence: float = 0.8
```

### DetectedEvent
```python
class DetectedEvent(BaseModel):
    filing_key: str
    event_type: str
    severity: str = "info"  # "error"|"warning"|"info"
    title: str = ""
    description: str
    related_fields: list[str] = Field(default_factory=list)
    confidence: float = 0.9
```

---

## 7. Canonical 欄位分類表

### 損益表（period_type = "duration"）

| canonical field | FinMind type | 說明 |
|----------------|-------------|------|
| `net_revenue` | Revenue | 營業收入（千元） |
| `gross_profit` | GrossProfit | 毛利 |
| `operating_income` | OperatingIncome | 營業利益 |
| `profit_before_tax` | IncomeBeforeTax | 稅前淨利 |
| `net_income` | IncomeAfterTaxes | 本期淨利 |
| `net_income_attributable_to_parent` | EquityAttributableToOwnersOfParent | 歸屬母公司淨利 |
| `eps_basic` | EPS / BasicEPS | 基本每股盈餘（TWD/股） |
| `eps_diluted` | DilutedEPS | 稀釋每股盈餘 |
| `operating_expenses` | OperatingExpenses | 營業費用 |
| `rd_expenses` | ResearchAndDevelopmentExpenses | 研發費用 |
| `tax_expense` | TAX | 所得稅費用 |
| `comprehensive_income` | TotalConsolidatedProfitForThePeriod | 本期綜合損益 |

### 資產負債表（period_type = "instant"）

| canonical field | FinMind type | 說明 |
|----------------|-------------|------|
| `cash_and_equivalents` | CashAndCashEquivalents | 現金及約當現金 |
| `accounts_receivable` | AccountsReceivable | 應收帳款 |
| `inventory` | Inventories | 存貨 |
| `current_assets` | CurrentAssets | 流動資產合計 |
| `total_assets` | Assets | 資產總計 |
| `accounts_payable` | AccountsPayable | 應付帳款 |
| `current_liabilities` | CurrentLiabilities | 流動負債合計 |
| `total_liabilities` | Liabilities | 負債總計 |
| `equity` | Equity | 權益總計 |
| `equity_attributable_to_parent` | EquityAttributableToOwnersOfParentCompany | 歸屬母公司權益 |
| `retained_earnings` | RetainedEarnings | 保留盈餘 |
| `share_capital` | CommonStocks | 股本 |

### 現金流量表（period_type = "duration"）

| canonical field | FinMind type | 說明 |
|----------------|-------------|------|
| `operating_cash_flow` | CashProvidedByOperatingActivities | 營業活動現金流量 |
| `investing_cash_flow` | CashProvidedByInvestingActivities | 投資活動現金流量 |
| `financing_cash_flow` | CashProvidedByFinancingActivities | 融資活動現金流量 |
| `capex` | PropertyAndPlantAndEquipment | 資本支出（購置不動產廠房設備） |
| `cash_beginning` | CashBalancesBeginningOfPeriod | 期初現金 |
| `cash_ending` | CashBalancesEndOfPeriod | 期末現金 |

---

## 8. HTTP API 與外部資料來源

### 8.1 FinancialReports HTTP API v1

本專案以 FastAPI 提供跨 repository 的 versioned consumer contract。正式
邊界是 HTTP 與 committed `docs/openapi-v1.json`，consumer 不得直接讀取本專案
PostgreSQL 或本地檔案。

**啟動：**

```bash
uv run uvicorn src.api.app:create_app --factory --host 127.0.0.1 --port 8010
```

**主要端點：**

| 類型 | 端點 |
|------|------|
| 健康 | `GET /health/live`, `GET /health/ready` |
| 發現 | `GET /v1/schema`, `GET /v1/capabilities` |
| Filing | `GET /v1/filings/{stock_code}/{period}/snapshot` |
| Context | `GET /v1/filings/{stock_code}/{period}/context` |
| 清單 | `GET /v1/stocks`, `GET /v1/stocks/{stock_code}/periods` |
| 工作 | `POST /v1/filings/{stock_code}/{period}/refresh`, `GET /v1/jobs/{job_id}` |
| 批次 | `POST /v1/batch/filings/query` |

回應 schema 版本為 `1.0.0`，包含 filing identity、readiness、pipeline
status、freshness、quality、snapshot、canonical facts、field availability、
validation、metrics、comparisons、events、evidence、insight cards、source
documents 與 pipeline state。詳細狀態碼、限制與 absence/unit 語意見
`docs/API_V1.md`。

### 8.2 FinMind API（主要財務數據來源）

**Base URL：** `https://api.finmindtrade.com/api/v4/data`

**Method：** GET

**Parameters：**

| 參數 | 型別 | 必填 | 說明 |
|------|------|------|------|
| `dataset` | string | ✓ | 資料集名稱 |
| `data_id` | string | ✓ | 股票代碼，例如 `"2330"` |
| `start_date` | string | ✓ | YYYY-MM-DD，通常為 `{year}-01-01` |
| `end_date` | string | ✓ | YYYY-MM-DD，季末日期 |
| `token` | string | ✗ | 付費層 token |

**使用的 Dataset：**

| dataset | 說明 |
|---------|------|
| `TaiwanStockFinancialStatements` | 損益表 |
| `TaiwanStockBalanceSheet` | 資產負債表 |
| `TaiwanStockCashFlowsStatement` | 現金流量表 |

**回應格式：**
```json
{
  "status": 200,
  "msg": "success",
  "data": [
    {
      "date": "2024-03-31",
      "stock_id": "2330",
      "type": "Revenue",
      "value": 592640000
    }
  ]
}
```

**數值單位換算：** FinMind 回傳完整新台幣（元），需除以 1000 轉換為千元：
```python
if unit == "TWD_thousands" and abs(value) >= 1000:
    value = value / 1000.0
```

**重試策略：** 最多 3 次，指數退避（2^attempt 秒）

**SSL：** WSL 環境需 `verify=False`

### 8.3 MOPS（公開資訊觀測站）

**用途：** 查詢公司基本資料（name_zh, industry, market）

**注意：** MOPS 封鎖自動化 XBRL 下載，只能查詢公司資訊

### 8.4 TWSE（台灣證券交易所）

**用途：** PDF 財務報告下載

**本地快取優先：** 先檢查 `data/financial_reports/{filename}`，不存在才下載

---

## 9. 驗證規則

| rule_name | 條件 | severity | 說明 |
|-----------|------|---------|------|
| `balance_sheet_equation` | \|assets - (liabilities + equity)\| / assets < 0.01 | error | 資產 = 負債 + 權益（±1% 容許誤差） |
| `gross_profit_lte_revenue` | gross_profit ≤ net_revenue | error | 毛利不可超過營收 |
| `income_consistency` | operating_income ≤ gross_profit | error | 營業利益不可超過毛利 |
| `eps_consistency` | sign(eps_basic) == sign(net_income) | error | EPS 與淨利符號一致 |
| `current_ratio_positive` | current_assets / current_liabilities > 0 | warning | 流動比率須為正值 |
| `cf_quality` | operating_cash_flow / net_income ≥ 0.7 | warning | 現金流品質 |
| `revenue_positive` | net_revenue > 0 | info | 營收須為正值 |

---

## 10. 計算指標

| metric_name | 公式 | 單位 |
|-------------|------|------|
| `gross_margin` | gross_profit / net_revenue | 比率（0.0–1.0） |
| `operating_margin` | operating_income / net_revenue | 比率 |
| `net_margin` | net_income / net_revenue | 比率 |
| `current_ratio` | current_assets / current_liabilities | 倍數 |
| `debt_to_equity` | total_liabilities / equity | 倍數 |
| `roe` | net_income / equity | 比率（年化） |
| `roa` | net_income / total_assets | 比率 |
| `book_value_per_share` | equity / (share_capital / 10) | 元/股 |
| `free_cash_flow` | operating_cash_flow - \|capex\| | 千元 |
| `cf_quality` | operating_cash_flow / net_income | 比率 |

---

## 11. 事件偵測規則

| event_type | 觸發條件 | severity | 相關欄位 |
|-----------|---------|---------|---------|
| `revenue_growth_acceleration` | YoY 營收成長 > 30% | info | net_revenue |
| `revenue_decline` | YoY 營收成長 < -10% | warning | net_revenue |
| `gross_margin_compression` | YoY 毛利率變化 < -3% | warning | gross_profit, net_revenue |
| `fcf_negative` | free_cash_flow < 0 | warning | operating_cash_flow, capex |
| `inventory_buildup` | QoQ 存貨成長 > 20% 且 QoQ 營收成長 < 5% | info | inventory, net_revenue |
| `cash_flow_quality_warning` | cf_quality < 0.7 | warning | operating_cash_flow, net_income |

---

## 12. 品質分數公式

```
quality_score = 0.40 × xbrl_coverage
              + 0.30 × completeness
              + 0.20 × validation_score
              + 0.10 × evidence_coverage
```

**各分項計算：**

```
xbrl_coverage    = (XBRL 來源的 facts 數量) / (canonical fields 總數)

completeness     = (9 個關鍵欄位中已取得的數量) / 9
  關鍵欄位：net_revenue, gross_profit, operating_income, net_income,
            eps_basic, total_assets, total_liabilities, equity, operating_cash_flow

validation_score = max(0, passed_rules / total_rules - error_count × 0.1)

evidence_coverage = (有 fact_evidence 記錄的 facts) / (總 facts 數)
```

---

## 13. CLI 指令完整參考

```bash
# ── 完整管道 ───────────────────────────────────────────────
uv run fr run 2330 2024 Q1
uv run fr run 2330 2024 Q1 --force
uv run fr run 2330 2024 Q1 --stages ingest,extract
uv run fr run 2330 2024 Q1 --db /path/to/custom.db --output-dir /path/to/raw

# ── 單一階段 ───────────────────────────────────────────────
uv run fr ingest  2330 2024 Q1
uv run fr extract 2330 2024 Q1
uv run fr validate 2330 2024 Q1
uv run fr insights 2330 2024 Q1

# ── 批次處理 ───────────────────────────────────────────────
uv run fr batch examples/test_20.json
uv run fr batch examples/test_20.json --concurrency 4
uv run fr batch examples/test_20.json --db custom.db

# ── 查詢與顯示 ─────────────────────────────────────────────
uv run fr show 2330 2024 Q1
uv run fr show 2330 2024 Q1 --format json
uv run fr show 2330 2024 Q1 --format summary

# ── 自然語言查詢（需 OPENAI_API_KEY）──────────────────────
uv run fr ask "毛利率為什麼下滑?" --stock 2330 --year 2024 --quarter Q1
```

---

## 14. 專案目錄結構

```
FinancialReports/
├── src/
│   ├── cli.py                        # CLI 入口（fr 指令）
│   ├── domain/
│   │   ├── identity.py               # FilingIdentity dataclass
│   │   ├── models.py                 # Pydantic models（Filing, Fact, Chunk...）
│   │   └── taxonomy.py               # Canonical 欄位對應（XBRL_TO_CANONICAL, KNOWN_XBRL_TAGS）
│   ├── sources/
│   │   ├── registry.py               # Client 工廠函數
│   │   ├── mops_client.py            # MOPS API（公司基本資料）
│   │   ├── xbrl_client.py            # XBRL/iXBRL 下載
│   │   ├── pdf_client.py             # TWSE PDF 下載
│   │   └── finmind_client.py         # FinMind API（財務數據主要回退來源）
│   ├── parsers/
│   │   ├── xbrl_parser.py            # XBRL instance 解析（lxml）
│   │   ├── ixbrl_parser.py           # iXBRL HTML 解析
│   │   ├── pdf_text_parser.py        # PDF 文字萃取（pdfplumber）
│   │   ├── pdf_table_parser.py       # PDF 表格萃取（word-position 法）
│   │   └── pdf_section_parser.py     # 章節偵測 + RAG chunk 建立
│   ├── normalize/
│   │   ├── fact_mapper.py            # XBRL tag → canonical field 對應
│   │   ├── period_normalizer.py      # 民國/西元日期轉換，quarter_to_dates()
│   │   ├── unit_normalizer.py        # 單位正規化（→ TWD_thousands）
│   │   └── company_mapper.py         # 股票代碼 → 公司資訊解析
│   ├── storage/
│   │   ├── schema.sql                # 17 張表的完整 DDL
│   │   ├── store.py                  # SQLAlchemy Core wrapper
│   │   └── json_exporter.py          # JSON 匯出
│   ├── analytics/
│   │   ├── metrics.py                # 財務指標計算（純函數）
│   │   ├── comparisons.py            # YoY/QoQ 比較
│   │   ├── event_detector.py         # 事件偵測（規則引擎）
│   │   └── insight_builder.py        # 洞察卡片建立（10 種）
│   ├── validation/
│   │   ├── rules.py                  # 7 條驗證規則
│   │   ├── reconciler.py             # 多來源交叉比對
│   │   └── quality_score.py          # 品質分數計算
│   ├── agent/
│   │   ├── query_service.py          # 高層查詢介面
│   │   ├── retriever.py              # 關鍵字檢索（facts, chunks）
│   │   └── context_builder.py        # LLM context pack 組裝
│   ├── api/
│   │   ├── app.py                    # FastAPI v1 routes 與 health
│   │   ├── contracts.py              # Versioned consumer schema
│   │   ├── service.py                # Filing envelope 組裝
│   │   ├── repository.py             # API read model
│   │   ├── jobs.py                   # Process-local refresh jobs
│   │   └── export_openapi.py         # OpenAPI artifact 產生器
│   └── pipeline/
│       ├── run.py                    # 管道協調器
│       ├── ingest.py                 # Stage 1
│       ├── extract.py                # Stage 2
│       ├── validate.py               # Stage 3
│       └── build_insights.py         # Stage 4
├── tests/
├── examples/
│   ├── test_20.json                  # 20 筆批次測試設定
│   ├── batch_query.json
│   └── semiconductor_batch.json
├── data/
│   ├── financial.db                  # 舊 SQLite 資料庫（僅供搬遷）
│   ├── raw/                          # XBRL/iXBRL 下載暫存
│   └── financial_reports/            # PDF 本地快取
│       └── {period_code}_{stock_code}_AI1.pdf
├── docs/
│   ├── API_V1.md                     # HTTP API contract
│   └── openapi-v1.json               # Committed OpenAPI baseline
├── pyproject.toml
├── uv.lock
└── .env                              # OPENAI_API_KEY, FINMIND_TOKEN
```

---

## 15. 依賴套件

### 核心

| 套件 | 版本 | 用途 |
|------|------|------|
| `httpx` | ≥0.27.0 | 非同步 HTTP 客戶端（FinMind, MOPS, TWSE） |
| `requests` | ≥2.32.0 | 同步 HTTP 客戶端 |
| `beautifulsoup4` | ≥4.12.0 | HTML 解析（MOPS, iXBRL） |
| `lxml` | ≥5.0.0 | XML/HTML 解析（XBRL, iXBRL） |
| `pydantic` | ≥2.7.0 | 資料驗證（v2） |
| `sqlalchemy` | ≥2.0.0 | 資料庫操作 |
| `pandas` | ≥2.0.0 | 資料處理 |
| `typer` | ≥0.12.0 | CLI 框架 |
| `rich` | ≥13.0.0 | 終端機美化輸出 |
| `python-dateutil` | ≥2.9.0 | 日期工具 |

### 選用 Extras

```bash
# PDF 萃取
uv sync --extra pdf
# pdfplumber>=0.11.0, pypdfium2>=4.0.0

# OCR（掃描 PDF）
uv sync --extra ocr
# paddleocr>=2.7.0, paddlepaddle>=2.6.0, opencv-python>=4.9.0

# 向量搜尋
uv sync --extra vector
# chromadb>=0.5.0, sentence-transformers>=3.0.0

# LLM 查詢
uv sync --extra llm
# openai>=1.30.0, tiktoken>=0.7.0
```
