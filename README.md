# Financial Reports Insight Engine

台灣上市櫃公司財報分析引擎，將 XBRL / iXBRL / PDF 原始文件轉換為結構化財務資料、計算財務指標、自動偵測異常事件，並產生 LLM Agent 可直接消費的洞察卡片。

```
XBRL / iXBRL / PDF / FinMind API
            │
            ▼  Stage 1: Ingest
     下載原始文件（TWSE / MOPS / FinMind）
            │
            ▼  Stage 2: Extract
  financial_facts（標準化財務數字）
  document_chunks（PDF 文字片段，供 RAG）
            │
            ▼  Stage 3: Validate
    驗證財務邏輯、計算品質分數（0–1）
            │
            ▼  Stage 4: Insights
  financial_metrics  ← 毛利率、ROE、FCF…
  period_comparisons ← YoY / QoQ 比較
  detected_events    ← 自動偵測財務異常
  insight_cards      ← Agent 可讀摘要
            │
            ▼
  fr ask "台積電 2024 Q1 有什麼重點？"
```

---

## 目錄

1. [系統需求與安裝](#1-系統需求與安裝)
2. [快速開始](#2-快速開始)
3. [管道四階段詳解](#3-管道四階段詳解)
4. [CLI 完整指令參考](#4-cli-完整指令參考)
5. [資料來源說明](#5-資料來源說明)
6. [資料庫結構](#6-資料庫結構)
7. [財務數字標準化](#7-財務數字標準化)
8. [計算指標與分析](#8-計算指標與分析)
9. [驗證規則](#9-驗證規則)
10. [專案結構](#10-專案結構)
11. [開發指南](#11-開發指南)

---

## 1. 系統需求與安裝

**需求：**
- Python 3.10+
- [uv](https://docs.astral.sh/uv/) 套件管理工具

**安裝步驟：**

```bash
git clone <repo-url>
cd FinancialReports

# 安裝核心依賴
uv sync

# 建議同時安裝 PDF 解析（大多數情況需要）
uv sync --extra pdf
```

**可選功能模組（Extra）：**

| Extra | 安裝指令 | 啟用功能 | 套件 |
|-------|----------|----------|------|
| `pdf` | `uv sync --extra pdf` | PDF 文字與表格萃取 | pdfplumber, pypdfium2 |
| `ocr` | `uv sync --extra ocr` | 掃描版 PDF 識別 | PaddleOCR, OpenCV |
| `vector` | `uv sync --extra vector` | 向量語意搜尋 | ChromaDB, sentence-transformers |
| `llm` | `uv sync --extra llm` | 自然語言問答 | openai, tiktoken |
| `all` | `uv sync --extra all` | 全部功能 | — |

**環境變數（`.env`）：**

```bash
cp .env.example .env
# 填入以下設定
OPENAI_API_KEY=sk-...       # fr ask 自然語言查詢時需要
FINMIND_TOKEN=              # FinMind 付費 token（免費層不需要）
```

---

## 2. 快速開始

### 單筆執行

```bash
# 完整跑完四個階段（下載 → 解析 → 驗證 → 產生洞察）
uv run fr run 2330 2024 Q1
```

執行完成後，可查看結果：

```bash
uv run fr show 2330 2024 Q1
```

### 批次執行 20 筆

```bash
uv run fr batch examples/test_20.json --concurrency 4
```

批次 JSON 格式如下，每筆指定股票代碼、年份、季別：

```json
[
  { "stock_code": "2330", "company_name": "台積電",  "year": 2024, "quarter": "Q1" },
  { "stock_code": "2317", "company_name": "鴻海",    "year": 2024, "quarter": "Q2" },
  { "stock_code": "2454", "company_name": "聯發科",  "year": 2024, "quarter": "Q3" }
]
```

**欄位說明：**

| 欄位 | 型別 | 必填 | 說明 |
|------|------|------|------|
| `stock_code` | string | ✓ | 台灣股票代碼（四位數字） |
| `company_name` | string | ✗ | 中文名稱，僅供記錄，不影響處理 |
| `year` | int | ✓ | 西元年份，例如 `2024` |
| `quarter` | string | ✓ | `"Q1"` / `"Q2"` / `"Q3"` / `"Q4"` |

### 自然語言查詢

```bash
# 需要 OPENAI_API_KEY 與 --extra llm
uv run fr ask "這季毛利率為什麼下滑？" --stock 2330 --year 2024 --quarter Q1
uv run fr ask "自由現金流狀況如何？" --stock 2454 --year 2024 --quarter Q2
```

---

## 3. 管道四階段詳解

每個階段都具備**幂等性保護**：已完成的階段預設跳過，除非加上 `--force`。

### Stage 1 — Ingest（下載）

```bash
uv run fr ingest 2330 2024 Q1
```

從三個來源平行非同步下載原始文件：

| 來源 | 取得內容 | 說明 |
|------|----------|------|
| MOPS | XBRL instance document | 結構化財務數字主要來源 |
| MOPS | iXBRL HTML | XBRL 不可用時的備援 |
| TWSE / 本地快取 | PDF 財務報告 | 文字萃取與附註 |

- PDF 優先使用本地快取（`data/financial_reports/`），不存在才連線下載
- 本地 PDF 命名規則：`{期間碼}_{股票代碼}_AI1.pdf`
  - 例：`202401_2330_AI1.pdf`（台積電 2024 Q1）
  - 期間碼：Q1=`01`、Q2=`02`、Q3=`03`、Q4=`04`
- 所有下載記錄存入 `source_documents` 表（含路徑、大小、checksum）
- 完成後 filing status 更新為 `ingested`

### Stage 2 — Extract（萃取）

```bash
uv run fr extract 2330 2024 Q1
```

按優先級依序嘗試三種財務數字來源：

**優先級 1：XBRL**（信心度 1.0）
- 解析 XML instance document
- 建立 context map（context_ref → 期間起訖日）
- 對應 ~100 個 XBRL tag → canonical 欄位名稱

**優先級 2：iXBRL**（信心度 0.95）
- 從 HTML 中解析 `ix:nonFraction` 元素
- 取出 tag 名稱與數值，邏輯同 XBRL

**優先級 3：FinMind API**（信心度 0.95）
- 當 XBRL / iXBRL 均無法取得時啟用
- 非同步並行查詢三個 dataset：
  - `TaiwanStockFinancialStatements`（損益表）
  - `TaiwanStockBalanceSheet`（資產負債表）
  - `TaiwanStockCashFlowsStatement`（現金流量表）
- 過濾至目標季末日期，轉換為 canonical 欄位
- 值從完整新台幣（元）自動換算為千元

**PDF 文字萃取**（與上述平行進行）
- 萃取每一頁全文 → `document_pages`
- 偵測財務章節（損益表、資產負債表、現金流量表等）→ `document_sections`
- 切割為 RAG 文字片段（~600 字/片段，50 字重疊）→ `document_chunks`
- 無 XBRL 時額外嘗試 PDF 表格解析（信心度 0.75）

所有財務數字存入 `financial_facts`，完成後 status 更新為 `extracted`。

**輸出範例：**
```
2330_2024Q1: facts=21, chunks=2681, status=completed
```

### Stage 3 — Validate（驗證）

```bash
uv run fr validate 2330 2024 Q1
```

執行七條財務邏輯驗證規則，並計算整體品質分數：

| 規則 | 檢查內容 | 嚴重度 |
|------|----------|--------|
| `balance_sheet_equation` | 資產 = 負債 + 權益（±1% 容許誤差） | error |
| `gross_profit_lte_revenue` | 毛利 ≤ 營收 | error |
| `income_consistency` | 營業利益 ≤ 毛利 | error |
| `eps_consistency` | EPS 與淨利正負號一致 | error |
| `current_ratio_positive` | 流動比率 > 0 | warning |
| `cf_quality` | 營業現金流 / 淨利 ≥ 0.7 | warning |
| `revenue_positive` | 營收 > 0 | info |

**品質分數（0.0–1.0）：**

```
quality_score = 0.40 × XBRL 覆蓋率
              + 0.30 × 關鍵欄位完整度（9 項）
              + 0.20 × 驗證通過率
              + 0.10 × 佐證覆蓋率
```

九項關鍵欄位：net_revenue、gross_profit、operating_income、net_income、eps_basic、total_assets、total_liabilities、equity、operating_cash_flow

完成後 status 更新為 `validated`。

### Stage 4 — Insights（洞察）

```bash
uv run fr insights 2330 2024 Q1
```

**計算財務指標** → 存入 `financial_metrics`：

| 指標 | 公式 |
|------|------|
| gross_margin | 毛利 / 營收 |
| operating_margin | 營業利益 / 營收 |
| net_margin | 淨利 / 營收 |
| current_ratio | 流動資產 / 流動負債 |
| debt_to_equity | 總負債 / 權益 |
| roe | 淨利 / 權益 |
| roa | 淨利 / 總資產 |
| book_value_per_share | 權益 / (股本 / 面額 10 元) |
| free_cash_flow | 營業現金流 − \|資本支出\| |
| cf_quality | 營業現金流 / 淨利 |

**計算 YoY / QoQ 比較** → 存入 `period_comparisons`：
- 對每個共同欄位計算：絕對變化量、百分比變化、方向（up/down/flat）
- 顯著性分級：large（≥10%）/ moderate（≥3%）/ small（<3%）

**偵測財務事件** → 存入 `detected_events`：

| 事件 | 觸發條件 | 嚴重度 |
|------|----------|--------|
| revenue_growth_acceleration | YoY 營收成長 > 30% | info |
| revenue_decline | YoY 營收衰退 < −10% | warning |
| gross_margin_compression | YoY 毛利率下滑 < −3% | warning |
| fcf_negative | 自由現金流 < 0 | warning |
| inventory_buildup | QoQ 存貨成長 > 20% 且營收低成長 | info |
| cash_flow_quality_warning | 現金流品質 < 0.7 | warning |

**產生洞察卡片** → 存入 `insight_cards`（10 種）：

| 卡片類型 | 說明 |
|----------|------|
| performance_summary | 頂層財務概覽（營收、淨利、EPS、毛利率） |
| revenue_growth | 營收 YoY 變化分析 |
| margin_change | 毛利率 / 營業利益率 / 淨利率趨勢 |
| profitability_change | 淨利與 EPS 變化 |
| cash_flow_quality | 現金流品質（OCF vs 淨利） |
| balance_sheet_strength | 資產 / 負債 / 權益概覽 |
| working_capital_change | QoQ 流動性指標 |
| capex_and_investment | 資本支出趨勢 |
| debt_and_liquidity | 槓桿與流動比率 |
| risk_and_commitments | 驗證發現的風險因子 |

完成後 status 更新為 `insight_ready`。

---

## 4. CLI 完整指令參考

### 管道指令

```bash
# 完整四階段
uv run fr run <stock_code> <year> <quarter> [選項]

# 單一階段
uv run fr ingest   <stock_code> <year> <quarter>
uv run fr extract  <stock_code> <year> <quarter>
uv run fr validate <stock_code> <year> <quarter>
uv run fr insights <stock_code> <year> <quarter>

# 批次
uv run fr batch <batch.json> [選項]
```

**通用選項：**

| 選項 | 預設值 | 適用指令 | 說明 |
|------|--------|----------|------|
| `--db PATH` | `data/financial.db` | 全部 | SQLite 資料庫路徑 |
| `--output-dir PATH` | `data/raw` | ingest, run | 原始文件下載目錄 |
| `--force` | False | 全部 | 強制重新執行已完成的階段 |
| `--stages TEXT` | 全部 | run | 只執行指定階段，逗號分隔 |
| `--concurrency INT` | 4 | batch | 最大同時處理筆數 |

### 查詢指令

```bash
# 表格顯示（預設）
uv run fr show 2330 2024 Q1

# JSON 格式輸出
uv run fr show 2330 2024 Q1 --format json

# 簡要摘要
uv run fr show 2330 2024 Q1 --format summary

# 自然語言問答
uv run fr ask "<問題>" --stock <代碼> --year <年> --quarter <季>
```

### 使用範例

```bash
# 台積電 2024 Q1，完整執行
uv run fr run 2330 2024 Q1

# 只重跑 extract 和 insights
uv run fr run 2330 2024 Q1 --stages extract,insights --force

# 自訂資料庫路徑
uv run fr run 2330 2024 Q1 --db /data/prod.db --output-dir /data/raw

# 批次處理半導體族群
uv run fr batch examples/semiconductor_batch.json --concurrency 6

# 查詢問答
uv run fr ask "本季 EPS 為何大幅成長？" --stock 2330 --year 2024 --quarter Q1
uv run fr ask "現金流有無異常？" --stock 2454 --year 2024 --quarter Q2
```

---

## 5. 資料來源說明

### 來源優先順序（Stage 2 財務數字萃取）

```
XBRL（優先）→ iXBRL（次要）→ FinMind API（回退）
```

| 來源 | 取得內容 | 信心度 | 備註 |
|------|----------|--------|------|
| XBRL | 結構化財務數字（100+ tags） | 1.0 | MOPS 自動化存取受限，可能無法下載 |
| iXBRL | HTML 嵌入式財務數字 | 0.95 | 同上 |
| FinMind API | 三表結構化數字 | 0.95 | 免費層無需 token，目前主要使用來源 |
| PDF 表格解析 | 財務報表頁面數字 | 0.75 | 僅在以上三者均無法使用時啟用 |

### FinMind API 說明

**端點：** `https://api.finmindtrade.com/api/v4/data`

使用的三個 Dataset：

| Dataset | 內容 |
|---------|------|
| `TaiwanStockFinancialStatements` | 損益表（營收、毛利、EPS 等） |
| `TaiwanStockBalanceSheet` | 資產負債表（資產、負債、權益等） |
| `TaiwanStockCashFlowsStatement` | 現金流量表（OCF、投資、融資、資本支出） |

- 免費層可直接使用，有速率限制
- 數值單位為完整新台幣（元），系統自動除以 1000 轉換為千元
- 付費 token 可提高速率上限，設定於 `FINMIND_TOKEN` 環境變數

### 本地 PDF 快取

將 PDF 放入 `data/financial_reports/` 目錄，可省去下載時間：

```
data/financial_reports/
├── 202401_2330_AI1.pdf   ← 台積電 2024 Q1
├── 202402_2330_AI1.pdf   ← 台積電 2024 Q2
├── 202401_2317_AI1.pdf   ← 鴻海 2024 Q1
└── ...
```

**命名規則：** `{期間碼}_{股票代碼}_AI1.pdf`

| 期間碼 | 對應季別 |
|--------|--------|
| `{year}01` | Q1（例：202401） |
| `{year}02` | Q2 |
| `{year}03` | Q3 |
| `{year}04` | Q4 |

---

## 6. 資料庫結構

資料存放於 SQLite（預設：`data/financial.db`，WAL 模式支援並發讀寫）。共 17 張資料表：

### 核心資料表

**`financial_facts`** — 所有標準化財務數字

```
filing_id | field          | value      | unit          | period_type | source_type | confidence
──────────┼────────────────┼────────────┼───────────────┼─────────────┼─────────────┼───────────
1         | net_revenue    | 592640.0   | TWD_thousands | duration    | finmind     | 0.95
1         | gross_profit   | 313840.0   | TWD_thousands | duration    | finmind     | 0.95
1         | eps_basic      | 8.7        | TWD_per_share | duration    | finmind     | 0.95
1         | total_assets   | 6071140.0  | TWD_thousands | instant     | finmind     | 0.95
```

`source_type` 可為：`xbrl` / `ixbrl` / `finmind` / `pdf_table` / `pdf_text` / `computed`  
`period_type`：`duration`（流量，如營收）/ `instant`（時點，如資產）

**`financial_metrics`** — 計算後的財務比率

```
filing_id | metric_name    | value  | formula
──────────┼────────────────┼────────┼─────────────────────────────
1         | gross_margin   | 0.530  | gross_profit / net_revenue
1         | net_margin     | 0.428  | net_income / net_revenue
1         | roe            | 0.185  | net_income / equity
1         | free_cash_flow | 125000 | operating_cash_flow - |capex|
```

**`period_comparisons`** — YoY / QoQ 比較

```
field       | compare_type | current_value | prior_value | change_pct | direction | significance
────────────┼──────────────┼───────────────┼─────────────┼────────────┼───────────┼─────────────
net_revenue | yoy          | 592640        | 508630      | +16.52%    | up        | large
net_income  | yoy          | 253950        | 197350      | +28.68%    | up        | large
eps_basic   | qoq          | 8.70          | 7.58        | +14.78%    | up        | large
```

**`detected_events`** — 自動偵測的財務事件

```
event_type                  | severity | title
────────────────────────────┼──────────┼────────────────────
revenue_growth_acceleration | info     | 營收高速成長（YoY +16.5%）
gross_margin_compression    | warning  | 毛利率下滑（YoY −3.2%）
```

**`insight_cards`** — Agent 可直接讀取的結構化摘要

```
card_type           | title             | summary                        | sentiment
────────────────────┼───────────────────┼────────────────────────────────┼──────────
performance_summary | 2330 2024Q1 摘要  | 營收 5,926 億，淨利率 42.8%…  | positive
revenue_growth      | 營收成長分析      | YoY 成長 16.5%，超越市場預期… | positive
```

### 輔助資料表

| 資料表 | 說明 |
|--------|------|
| `companies` | 公司基本資料（代碼、名稱、產業） |
| `filings` | 季度申報記錄（狀態機、品質分數） |
| `source_documents` | 下載文件記錄（路徑、大小、checksum） |
| `fact_evidence` | 財務數字的原始文件佐證 |
| `document_pages` | PDF 全頁文字內容 |
| `document_sections` | PDF 章節切分（損益表、資產負債表等） |
| `document_chunks` | RAG 文字片段（~600 字/片段） |
| `chunk_embeddings` | 向量嵌入（選用，需 --extra vector） |
| `validation_results` | 七條驗證規則執行結果 |
| `text_summaries` | 文字摘要 |
| `insight_evidence` | 洞察卡片的佐證連結 |
| `pipeline_runs` | 管道執行日誌（稽核用） |

**Filing 狀態機：**

```
pending → ingested → extracted → validated → insight_ready
                                           ↘ failed
```

完整 Schema DDL 請參閱 [`SPEC.md`](SPEC.md)。

---

## 7. 財務數字標準化

所有來源的財務數字都對應至統一的 canonical 欄位名稱，單位統一為**新台幣千元**（EPS 為每股元）。

### 損益表欄位（period_type = duration）

| canonical 欄位 | 說明 | FinMind type |
|---------------|------|-------------|
| `net_revenue` | 營業收入 | Revenue |
| `gross_profit` | 毛利 | GrossProfit |
| `operating_income` | 營業利益 | OperatingIncome |
| `profit_before_tax` | 稅前淨利 | IncomeBeforeTax |
| `net_income` | 本期淨利 | IncomeAfterTaxes |
| `net_income_attributable_to_parent` | 歸屬母公司淨利 | EquityAttributableToOwnersOfParent |
| `eps_basic` | 基本每股盈餘（元/股） | EPS / BasicEPS |
| `eps_diluted` | 稀釋每股盈餘 | DilutedEPS |
| `operating_expenses` | 營業費用 | OperatingExpenses |
| `rd_expenses` | 研發費用 | ResearchAndDevelopmentExpenses |
| `tax_expense` | 所得稅費用 | TAX |
| `comprehensive_income` | 本期綜合損益 | TotalConsolidatedProfitForThePeriod |

### 資產負債表欄位（period_type = instant）

| canonical 欄位 | 說明 | FinMind type |
|---------------|------|-------------|
| `cash_and_equivalents` | 現金及約當現金 | CashAndCashEquivalents |
| `accounts_receivable` | 應收帳款 | AccountsReceivable |
| `inventory` | 存貨 | Inventories |
| `current_assets` | 流動資產合計 | CurrentAssets |
| `total_assets` | 資產總計 | Assets |
| `accounts_payable` | 應付帳款 | AccountsPayable |
| `current_liabilities` | 流動負債合計 | CurrentLiabilities |
| `total_liabilities` | 負債總計 | Liabilities |
| `equity` | 權益總計 | Equity |
| `retained_earnings` | 保留盈餘 | RetainedEarnings |
| `share_capital` | 股本 | CommonStocks |

### 現金流量表欄位（period_type = duration）

| canonical 欄位 | 說明 | FinMind type |
|---------------|------|-------------|
| `operating_cash_flow` | 營業活動現金流量 | CashProvidedByOperatingActivities |
| `investing_cash_flow` | 投資活動現金流量 | CashProvidedByInvestingActivities |
| `financing_cash_flow` | 融資活動現金流量 | CashProvidedByFinancingActivities |
| `capex` | 資本支出（購置不動產廠房設備） | PropertyAndPlantAndEquipment |
| `cash_ending` | 期末現金 | CashBalancesEndOfPeriod |

---

## 8. 計算指標與分析

### 財務指標（Stage 4 計算）

| 指標名稱 | 公式 | 單位 |
|---------|------|------|
| `gross_margin` | gross_profit / net_revenue | 比率 |
| `operating_margin` | operating_income / net_revenue | 比率 |
| `net_margin` | net_income / net_revenue | 比率 |
| `current_ratio` | current_assets / current_liabilities | 倍 |
| `debt_to_equity` | total_liabilities / equity | 倍 |
| `roe` | net_income / equity | 比率 |
| `roa` | net_income / total_assets | 比率 |
| `book_value_per_share` | equity / (share_capital / 10) | 元/股 |
| `free_cash_flow` | operating_cash_flow − \|capex\| | 千元 |
| `cf_quality` | operating_cash_flow / net_income | 比率 |

### YoY / QoQ 比較

- 系統自動從資料庫取得去年同期（YoY）與上一季（QoQ）資料
- 對每個共同欄位計算：絕對變化量、百分比變化、方向
- **顯著性分級：**
  - `large`：|變化%| ≥ 10%
  - `moderate`：3% ≤ |變化%| < 10%
  - `small`：|變化%| < 3%

### 自動偵測事件

| 事件類型 | 觸發條件 | 嚴重度 |
|---------|----------|--------|
| revenue_growth_acceleration | YoY 營收 > +30% | info |
| revenue_decline | YoY 營收 < −10% | warning |
| gross_margin_compression | YoY 毛利率 < −3% | warning |
| fcf_negative | 自由現金流 < 0 | warning |
| inventory_buildup | QoQ 存貨 > +20% 且 QoQ 營收 < +5% | info |
| cash_flow_quality_warning | OCF / 淨利 < 0.7 | warning |

---

## 9. 驗證規則

Stage 3 對每筆 filing 執行七條財務邏輯檢查：

| 規則名稱 | 檢查條件 | 嚴重度 | 說明 |
|---------|----------|--------|------|
| `balance_sheet_equation` | \|資產 − (負債 + 權益)\| / 資產 < 1% | error | 資產負債表平衡 |
| `gross_profit_lte_revenue` | 毛利 ≤ 營收 | error | 毛利不可超過營收 |
| `income_consistency` | 營業利益 ≤ 毛利 | error | 利益層層遞減邏輯 |
| `eps_consistency` | sign(EPS) = sign(淨利) | error | EPS 與淨利符號一致 |
| `current_ratio_positive` | 流動資產 / 流動負債 > 0 | warning | 流動比率須正值 |
| `cf_quality` | 營業現金流 / 淨利 ≥ 0.7 | warning | 淨利有足夠現金支撐 |
| `revenue_positive` | 營收 > 0 | info | 基本正常營業確認 |

---

## 10. 專案結構

```
FinancialReports/
├── src/
│   ├── cli.py                        # CLI 入口（fr 指令，typer）
│   │
│   ├── domain/
│   │   ├── identity.py               # FilingIdentity dataclass（stock_code, year, quarter）
│   │   ├── models.py                 # Pydantic v2 models（Filing, Fact, Chunk, InsightCard…）
│   │   └── taxonomy.py               # XBRL_TO_CANONICAL、KNOWN_XBRL_TAGS（100+ tags）
│   │
│   ├── sources/
│   │   ├── registry.py               # Client 工廠函數（singleton pattern）
│   │   ├── mops_client.py            # MOPS API：公司基本資料查詢
│   │   ├── xbrl_client.py            # XBRL / iXBRL 文件下載
│   │   ├── pdf_client.py             # TWSE PDF 下載（含本地快取檢查）
│   │   └── finmind_client.py         # FinMind API：三表非同步並行查詢
│   │
│   ├── parsers/
│   │   ├── xbrl_parser.py            # XBRL XML 解析（lxml），建立 context map
│   │   ├── ixbrl_parser.py           # iXBRL HTML 解析，萃取 ix:nonFraction
│   │   ├── pdf_text_parser.py        # PDF 全頁文字萃取（pdfplumber）
│   │   ├── pdf_table_parser.py       # PDF 表格解析（word-position 座標法）
│   │   └── pdf_section_parser.py     # 財務章節偵測 + RAG chunk 切割
│   │
│   ├── normalize/
│   │   ├── fact_mapper.py            # XBRL tag → canonical field，重複項目去除
│   │   ├── period_normalizer.py      # 民國/西元日期轉換，quarter_to_dates()
│   │   ├── unit_normalizer.py        # 單位統一（→ TWD_thousands / TWD_per_share）
│   │   └── company_mapper.py         # 股票代碼 → 公司名稱、產業解析
│   │
│   ├── storage/
│   │   ├── schema.sql                # 17 張表完整 DDL（含 PRAGMA 設定）
│   │   ├── sqlite_store.py           # SQLAlchemy Core wrapper（upsert、bulk save）
│   │   ├── json_exporter.py          # 匯出 filing 資料為 JSON
│   │   └── vector_store.py           # 向量儲存介面（ChromaDB，佔位）
│   │
│   ├── analytics/
│   │   ├── metrics.py                # 財務指標計算（純函數）
│   │   ├── comparisons.py            # YoY / QoQ 比較、顯著性分級
│   │   ├── event_detector.py         # 規則引擎：偵測財務異常事件
│   │   └── insight_builder.py        # 10 種洞察卡片建立
│   │
│   ├── validation/
│   │   ├── rules.py                  # 七條財務邏輯驗證規則
│   │   ├── reconciler.py             # 多來源交叉比對（XBRL vs PDF vs FinMind）
│   │   └── quality_score.py          # 四維品質分數計算
│   │
│   ├── agent/
│   │   ├── query_service.py          # 高層查詢 API（facts / insights / text）
│   │   ├── retriever.py              # 關鍵字檢索（FactRetriever、ChunkRetriever）
│   │   └── context_builder.py        # LLM context pack 組裝（送給 OpenAI 前）
│   │
│   └── pipeline/
│       ├── run.py                    # 管道協調器（串接四階段）
│       ├── ingest.py                 # Stage 1：下載
│       ├── extract.py                # Stage 2：萃取
│       ├── validate.py               # Stage 3：驗證
│       └── build_insights.py         # Stage 4：洞察
│
├── tests/                            # pytest 測試套件
├── examples/
│   ├── test_20.json                  # 20 筆批次測試（10 家公司 × 多季）
│   ├── batch_query.json              # 查詢批次設定
│   └── semiconductor_batch.json      # 半導體族群批次設定
├── data/
│   ├── financial.db                  # SQLite 資料庫（預設路徑）
│   ├── raw/                          # 下載的 XBRL / iXBRL 暫存
│   └── financial_reports/            # PDF 本地快取
├── config/
│   ├── crawler_config.json           # 爬蟲設定（timeout、重試次數等）
│   └── xbrl_tags.json                # XBRL tag 對應表
├── SPEC.md                           # 完整技術規格文件
├── pyproject.toml                    # 專案設定與依賴
├── uv.lock                           # 鎖定依賴版本
└── .env                              # 環境變數（OPENAI_API_KEY 等）
```

---

## 11. 開發指南

### 執行測試

```bash
uv run pytest                              # 全部測試
uv run pytest tests/test_parsers.py -v    # 指定測試檔案
uv run pytest --cov=src/ --cov-report=html # 覆蓋率報告
```

### 程式碼品質

```bash
uv run ruff check src/ tests/    # Lint 檢查
uv run ruff format src/ tests/   # 自動格式化
uv run mypy src/ --strict        # 型別檢查
```

### 核心依賴

| 套件 | 用途 |
|------|------|
| `httpx` | 非同步 HTTP 客戶端（FinMind / MOPS / TWSE） |
| `lxml` | XML / HTML 解析（XBRL / iXBRL） |
| `pydantic` v2 | 資料模型驗證 |
| `sqlalchemy` | 資料庫操作（Core，非 ORM） |
| `typer` + `rich` | CLI 框架與終端機美化 |
| `pdfplumber` | PDF 文字與座標萃取（--extra pdf） |
| `openai` | LLM 問答（--extra llm） |

完整依賴清單請參閱 `pyproject.toml`。

---

## 參考

- [完整技術規格（SPEC.md）](SPEC.md) — Input/Output 規格、DB Schema、所有規則細節
- [FinMind API 文件](https://finmindtrade.com/) — 財務數據 API 說明
- [uv 文件](https://docs.astral.sh/uv/) — 套件管理工具
