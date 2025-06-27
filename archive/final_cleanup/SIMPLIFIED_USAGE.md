# 財報爬蟲統一介面使用說明

## 快速開始

### 1. 單筆查詢
```powershell
python financial_crawler.py examples/single_query.json
```

### 2. 批次查詢
```powershell
python financial_crawler.py examples/batch_query.json
```

### 3. 直接 JSON 字串查詢
```powershell
python financial_crawler.py '{"stock_code":"2330","company_name":"台積電","year":2025,"season":"Q1"}'
```

## JSON 輸入格式

### 單筆查詢格式
```json
{
  "stock_code": "2330",
  "company_name": "台積電", 
  "year": 2025,
  "season": "Q1",
  "test_mode": false
}
```

### 批次查詢格式
```json
[
  {
    "stock_code": "2330",
    "company_name": "台積電",
    "year": 2025,
    "season": "Q1"
  },
  {
    "stock_code": "2454", 
    "company_name": "聯發科",
    "year": 2025,
    "season": "Q1"
  }
]
```

## 必要欄位說明

- `stock_code`: 股票代碼 (如: "2330")
- `company_name`: 公司名稱 (如: "台積電")  
- `year`: 報告年度 (如: 2025)
- `season`: 報告季度 (如: "Q1", "Q2", "Q3", "Q4" 或 "1", "2", "3", "4")

## 可選欄位

- `test_mode`: 測試模式，儲存到測試目錄 (預設: false)

## 命令列選項

```powershell
python financial_crawler.py <JSON檔案或字串> [選項]

選項:
  --config CONFIG     指定配置檔案路徑
  --output OUTPUT     指定結果輸出檔案路徑  
  --validate-only     僅驗證輸入格式，不執行下載
```

## 輸出說明

### 下載結果
- **PDF檔案**: 儲存在 `data/financial_reports/` 目錄
- **JSON檔案**: 對應的結構化數據檔案
- **查詢結果**: 儲存在 `output/query_results_YYYYMMDD_HHMMSS.json`

### 目錄結構
```
data/
├── financial_reports/     # 正式下載結果
└── test_results/         # 測試模式結果

output/                   # 查詢結果記錄
└── query_results_*.json

examples/                 # JSON 輸入範例
├── single_query.json
├── batch_query.json
└── multi_period_query.json
```

## 常見使用場景

### 1. 下載最新一季財報
```powershell
python financial_crawler.py '{"stock_code":"2330","company_name":"台積電","year":2025,"season":"Q1"}'
```

### 2. 批次下載多家公司同期財報
```powershell
python financial_crawler.py examples/batch_query.json
```

### 3. 下載某公司多個期間財報
```powershell
python financial_crawler.py examples/multi_period_query.json
```

### 4. 測試模式下載
```json
{
  "stock_code": "2330",
  "company_name": "台積電",
  "year": 2025, 
  "season": "Q1",
  "test_mode": true
}
```

### 5. 僅驗證JSON格式
```powershell
python financial_crawler.py examples/single_query.json --validate-only
```

## 注意事項

1. **季度對應**: Q1=5月, Q2=8月, Q3=11月, Q4=次年2月發布
2. **下載間隔**: 批次查詢自動添加2秒間隔，避免請求過快
3. **檔案命名**: PDF檔案格式為 `YYMM_STOCKCODE_AI1.pdf`
4. **錯誤處理**: 失敗的查詢會在結果中標記，但不會中斷批次處理
5. **檔案驗證**: 自動檢查PDF檔案完整性和大小

## 錯誤排除

### 常見錯誤
- **查詢無結果**: 可能該期間尚未發布財報
- **下載超時**: 網路問題，可重試
- **檔案大小異常**: 可能下載不完整或格式錯誤

### 檢查步驟
1. 確認股票代碼和期間正確
2. 檢查網路連線
3. 查看錯誤訊息和輸出記錄
4. 必要時可開啟測試模式調試
