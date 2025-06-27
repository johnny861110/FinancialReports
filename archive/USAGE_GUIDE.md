# 🎯 ETF 0050 財報爬蟲 - 快速使用指南

## 📁 整理後的專案結構

```
FinancialReports/
├── crawlers/                           # 🕷️ 核心爬蟲工具
│   ├── twse_financial_crawler.py      # TWSE財報爬蟲核心
│   └── etf0050_twse_complete_crawler.py # ETF 0050批次爬蟲
├── tools/                              # 🔧 輔助工具
│   └── check_download_results.py      # 結果檢查工具
├── data/                               # 📊 下載的數據
│   └── etf0050_reports/               # ETF 0050財報數據
├── config/                             # ⚙️ 配置檔案
├── legacy/                             # 📦 舊版工具備份
├── docs/                               # 📚 文檔
└── README.md                           # 📖 專案說明
```

## 🚀 立即開始使用

### 1. 批次下載財報

```bash
# 進入爬蟲目錄
cd crawlers

# 運行ETF 0050批次爬蟲
python etf0050_twse_complete_crawler.py

# 選擇模式：
# 1 = 測試模式 (3家公司 × 2期間 = 6任務)
# 2 = 小批量 (5家公司 × 4期間 = 20任務) 
# 3 = 完整爬取 (20家公司 × 8期間 = 160任務)
```

### 2. 檢查下載結果

```bash
# 進入工具目錄
cd tools

# 檢查下載結果
python check_download_results.py
```

## ✅ 已驗證功能

### 🎯 成功率統計
- **測試成功率**: 83.3% (6次嘗試，5次成功)
- **已下載檔案**: 5個IFRSs合併財報PDF
- **驗證公司**: 台積電、聯發科、鴻海

### 📋 已成功下載的資料
```
✅ 台積電(2330): 2024Q1, 2024Q2
✅ 聯發科(2454): 2024Q1, 2024Q2  
✅ 鴻海(2317): 2024Q1
```

### 🔧 技術特色
- ✅ 使用TWSE官方網站 (https://doc.twse.com.tw/)
- ✅ 無需Selenium，使用HTTP請求更穩定
- ✅ 自動處理JavaScript表單提交
- ✅ 支援中間頁面跳轉和實際PDF下載
- ✅ 完整的進度追蹤和錯誤記錄
- ✅ 自動目錄組織（按公司、按期間）

## 📊 下載的檔案格式

下載的PDF檔案會按以下結構組織：

```
data/etf0050_reports/
├── by_company/                    # 按公司分類
│   ├── 2330/                     # 台積電
│   │   ├── 2024Q1/
│   │   │   ├── 202401_2330_AI1.pdf
│   │   │   └── download_summary.json
│   │   └── 2024Q2/
│   └── 2454/                     # 聯發科
└── by_period/                     # 按期間分類
    ├── 2024Q1/
    └── 2024Q2/
```

## 🎮 進階使用

### 擴大下載範圍
如果測試成功，可以選擇更大的批次：
- **小批量**: 5家公司，4個期間 (20任務)
- **完整爬取**: 20家公司，8個期間 (160任務)

### 自訂公司清單
編輯 `crawlers/etf0050_twse_complete_crawler.py` 中的 `etf0050_stocks` 變數來自訂要下載的公司。

### 自訂期間範圍
編輯 `target_periods` 變數來設定要下載的年份和季度。

## 🛠️ 故障排除

### 1. 下載失敗
- 檢查網路連接
- 確認股票代號正確
- 查看 `reports/errors_*.json` 瞭解詳細錯誤

### 2. 檔案不存在
- 確保在正確的目錄執行命令
- 檢查 `data/etf0050_reports/` 目錄是否存在

### 3. 進度追蹤
每次爬取會生成詳細報告：
- `reports/crawl_summary_*.json` - 總結統計
- `reports/errors_*.json` - 錯誤詳情

## 🔄 專案維護

### 備份位置
重要檔案已備份到: `backup_20250627_000005/`

### 清理報告
查看 `cleanup_report.json` 瞭解整理詳情

---

**最後更新**: 2025年6月26日  
**專案狀態**: ✅ 可立即使用  
**建議**: 先運行測試模式驗證功能，再擴大到批次下載
