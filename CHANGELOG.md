# Changelog

所有重要變更記錄於此文件。格式參考 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.0.0/)。

---

## [Unreleased]

## [3.0.0] - 2026-08-28

### Added

- Added the versioned FastAPI v1 producer contract for typed consumers.
- Added schema and capability discovery, stock/period pagination, filing
  snapshot and context responses, bounded batch queries, refresh jobs, and
  health/readiness endpoints.
- Added rich filing envelopes containing canonical facts, units, absence
  states, quality, freshness, validation, comparisons, evidence, source
  documents, insight cards, and pipeline state.
- Added a committed OpenAPI artifact and runtime drift test.
- Added Financial Agent compatibility fixtures and contract tests.

### Changed

- Corrected FinMind mappings and added bank-sector canonical fields before
  publishing the v1 schema.
- Established HTTP as the supported cross-repository boundary; consumers do
  not access the producer SQLite database directly.

### Verified

- Python 3.10, 3.11, and 3.12 CI matrix passed before merge.
- Financial Agent consumed a real `2330/2025Q1` filing from producer `main`
  with JSON fallback disabled.

## [0.3.0] — 2026-06-08

### Fixed

#### FinMind 欄位對應全面修正（`src/sources/finmind_client.py`）

原始對應表使用的 FinMind type key 有多個與 API 實際回傳值不符，導致相關欄位在所有 filing 中系統性缺失：

| 欄位 | 修正前（不存在的 key） | 修正後（FinMind 實際 key） |
|------|----------------------|--------------------------|
| `total_assets` | `Assets` | `TotalAssets` |
| `operating_cash_flow` | `CashProvidedByOperatingActivities` | `CashFlowsFromOperatingActivities` |
| `financing_cash_flow` | `CashProvidedByFinancingActivities` | `CashFlowsProvidedFromFinancingActivities` |
| `accounts_receivable` | `AccountsReceivable` | `AccountsReceivableNet` |
| `share_capital` | `CommonStocks` | `CapitalStock` / `OrdinaryShare` |

同時新增各欄位的備援 key（fallback），提升來源相容性。

#### 銀行業損益表欄位補齊

金融股（2881/2882 等）FinMind 損益表使用不同 key，補入對應：

- `IncomeAfterTax` / `IncomeFromContinuingOperations` → `net_income`
- `PreTaxIncome` → `profit_before_tax`

### Added

#### 銀行業專用欄位（`src/domain/taxonomy.py`、`src/sources/finmind_client.py`）

新增三個金融業結構特有欄位：

| canonical 欄位 | FinMind type | 說明 |
|---------------|-------------|------|
| `net_interest_income` | `NetInterestIncome` | 淨利息收入 |
| `net_non_interest_income` | `NetNonInterestIncome` | 淨非利息收入 |
| `loan_loss_provisions` | `BadDebts` | 呆帳費用 / 信用損失準備 |

#### 銀行業品質評分獨立 key fields（`src/validation/quality_score.py`）

金融業資產負債表結構不同（無毛利、流動資產 / 負債分類），新增 `_KEY_FIELDS_BANK` 清單，股票代碼開頭 `28` 的 filing 自動使用銀行業標準評分：

銀行業 key fields：`net_revenue`, `net_interest_income`, `net_income`, `eps_basic`,
`total_assets`, `total_liabilities`, `equity`, `operating_cash_flow`

### Changed

#### 品質分數：XBRL 覆蓋率 → 資料來源覆蓋率（`src/validation/quality_score.py`）

原先 40% 的 XBRL 覆蓋率權重只計算 `source_type IN ('xbrl', 'ixbrl')` 的欄位，
導致所有來自 FinMind 的 filing 這一項永遠得 0 分，實際上限僅 0.6。

改為「資料來源覆蓋率」，涵蓋 `source_type IN ('xbrl', 'ixbrl', 'finmind')` 三種結構化來源：

```
quality_score = 0.40 × 資料來源覆蓋率   ← 原：XBRL 覆蓋率（FinMind 永遠 0 分）
              + 0.30 × 關鍵欄位完整度
              + 0.20 × 驗證通過率
              + 0.10 × 佐證覆蓋率
```

品質分數提升效果：

| 類型 | 修正前 | 修正後 |
|------|--------|--------|
| 一般股 | 0.43 | **0.82** |
| 金融股 | 0.33 | **0.75** |

### Removed

- 刪除 `9999_2024Q1` 測試假資料（股票代號 9999 不存在）

### Data

- 全部 28 個有效 filing 重新執行 extract → validate → insights
- `total_assets` 覆蓋：0/28 → **28/28**
- `operating_cash_flow` 覆蓋：0/28 → **28/28**
- Facts per filing（一般股）：21 → **27**
- Financial metrics per filing（一般股）：6 → **10**（新增 `roa`, `book_value_per_share`, `cf_quality`, `rd_intensity`）
- Detected events：0 → **35**（涵蓋 16 個 filing）

---

## [0.2.0] — 2025-10-01

### Added
- FinMind API 作為 XBRL 不可用時的主要資料來源
- `TaiwanStockFinancialStatements` / `TaiwanStockBalanceSheet` / `TaiwanStockCashFlowsStatement` 三表非同步並行查詢
- WAL 模式 SQLite，支援並發讀寫

### Changed
- 移除舊版架構（core、processors、validators、scripts 目錄）
- 重構為四階段 pipeline（ingest / extract / validate / insights）

---

## [0.1.0] — 2025-09-01

### Added
- 初始版本：XBRL / iXBRL / PDF 解析
- SQLite 資料庫設計（17 張資料表）
- CLI 基礎指令（`fr run`, `fr show`, `fr status`）
- 單元測試套件
