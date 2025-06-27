# 📖 文件導覽 - 找到您需要的資源

根據您的需求，快速找到對應的文件和工具！

## 🎯 我是新手，第一次使用

### 📋 建議閱讀順序
1. **`README.md`** - 專案總覽和特色介紹（5分鐘）
2. **`QUICK_START.md`** - 快速開始指南（3分鐘）
3. **執行 `python start_here.py`** - 互動式體驗（5分鐘）
4. **`USER_GUIDE.md`** - 完整使用指南（15分鐘）

### 🚀 立即開始
```bash
# 第一步：驗證安裝
python financial_crawler.py --stats

# 第二步：互動式導覽
python start_here.py

# 第三步：下載第一份財報
python financial_crawler.py examples/single_query.json
```

---

## 💼 我要執行日常工作

### 📥 下載財報
- **單筆下載**: 修改 `examples/single_query.json` → 執行
- **批次下載**: 修改 `examples/batch_query.json` → 執行
- **快速測試**: `python start_here.py`

### 🔍 搜尋財報
```bash
# 查看統計
python financial_crawler.py --stats

# 搜尋特定公司
python financial_crawler.py --search "公司名稱"
```

### ✅ 驗證結果
```bash
python test_crawler.py --validate data/financial_reports
```

---

## 🔧 我需要進階功能

### 📚 詳細說明
- **`docs/guides/HOW_TO_CRAWL.md`** - 完整爬蟲指南
- **`PROJECT_STRUCTURE.md`** - 專案結構說明
- **`config/settings.py`** - 系統設定檔

### 🛠️ 進階工具
- **`scripts/rebuild_master_index.py`** - 重建索引
- **`scripts/crawlers/`** - 批次爬蟲工具
- **`scripts/validation/`** - 驗證工具

---

## 📊 我想查看範例和格式

### 💡 查詢範例
- **`examples/single_query.json`** - 單筆查詢範例
- **`examples/batch_query.json`** - 批次查詢範例
- **`examples/demo_master_index.py`** - 索引功能示範

### 📋 檔案格式說明
查看 `PROJECT_STRUCTURE.md` 中的「檔案命名規則」章節

---

## ❓ 我遇到問題需要幫助

### 🚨 常見問題
1. **`QUICK_START.md`** → 「常見問題」章節
2. **`USER_GUIDE.md`** → 「常見問題與解決方案」章節
3. **`README.md`** → 「常見問題」章節

### 🔍 診斷工具
```bash
# 系統狀態檢查
python financial_crawler.py --stats

# 檔案驗證
python test_crawler.py --validate data/financial_reports

# 完整診斷
python scripts/crawlers/diagnostic_batch_crawler.py
```

---

## 🏗️ 我想了解專案結構

### 📁 檔案組織
- **`PROJECT_STRUCTURE.md`** - 完整目錄結構說明
- **`USER_GUIDE.md`** - 重要檔案位置說明

### 🗺️ 快速定位
| 需求 | 檔案/目錄 |
|------|-----------|
| 下載財報 | `financial_crawler.py` + `examples/` |
| 查看結果 | `data/financial_reports/` |
| 搜尋記錄 | `data/master_index.json` |
| 系統設定 | `config/settings.py` |
| 測試功能 | `test_crawler.py` |

---

## 📈 我想查看專案狀態和報告

### 📊 狀態檔案
- **`docs/reports/PROJECT_STATUS.md`** - 專案整體狀態
- **`docs/reports/TEST_REPORT_*.md`** - 測試報告
- **`data/master_index.json`** - 下載記錄統計

### 🔬 技術文件
- **`docs/guides/`** - 詳細技術指南
- **`config/`** - 配置檔案和說明

---

## 🎯 快速操作備忘錄

### 常用命令
```bash
# 查看系統狀態
python financial_crawler.py --stats

# 搜尋財報
python financial_crawler.py --search "關鍵字"

# 下載單筆
python financial_crawler.py examples/single_query.json

# 下載批次
python financial_crawler.py examples/batch_query.json

# 新手導覽
python start_here.py

# 驗證檔案
python test_crawler.py --validate data/financial_reports
```

### 重要檔案路徑
- **主程式**: `financial_crawler.py`
- **範例檔**: `examples/single_query.json`
- **下載結果**: `data/financial_reports/`
- **主索引**: `data/master_index.json`
- **設定檔**: `config/settings.py`

---

## 🔄 更新與維護

### 定期檢查
```bash
# 查看下載統計
python financial_crawler.py --stats

# 重建索引（如需要）
python scripts/rebuild_master_index.py

# 驗證所有檔案
python test_crawler.py --validate data/financial_reports
```

---

**💡 提示**: 如果仍有疑問，建議先執行 `python start_here.py` 進行互動式導覽！
