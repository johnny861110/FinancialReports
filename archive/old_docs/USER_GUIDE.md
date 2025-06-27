# 財報爬蟲使用指南 🚀

## 項目簡介

這是一個簡化的台灣上市公司財報爬蟲工具，支援**JSON格式**的單筆和批次查詢，讓您能夠輕鬆下載財務報告PDF和對應的結構化JSON數據。

## ✨ 主要特色

- ✅ **JSON統一輸入**: 所有查詢都使用JSON格式
- ✅ **單筆/批次查詢**: 靈活支援不同使用場景  
- ✅ **自動驗證**: 檔案格式和完整性檢查
- ✅ **結構化輸出**: PDF + JSON雙重格式
- ✅ **錯誤處理**: 詳細的錯誤訊息和重試機制
- ✅ **進度追蹤**: 批次查詢進度顯示

## 🚀 快速開始

### 1. 單筆查詢
```bash
python financial_crawler.py examples/single_query.json
```

### 2. 批次查詢  
```bash
python financial_crawler.py examples/batch_query.json
```

### 3. 直接JSON字串
```bash
python financial_crawler.py '{"stock_code":"2330","company_name":"台積電","year":2024,"season":"Q1"}'
```

## 📝 JSON輸入格式

### 單筆查詢
```json
{
  "stock_code": "2330",
  "company_name": "台積電",
  "year": 2024,
  "season": "Q1"
}
```

### 批次查詢
```json
[
  {
    "stock_code": "2330", 
    "company_name": "台積電",
    "year": 2024,
    "season": "Q1"
  },
  {
    "stock_code": "2454",
    "company_name": "聯發科", 
    "year": 2024,
    "season": "Q1"
  }
]
```

## 📊 必要欄位

| 欄位 | 說明 | 範例 |
|------|------|------|
| `stock_code` | 股票代碼 | "2330" |
| `company_name` | 公司名稱 | "台積電" |
| `year` | 報告年度 | 2024 |
| `season` | 報告季度 | "Q1", "Q2", "Q3", "Q4" |

## 🎯 使用範例

### 下載台積電最新財報
```bash
python financial_crawler.py '{"stock_code":"2330","company_name":"台積電","year":2024,"season":"Q2"}'
```

### 批次下載多家公司同期財報
```bash
python financial_crawler.py examples/batch_query.json
```

### 僅驗證JSON格式
```bash
python financial_crawler.py examples/single_query.json --validate-only
```

## 📁 輸出結構

```
data/
├── financial_reports/          # 下載的財報檔案
│   ├── 202401_2330_AI1.pdf    # PDF檔案
│   ├── 202401_2330_AI1.json   # 結構化數據
│   └── debug/                 # 調試記錄

output/                         # 查詢結果
└── query_results_*.json       # 執行結果摘要
```

## ⚙️ 命令列選項

```bash
python financial_crawler.py <JSON檔案或字串> [選項]

選項:
  --config CONFIG      指定配置檔案路徑
  --output OUTPUT      指定結果輸出檔案
  --validate-only      僅驗證JSON格式
```

## 🔧 配置文件

配置文件位於 `config/crawler_config.json`：

```json
{
  "output_dir": "data/financial_reports",
  "download_delay": 2,
  "max_retry": 3,
  "timeout": 30
}
```

## 📋 常見使用場景

### 1. 投資研究
批次下載多家公司同期財報進行比較分析

### 2. 數據收集
系統性收集特定時期的財報數據

### 3. 合規檢查
驗證和下載最新披露的財務報告

### 4. 學術研究
收集歷史財報數據進行研究分析

## ⚠️ 注意事項

1. **季度時間**: Q1、Q2、Q3、Q4 對應各季度財報
2. **檔案格式**: 下載的PDF檔案格式為 `YYYYMM_STOCKCODE_AI1.pdf`
3. **批次間隔**: 自動在請求間添加2秒延遲
4. **網路要求**: 需要穩定的網路連線

## 🆘 常見問題

### Q: 下載失敗怎麼辦？
A: 檢查股票代碼、年份季度是否正確，以及該期間財報是否已發布

### Q: 如何知道哪些財報可下載？
A: 一般上市公司在每季結束後1-2個月內發布財報

### Q: 支援哪些公司？
A: 支援所有台灣證交所上市公司（使用正確的股票代碼）

### Q: JSON格式錯誤怎麼辦？
A: 使用 `--validate-only` 選項檢查格式，或參考範例檔案

## 📞 技術支援

- 查看 `output/query_results_*.json` 了解執行結果
- 檢查 `data/financial_reports/debug/` 目錄中的調試檔案
- 確認網路連線和防火牆設定

---

🎉 **開始使用**: `python financial_crawler.py examples/single_query.json`
