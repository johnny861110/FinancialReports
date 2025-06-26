# 📁 專案結構總覽

## 整理後的資料夾結構

```
FinancialReports/
├── 📄 QUICK_START.md                    # 快速開始指南
├── 📄 requirements.txt                  # Python套件需求
├── 📄 organize_project_simple.py        # 專案整理工具
│
├── 🔧 scripts/                          # 腳本檔案目錄
│   ├── 🕷️ crawlers/                    # 爬蟲腳本
│   │   ├── comprehensive_financial_crawler.py    # 主要批次爬蟲
│   │   ├── diagnostic_batch_crawler.py          # 診斷批次爬蟲
│   │   ├── financial_crawler_guide.py          # 爬蟲使用指南
│   │   └── main.py                              # 主程式進入點
│   │
│   ├── 🧪 tests/                       # 測試腳本
│   │   ├── improved_2330_test.py                # 改進版台積電測試 ⭐
│   │   ├── simple_2330_test.py                  # 簡化版測試
│   │   └── test_2330_2025q1.py                  # 2025Q1專用測試
│   │
│   ├── 🛠️ tools/                       # 工具腳本
│   │   └── setup_pdf_parsing.py                # PDF解析設定
│   │
│   └── ✅ validation/                   # 驗證腳本
│       ├── validate_download.py                # 下載結果驗證 ⭐
│       └── check_pdf_content.py                # PDF內容檢查
│
├── 💾 data/                             # 數據檔案目錄
│   ├── 📊 financial_reports/            # 主要財報數據
│   │   ├── by_company/                  # 按公司分類
│   │   │   ├── 2330_台積電/
│   │   │   ├── 2454_聯發科/
│   │   │   └── 2317_鴻海/
│   │   ├── by_season/                   # 按季度分類
│   │   └── search_indexes/              # 搜尋索引
│   │
│   ├── 🧪 test_results/                 # 測試結果
│   │   ├── 202501_2330_AI1.pdf          # 台積電2025Q1財報 ⭐
│   │   └── 202501_2330_AI1.json         # 對應JSON元數據 ⭐
│   │
│   └── 🔍 debug_logs/                   # 調試記錄
│       └── debug_responses/             # 網站回應記錄
│
├── 📚 docs/                             # 文件資料目錄
│   ├── 📖 guides/                       # 使用指南
│   │   ├── HOW_TO_CRAWL.md              # 完整爬蟲使用說明 ⭐
│   │   ├── README.md                    # 專案說明
│   │   └── USAGE_GUIDE.md               # 使用指南
│   │
│   └── 📋 reports/                      # 報告文件
│       ├── TEST_REPORT_2330_2025Q1.md   # 台積電測試報告 ⭐
│       ├── PROJECT_STATUS.md            # 專案狀態
│       ├── PROJECT_STATUS_UPDATE_*.md   # 狀態更新
│       ├── FINAL_SUMMARY.md             # 最終總結
│       └── PROJECT_CLEANUP_REPORT.md    # 清理報告
│
├── ⚙️ config/                           # 配置檔案目錄
│   └── settings/                        # 設定檔案
│       ├── __init__.py
│       ├── settings.py                  # 主要設定
│       └── xbrl_tags.json               # XBRL標籤配置
│
├── 💾 backup/                           # 備份檔案目錄
│   └── archives/                        # 存檔備份
│
├── 📤 output/                           # 輸出檔案目錄
│   ├── downloads/                       # 下載檔案暫存
│   └── logs/                            # 運行日誌
│
├── 🗂️ crawlers/                        # 舊版爬蟲檔案
├── 🛠️ tools/                           # 舊版工具檔案
├── 📁 docs/ (舊版)                      # 舊版文件
└── 📦 final_backup_*/                   # 最終備份
```

## ⭐ 重要檔案說明

### 🚀 立即可用
- **`QUICK_START.md`** - 30秒快速開始
- **`scripts/tests/improved_2330_test.py`** - 最穩定的測試腳本
- **`scripts/validation/validate_download.py`** - 結果驗證工具

### 📊 已驗證成果
- **`data/test_results/202501_2330_AI1.pdf`** - 成功下載的台積電2025Q1財報
- **`data/test_results/202501_2330_AI1.json`** - 完整的JSON元數據
- **`docs/reports/TEST_REPORT_2330_2025Q1.md`** - 詳細測試報告

### 📖 使用指南
- **`docs/guides/HOW_TO_CRAWL.md`** - 完整的爬蟲使用說明
- **`docs/guides/README.md`** - 專案總體說明
- **`docs/guides/USAGE_GUIDE.md`** - 詳細使用指南

## 🎯 使用建議

### 新手用戶
1. 閱讀 `QUICK_START.md`
2. 執行 `scripts/tests/improved_2330_test.py`
3. 用 `scripts/validation/validate_download.py` 驗證

### 進階用戶
1. 閱讀 `docs/guides/HOW_TO_CRAWL.md`
2. 使用 `scripts/crawlers/comprehensive_financial_crawler.py`
3. 查看 `docs/reports/` 中的測試報告

### 開發者
1. 檢查 `config/settings/` 中的配置
2. 參考 `docs/reports/TEST_REPORT_2330_2025Q1.md`
3. 使用 `scripts/crawlers/diagnostic_batch_crawler.py` 進行調試

---

**整理完成時間**: 2025-06-27 01:25  
**整理狀態**: ✅ 完成  
**下一步**: 參考 `QUICK_START.md` 開始使用
