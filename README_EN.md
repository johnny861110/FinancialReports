# Financial Reports Insight Engine

A Taiwan-listed company financial report analysis engine that converts XBRL / iXBRL / PDF source documents into structured financial data, computes financial metrics, automatically detects anomalous events, and generates insight cards ready for LLM Agent consumption.

```
XBRL / iXBRL / PDF / FinMind API
            │
            ▼  Stage 1: Ingest
     Download source documents (TWSE / MOPS / FinMind)
            │
            ▼  Stage 2: Extract
  financial_facts  (normalized financial figures)
  document_chunks  (PDF text segments for RAG)
            │
            ▼  Stage 3: Validate
    Validate financial logic, compute quality score (0–1)
            │
            ▼  Stage 4: Insights
  financial_metrics  ← gross margin, ROE, FCF…
  period_comparisons ← YoY / QoQ comparisons
  detected_events    ← automatically detected anomalies
  insight_cards      ← agent-ready structured summaries
            │
            ▼
  fr ask "What are the key highlights for TSMC 2024 Q1?"
```

---

## Table of Contents

1. [Requirements & Installation](#1-requirements--installation)
2. [Quick Start](#2-quick-start)
3. [Pipeline Stages In Depth](#3-pipeline-stages-in-depth)
4. [CLI Command Reference](#4-cli-command-reference)
5. [Data Sources](#5-data-sources)
6. [Database Schema](#6-database-schema)
7. [Financial Data Normalization](#7-financial-data-normalization)
8. [Computed Metrics & Analysis](#8-computed-metrics--analysis)
9. [Validation Rules](#9-validation-rules)
10. [Project Structure](#10-project-structure)
11. [Development Guide](#11-development-guide)

---

## 1. Requirements & Installation

**Requirements:**
- Python 3.10+
- [uv](https://docs.astral.sh/uv/) package manager

**Installation:**

```bash
git clone <repo-url>
cd FinancialReports

# Install core dependencies
uv sync

# Recommended: also install PDF parsing support
uv sync --extra pdf
```

**Optional Feature Modules (Extras):**

| Extra | Install Command | Features Enabled | Packages |
|-------|-----------------|------------------|----------|
| `pdf` | `uv sync --extra pdf` | PDF text and table extraction | pdfplumber, pypdfium2 |
| `ocr` | `uv sync --extra ocr` | Scanned PDF recognition | PaddleOCR, OpenCV |
| `vector` | `uv sync --extra vector` | Vector semantic search | ChromaDB, sentence-transformers |
| `llm` | `uv sync --extra llm` | Natural language Q&A | openai, tiktoken |
| `all` | `uv sync --extra all` | All features | — |

**Environment Variables (`.env`):**

```bash
cp .env.example .env
# Fill in the following
OPENAI_API_KEY=sk-...       # Required for fr ask natural language queries
FINMIND_TOKEN=              # FinMind paid tier token (not required for free tier)
```

---

## 2. Quick Start

### Single Filing

```bash
# Run all four stages: download → parse → validate → generate insights
uv run fr run 2330 2024 Q1
```

After completion, view the results:

```bash
uv run fr show 2330 2024 Q1
```

### Batch Processing (20 Filings)

```bash
uv run fr batch examples/test_20.json --concurrency 4
```

The batch JSON format specifies stock code, year, and quarter for each filing:

```json
[
  { "stock_code": "2330", "company_name": "TSMC",       "year": 2024, "quarter": "Q1" },
  { "stock_code": "2317", "company_name": "Foxconn",    "year": 2024, "quarter": "Q2" },
  { "stock_code": "2454", "company_name": "MediaTek",   "year": 2024, "quarter": "Q3" }
]
```

**Field Specification:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `stock_code` | string | ✓ | Taiwan stock code (four-digit number) |
| `company_name` | string | ✗ | Company name for display only, does not affect processing |
| `year` | int | ✓ | Calendar year, e.g. `2024` |
| `quarter` | string | ✓ | `"Q1"` / `"Q2"` / `"Q3"` / `"Q4"` |

### Natural Language Q&A

```bash
# Requires OPENAI_API_KEY and --extra llm
uv run fr ask "Why did gross margin decline this quarter?" --stock 2330 --year 2024 --quarter Q1
uv run fr ask "How does free cash flow look?" --stock 2454 --year 2024 --quarter Q2
```

---

## 3. Pipeline Stages In Depth

Each stage has **idempotency protection**: completed stages are skipped by default unless `--force` is specified.

### Stage 1 — Ingest (Download)

```bash
uv run fr ingest 2330 2024 Q1
```

Downloads source documents from three origins in parallel via async I/O:

| Source | Content Retrieved | Notes |
|--------|-------------------|-------|
| MOPS | XBRL instance document | Primary source of structured financial figures |
| MOPS | iXBRL HTML | Fallback when XBRL is unavailable |
| TWSE / local cache | PDF financial report | Used for text extraction and notes |

- PDF downloads check the local cache (`data/financial_reports/`) first; only fetches remotely if not found
- Local PDF naming convention: `{period_code}_{stock_code}_AI1.pdf`
  - Example: `202401_2330_AI1.pdf` (TSMC 2024 Q1)
  - Period codes: Q1=`01`, Q2=`02`, Q3=`03`, Q4=`04`
- All download records are saved to the `source_documents` table (path, size, checksum)
- Filing status updated to `ingested` upon completion

### Stage 2 — Extract (Parse)

```bash
uv run fr extract 2330 2024 Q1
```

Attempts three financial data sources in priority order:

**Priority 1: XBRL** (confidence 1.0)
- Parses XML instance document
- Builds a context map (context_ref → period start/end dates)
- Maps ~100 XBRL tags to canonical field names

**Priority 2: iXBRL** (confidence 0.95)
- Parses `ix:nonFraction` elements from HTML
- Extracts tag names and values using the same logic as XBRL

**Priority 3: FinMind API** (confidence 0.95)
- Activated when both XBRL and iXBRL are unavailable
- Queries three datasets concurrently via async:
  - `TaiwanStockFinancialStatements` (income statement)
  - `TaiwanStockBalanceSheet` (balance sheet)
  - `TaiwanStockCashFlowsStatement` (cash flow statement)
- Filters to the target quarter-end date and maps to canonical fields
- Values are automatically converted from full TWD (yuan) to thousands (÷ 1000)

**PDF Text Extraction** (runs in parallel with the above)
- Extracts full-page text for every page → `document_pages`
- Detects financial statement sections (requires a 民國 date marker within 300 chars) → `document_sections`
- Splits into RAG text chunks (~600 chars/chunk, 50-char overlap) → `document_chunks`
- When no XBRL source is available, also attempts PDF table parsing (confidence 0.75)

All financial figures are saved to `financial_facts`. Filing status updated to `extracted`.

**Sample output:**
```
2330_2024Q1: facts=21, chunks=2681, status=completed
```

### Stage 3 — Validate (Quality Check)

```bash
uv run fr validate 2330 2024 Q1
```

Runs seven financial logic validation rules and computes an overall quality score:

| Rule | Check | Severity |
|------|-------|----------|
| `balance_sheet_equation` | Assets = Liabilities + Equity (±1% tolerance) | error |
| `gross_profit_lte_revenue` | Gross Profit ≤ Revenue | error |
| `income_consistency` | Operating Income ≤ Gross Profit | error |
| `eps_consistency` | Sign of EPS matches sign of Net Income | error |
| `current_ratio_positive` | Current Ratio > 0 | warning |
| `cf_quality` | Operating Cash Flow / Net Income ≥ 0.7 | warning |
| `revenue_positive` | Revenue > 0 | info |

**Quality Score (0.0–1.0):**

```
quality_score = 0.40 × XBRL coverage ratio
              + 0.30 × key field completeness (9 fields)
              + 0.20 × validation pass rate
              + 0.10 × evidence coverage ratio
```

Nine key fields: net_revenue, gross_profit, operating_income, net_income, eps_basic, total_assets, total_liabilities, equity, operating_cash_flow

Filing status updated to `validated` upon completion.

### Stage 4 — Insights (Analysis)

```bash
uv run fr insights 2330 2024 Q1
```

**Compute Financial Metrics** → saved to `financial_metrics`:

| Metric | Formula |
|--------|---------|
| gross_margin | gross_profit / net_revenue |
| operating_margin | operating_income / net_revenue |
| net_margin | net_income / net_revenue |
| current_ratio | current_assets / current_liabilities |
| debt_to_equity | total_liabilities / equity |
| roe | net_income / equity |
| roa | net_income / total_assets |
| book_value_per_share | equity / (share_capital / par value 10) |
| free_cash_flow | operating_cash_flow − \|capex\| |
| cf_quality | operating_cash_flow / net_income |

**Compute YoY / QoQ Comparisons** → saved to `period_comparisons`:
- For each common field: absolute change, percentage change, direction (up/down/flat)
- Significance levels: large (≥10%) / moderate (≥3%) / small (<3%)

**Detect Financial Events** → saved to `detected_events`:

| Event | Trigger | Severity |
|-------|---------|----------|
| revenue_growth_acceleration | YoY revenue growth > 30% | info |
| revenue_decline | YoY revenue decline < −10% | warning |
| gross_margin_compression | YoY gross margin change < −3% | warning |
| fcf_negative | Free cash flow < 0 | warning |
| inventory_buildup | QoQ inventory growth > 20% and QoQ revenue growth < 5% | info |
| cash_flow_quality_warning | OCF / Net Income < 0.7 | warning |

**Generate Insight Cards** → saved to `insight_cards` (10 types):

| Card Type | Description |
|-----------|-------------|
| performance_summary | Top-level overview (revenue, net income, EPS, gross margin) |
| revenue_growth | Revenue YoY change analysis |
| margin_change | Gross / operating / net margin trend |
| profitability_change | Net income and EPS change |
| cash_flow_quality | Cash flow quality (OCF vs net income) |
| balance_sheet_strength | Assets / liabilities / equity overview |
| working_capital_change | QoQ liquidity metrics |
| capex_and_investment | Capital expenditure trend |
| debt_and_liquidity | Leverage and current ratio |
| risk_and_commitments | Risk factors surfaced by validation |

Filing status updated to `insight_ready` upon completion.

---

## 4. CLI Command Reference

### Pipeline Commands

```bash
# Full four-stage pipeline
uv run fr run <stock_code> <year> <quarter> [options]

# Individual stages
uv run fr ingest   <stock_code> <year> <quarter>
uv run fr extract  <stock_code> <year> <quarter>
uv run fr validate <stock_code> <year> <quarter>
uv run fr insights <stock_code> <year> <quarter>

# Batch processing
uv run fr batch <batch.json> [options]
```

**Common Options:**

| Option | Default | Applies To | Description |
|--------|---------|------------|-------------|
| `--db PATH` | `data/financial.db` | all | SQLite database path |
| `--output-dir PATH` | `data/raw` | ingest, run | Directory for downloaded source files |
| `--force` | False | all | Force re-run of already-completed stages |
| `--stages TEXT` | all | run | Only run specified stages (comma-separated) |
| `--concurrency INT` | 4 | batch | Maximum number of concurrent filings |

### Query Commands

```bash
# Table display (default)
uv run fr show 2330 2024 Q1

# JSON format output
uv run fr show 2330 2024 Q1 --format json

# Brief summary
uv run fr show 2330 2024 Q1 --format summary

# Natural language Q&A
uv run fr ask "<question>" --stock <code> --year <year> --quarter <quarter>
```

### Usage Examples

```bash
# TSMC 2024 Q1, full pipeline
uv run fr run 2330 2024 Q1

# Re-run only extract and insights stages
uv run fr run 2330 2024 Q1 --stages extract,insights --force

# Custom database path
uv run fr run 2330 2024 Q1 --db /data/prod.db --output-dir /data/raw

# Batch process semiconductor sector
uv run fr batch examples/semiconductor_batch.json --concurrency 6

# Natural language queries
uv run fr ask "Why did EPS grow significantly this quarter?" --stock 2330 --year 2024 --quarter Q1
uv run fr ask "Are there any cash flow anomalies?" --stock 2454 --year 2024 --quarter Q2
```

---

## 5. Data Sources

### Source Priority Order (Stage 2 Financial Data Extraction)

```
XBRL (primary) → iXBRL (secondary) → FinMind API (fallback)
```

| Source | Content | Confidence | Notes |
|--------|---------|------------|-------|
| XBRL | Structured financial figures (100+ tags) | 1.0 | MOPS blocks automated access; may be unavailable |
| iXBRL | HTML-embedded financial figures | 0.95 | Same access limitations as XBRL |
| FinMind API | Three-statement structured data | 0.95 | Free tier requires no token; currently the primary used source |
| PDF table parsing | Numbers from financial statement pages | 0.75 | Only activated when all three sources above are unavailable |

### FinMind API Details

**Endpoint:** `https://api.finmindtrade.com/api/v4/data`

Datasets used:

| Dataset | Content |
|---------|---------|
| `TaiwanStockFinancialStatements` | Income statement (revenue, gross profit, EPS, etc.) |
| `TaiwanStockBalanceSheet` | Balance sheet (assets, liabilities, equity, etc.) |
| `TaiwanStockCashFlowsStatement` | Cash flow statement (OCF, investing, financing, capex) |

- Free tier works without a token; subject to rate limiting
- Values are in full TWD (yuan); the system automatically divides by 1,000 to convert to thousands
- A paid token can be set via the `FINMIND_TOKEN` environment variable to increase rate limits

### Local PDF Cache

Place PDF files in the `data/financial_reports/` directory to skip downloading:

```
data/financial_reports/
├── 202401_2330_AI1.pdf   ← TSMC 2024 Q1
├── 202402_2330_AI1.pdf   ← TSMC 2024 Q2
├── 202401_2317_AI1.pdf   ← Foxconn 2024 Q1
└── ...
```

**Naming convention:** `{period_code}_{stock_code}_AI1.pdf`

| Period Code | Quarter |
|-------------|---------|
| `{year}01` | Q1 (e.g. 202401) |
| `{year}02` | Q2 |
| `{year}03` | Q3 |
| `{year}04` | Q4 |

---

## 6. Database Schema

Data is stored in SQLite (default: `data/financial.db`, WAL mode for concurrent read/write). There are 17 tables in total.

### Core Tables

**`financial_facts`** — All normalized financial figures

```
filing_id | field          | value      | unit          | period_type | source_type | confidence
──────────┼────────────────┼────────────┼───────────────┼─────────────┼─────────────┼───────────
1         | net_revenue    | 592640.0   | TWD_thousands | duration    | finmind     | 0.95
1         | gross_profit   | 313840.0   | TWD_thousands | duration    | finmind     | 0.95
1         | eps_basic      | 8.7        | TWD_per_share | duration    | finmind     | 0.95
1         | total_assets   | 6071140.0  | TWD_thousands | instant     | finmind     | 0.95
```

`source_type` values: `xbrl` / `ixbrl` / `finmind` / `pdf_table` / `pdf_text` / `computed`  
`period_type`: `duration` (flow, e.g. revenue) / `instant` (point-in-time, e.g. assets)

**`financial_metrics`** — Computed financial ratios

```
filing_id | metric_name    | value  | formula
──────────┼────────────────┼────────┼─────────────────────────────
1         | gross_margin   | 0.530  | gross_profit / net_revenue
1         | net_margin     | 0.428  | net_income / net_revenue
1         | roe            | 0.185  | net_income / equity
1         | free_cash_flow | 125000 | operating_cash_flow - |capex|
```

**`period_comparisons`** — YoY / QoQ comparisons

```
field       | compare_type | current_value | prior_value | change_pct | direction | significance
────────────┼──────────────┼───────────────┼─────────────┼────────────┼───────────┼─────────────
net_revenue | yoy          | 592640        | 508630      | +16.52%    | up        | large
net_income  | yoy          | 253950        | 197350      | +28.68%    | up        | large
eps_basic   | qoq          | 8.70          | 7.58        | +14.78%    | up        | large
```

**`detected_events`** — Automatically detected financial events

```
event_type                  | severity | title
────────────────────────────┼──────────┼────────────────────────────────────
revenue_growth_acceleration | info     | Revenue high growth (YoY +16.5%)
gross_margin_compression    | warning  | Gross margin declined (YoY −3.2%)
```

**`insight_cards`** — Structured summaries ready for LLM Agent consumption

```
card_type           | title                  | summary                               | sentiment
────────────────────┼────────────────────────┼───────────────────────────────────────┼──────────
performance_summary | 2330 2024Q1 Summary    | Revenue NT$592.6B, net margin 42.8%…  | positive
revenue_growth      | Revenue Growth         | YoY growth 16.5%, beat expectations…  | positive
```

### Supporting Tables

| Table | Description |
|-------|-------------|
| `companies` | Company master data (code, name, industry) |
| `filings` | Quarterly filing records (state machine, quality score) |
| `source_documents` | Downloaded file records (path, size, checksum) |
| `fact_evidence` | Source document evidence linking to financial facts |
| `document_pages` | Full-page text content from PDFs |
| `document_sections` | PDF section splits (income statement, balance sheet, etc.) |
| `document_chunks` | RAG text segments (~600 chars/chunk) |
| `chunk_embeddings` | Vector embeddings (optional, requires --extra vector) |
| `validation_results` | Results of the seven validation rule checks |
| `text_summaries` | Text summaries |
| `insight_evidence` | Evidence links for insight cards |
| `pipeline_runs` | Pipeline execution audit log |

**Filing State Machine:**

```
pending → ingested → extracted → validated → insight_ready
                                           ↘ failed
```

For the complete Schema DDL for all 17 tables, see [`SPEC.md`](SPEC.md).

---

## 7. Financial Data Normalization

All financial figures from every source are mapped to a unified set of canonical field names. Units are standardized to **TWD thousands** (EPS uses TWD per share).

### Income Statement Fields (period_type = duration)

| Canonical Field | Description | FinMind Type |
|-----------------|-------------|-------------|
| `net_revenue` | Revenue | Revenue |
| `gross_profit` | Gross Profit | GrossProfit |
| `operating_income` | Operating Income | OperatingIncome |
| `profit_before_tax` | Profit Before Tax | IncomeBeforeTax |
| `net_income` | Net Income | IncomeAfterTaxes |
| `net_income_attributable_to_parent` | Net Income Attributable to Parent | EquityAttributableToOwnersOfParent |
| `eps_basic` | Basic EPS (TWD/share) | EPS / BasicEPS |
| `eps_diluted` | Diluted EPS | DilutedEPS |
| `operating_expenses` | Operating Expenses | OperatingExpenses |
| `rd_expenses` | R&D Expenses | ResearchAndDevelopmentExpenses |
| `tax_expense` | Income Tax Expense | TAX |
| `comprehensive_income` | Total Comprehensive Income | TotalConsolidatedProfitForThePeriod |

### Balance Sheet Fields (period_type = instant)

| Canonical Field | Description | FinMind Type |
|-----------------|-------------|-------------|
| `cash_and_equivalents` | Cash and Cash Equivalents | CashAndCashEquivalents |
| `accounts_receivable` | Accounts Receivable | AccountsReceivable |
| `inventory` | Inventories | Inventories |
| `current_assets` | Total Current Assets | CurrentAssets |
| `total_assets` | Total Assets | Assets |
| `accounts_payable` | Accounts Payable | AccountsPayable |
| `current_liabilities` | Total Current Liabilities | CurrentLiabilities |
| `total_liabilities` | Total Liabilities | Liabilities |
| `equity` | Total Equity | Equity |
| `retained_earnings` | Retained Earnings | RetainedEarnings |
| `share_capital` | Share Capital | CommonStocks |

### Cash Flow Statement Fields (period_type = duration)

| Canonical Field | Description | FinMind Type |
|-----------------|-------------|-------------|
| `operating_cash_flow` | Cash from Operating Activities | CashProvidedByOperatingActivities |
| `investing_cash_flow` | Cash from Investing Activities | CashProvidedByInvestingActivities |
| `financing_cash_flow` | Cash from Financing Activities | CashProvidedByFinancingActivities |
| `capex` | Capital Expenditures (PP&E purchases) | PropertyAndPlantAndEquipment |
| `cash_ending` | Ending Cash Balance | CashBalancesEndOfPeriod |

---

## 8. Computed Metrics & Analysis

### Financial Metrics (Computed in Stage 4)

| Metric Name | Formula | Unit |
|------------|---------|------|
| `gross_margin` | gross_profit / net_revenue | ratio |
| `operating_margin` | operating_income / net_revenue | ratio |
| `net_margin` | net_income / net_revenue | ratio |
| `current_ratio` | current_assets / current_liabilities | multiple |
| `debt_to_equity` | total_liabilities / equity | multiple |
| `roe` | net_income / equity | ratio |
| `roa` | net_income / total_assets | ratio |
| `book_value_per_share` | equity / (share_capital / 10) | TWD/share |
| `free_cash_flow` | operating_cash_flow − \|capex\| | TWD thousands |
| `cf_quality` | operating_cash_flow / net_income | ratio |

### YoY / QoQ Comparisons

- The system automatically retrieves prior year same quarter (YoY) and prior quarter (QoQ) data from the database
- For each common field, it computes: absolute change, percentage change, direction
- **Significance levels:**
  - `large`: |change %| ≥ 10%
  - `moderate`: 3% ≤ |change %| < 10%
  - `small`: |change %| < 3%

### Automated Event Detection

| Event Type | Trigger Condition | Severity |
|-----------|-------------------|----------|
| revenue_growth_acceleration | YoY revenue > +30% | info |
| revenue_decline | YoY revenue < −10% | warning |
| gross_margin_compression | YoY gross margin < −3% | warning |
| fcf_negative | Free cash flow < 0 | warning |
| inventory_buildup | QoQ inventory > +20% and QoQ revenue < +5% | info |
| cash_flow_quality_warning | OCF / Net Income < 0.7 | warning |

---

## 9. Validation Rules

Stage 3 runs seven financial logic checks against each filing:

| Rule Name | Check Condition | Severity | Description |
|-----------|-----------------|----------|-------------|
| `balance_sheet_equation` | \|Assets − (Liabilities + Equity)\| / Assets < 1% | error | Balance sheet must balance |
| `gross_profit_lte_revenue` | Gross Profit ≤ Revenue | error | Gross profit cannot exceed revenue |
| `income_consistency` | Operating Income ≤ Gross Profit | error | Income diminishes at each layer |
| `eps_consistency` | sign(EPS) = sign(Net Income) | error | EPS and net income must share the same sign |
| `current_ratio_positive` | Current Assets / Current Liabilities > 0 | warning | Current ratio must be positive |
| `cf_quality` | Operating Cash Flow / Net Income ≥ 0.7 | warning | Net income should be sufficiently backed by cash |
| `revenue_positive` | Revenue > 0 | info | Confirms basic active operations |

---

## 10. Project Structure

```
FinancialReports/
├── src/
│   ├── cli.py                        # CLI entry point (fr command, typer)
│   │
│   ├── domain/
│   │   ├── identity.py               # FilingIdentity dataclass (stock_code, year, quarter)
│   │   ├── models.py                 # Pydantic v2 models (Filing, Fact, Chunk, InsightCard…)
│   │   └── taxonomy.py               # XBRL_TO_CANONICAL, KNOWN_XBRL_TAGS (100+ tags)
│   │
│   ├── sources/
│   │   ├── registry.py               # Client factory functions (singleton pattern)
│   │   ├── mops_client.py            # MOPS API: company metadata lookup
│   │   ├── xbrl_client.py            # XBRL / iXBRL document download
│   │   ├── pdf_client.py             # TWSE PDF download (with local cache check)
│   │   └── finmind_client.py         # FinMind API: three-statement concurrent async queries
│   │
│   ├── parsers/
│   │   ├── xbrl_parser.py            # XBRL XML parsing (lxml), builds context map
│   │   ├── ixbrl_parser.py           # iXBRL HTML parsing, extracts ix:nonFraction
│   │   ├── pdf_text_parser.py        # PDF full-page text extraction (pdfplumber)
│   │   ├── pdf_table_parser.py       # PDF table parsing (word-position coordinate method)
│   │   └── pdf_section_parser.py     # Financial section detection + RAG chunk splitting
│   │
│   ├── normalize/
│   │   ├── fact_mapper.py            # XBRL tag → canonical field, deduplication
│   │   ├── period_normalizer.py      # ROC/CE date conversion, quarter_to_dates()
│   │   ├── unit_normalizer.py        # Unit standardization (→ TWD_thousands / TWD_per_share)
│   │   └── company_mapper.py         # Stock code → company name and industry resolution
│   │
│   ├── storage/
│   │   ├── schema.sql                # Full DDL for all 17 tables (with PRAGMA settings)
│   │   ├── sqlite_store.py           # SQLAlchemy Core wrapper (upsert, bulk save)
│   │   ├── json_exporter.py          # Export filing data to JSON
│   │   └── vector_store.py           # Vector storage interface (ChromaDB, placeholder)
│   │
│   ├── analytics/
│   │   ├── metrics.py                # Financial metric computation (pure functions)
│   │   ├── comparisons.py            # YoY / QoQ comparisons, significance grading
│   │   ├── event_detector.py         # Rule engine: detect financial anomaly events
│   │   └── insight_builder.py        # Build 10 types of insight cards
│   │
│   ├── validation/
│   │   ├── rules.py                  # Seven financial logic validation rules
│   │   ├── reconciler.py             # Cross-source reconciliation (XBRL vs PDF vs FinMind)
│   │   └── quality_score.py          # Four-component quality score computation
│   │
│   ├── agent/
│   │   ├── query_service.py          # High-level query API (facts / insights / text)
│   │   ├── retriever.py              # Keyword retrieval (FactRetriever, ChunkRetriever)
│   │   └── context_builder.py        # Assemble LLM context pack (sent to OpenAI)
│   │
│   └── pipeline/
│       ├── run.py                    # Pipeline orchestrator (chains all four stages)
│       ├── ingest.py                 # Stage 1: download
│       ├── extract.py                # Stage 2: extract
│       ├── validate.py               # Stage 3: validate
│       └── build_insights.py         # Stage 4: insights
│
├── tests/                            # pytest test suite
├── examples/
│   ├── test_20.json                  # 20-filing batch test (10 companies × multiple quarters)
│   ├── batch_query.json              # Query batch config
│   └── semiconductor_batch.json      # Semiconductor sector batch config
├── data/
│   ├── financial.db                  # SQLite database (default path)
│   ├── raw/                          # Downloaded XBRL / iXBRL staging area
│   └── financial_reports/            # Local PDF cache
├── config/
│   ├── crawler_config.json           # Crawler settings (timeout, retry count, etc.)
│   └── xbrl_tags.json                # XBRL tag mapping table
├── SPEC.md                           # Full technical specification document
├── pyproject.toml                    # Project config and dependencies
├── uv.lock                           # Locked dependency versions
└── .env                              # Environment variables (OPENAI_API_KEY, etc.)
```

---

## 11. Development Guide

### Running Tests

```bash
uv run pytest                                  # Run all tests
uv run pytest tests/test_parsers.py -v        # Run a specific test file
uv run pytest --cov=src/ --cov-report=html    # Generate coverage report
```

### Code Quality

```bash
uv run ruff check src/ tests/    # Lint
uv run ruff format src/ tests/   # Auto-format
uv run mypy src/ --strict        # Type checking
```

### Core Dependencies

| Package | Purpose |
|---------|---------|
| `httpx` | Async HTTP client (FinMind / MOPS / TWSE) |
| `lxml` | XML / HTML parsing (XBRL / iXBRL) |
| `pydantic` v2 | Data model validation |
| `sqlalchemy` | Database operations (Core, not ORM) |
| `typer` + `rich` | CLI framework and terminal output styling |
| `pdfplumber` | PDF text and coordinate extraction (--extra pdf) |
| `openai` | LLM Q&A (--extra llm) |

For the complete dependency list, see `pyproject.toml`.

---

## References

- [Full Technical Specification (SPEC.md)](SPEC.md) — Input/Output specs, DB schema, all rule details
- [FinMind API Documentation](https://finmindtrade.com/) — Financial data API reference
- [uv Documentation](https://docs.astral.sh/uv/) — Package manager
