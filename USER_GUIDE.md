# 新手完整使用指南 📖

這是一份詳細的使用指南，專門為第一次使用財報爬蟲的用戶設計。

## 🎯 您將學會什麼

- ✅ 安裝和設定系統
- ✅ 下載單家公司財報
- ✅ 批次下載多家公司財報
- ✅ 搜尋和管理已下載的財報
- ✅ 驗證下載結果的完整性
- ✅ 自訂查詢條件

## 📋 前置準備

### 系統需求
- Windows 10/11 或 macOS 或 Linux
- Python 3.7 以上版本
- 穩定的網路連線
- 約 500MB 可用硬碟空間

### 檢查 Python 版本
```bash
python --version
```
應該顯示 Python 3.7.x 或更新版本。

## 🚀 第一步：快速安裝

### 1. 下載專案
如果您還沒有專案檔案，請先下載或複製到本機。

### 2. 安裝套件
開啟命令提示字元或終端機，執行：

```bash
cd c:\Users\johnn\FinancialReports
pip install -r requirements.txt
```

### 3. 驗證安裝
```bash
python financial_crawler.py --stats
```

如果看到類似以下訊息，表示安裝成功：
```
📊 財報下載統計
================
總下載財報數量: 0
最後更新時間: 2025-06-27
```

## 📥 第二步：下載您的第一份財報

### 方法 A：使用互動式導覽（推薦新手）

```bash
python start_here.py
```

這個程式會引導您完成所有步驟，非常適合第一次使用。

### 方法 B：使用範例檔案

```bash
python financial_crawler.py examples/single_query.json
```

這會下載台積電 2024Q1 的財報。

### 方法 C：直接指定參數

```bash
python financial_crawler.py --stock-code 2330 --company "台積電" --year 2024 --season Q1
```

## 🔍 第三步：搜尋和管理財報

### 查看所有已下載的財報
```bash
python financial_crawler.py --stats
```

### 搜尋特定公司
```bash
# 按公司名稱搜尋
python financial_crawler.py --search "台積電"

# 按股票代碼搜尋
python financial_crawler.py --search "2330"

# 按年份搜尋
python financial_crawler.py --search "2024"
```

### 查看檔案位置
下載的檔案會儲存在：
- **PDF檔案**: `data/financial_reports/`
- **JSON資料**: 同目錄下的 .json 檔案
- **主索引**: `data/master_index.json`

## 📊 第四步：批次下載多家公司

### 編輯批次查詢檔案

開啟 `examples/batch_query.json`，內容如下：

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
  },
  {
    "stock_code": "2317",
    "company_name": "鴻海",
    "year": 2024,
    "season": "Q1"
  }
]
```

### 執行批次下載

```bash
python financial_crawler.py examples/batch_query.json
```

系統會依序下載列表中的所有財報。

## ✅ 第五步：驗證下載結果

### 自動驗證
系統會在下載時自動驗證檔案，通常不需要額外動作。

### 手動驗證
```bash
python test_crawler.py --validate data/financial_reports
```

### 檢查檔案大小
正常的季報 PDF 檔案通常在 3-8 MB 之間。如果檔案太小（< 1 MB），可能下載不完整。

## 🎯 第六步：自訂查詢

### 修改單筆查詢
編輯 `examples/single_query.json`：

```json
{
  "stock_code": "2317",
  "company_name": "鴻海",
  "year": 2023,
  "season": "Q4"
}
```

### 支援的季度格式
- **Q1**: 第一季（1-3月）
- **Q2**: 第二季（4-6月）
- **Q3**: 第三季（7-9月）
- **Q4**: 第四季（10-12月）

### 常見台灣50成分股代碼
- **2330**: 台積電
- **2454**: 聯發科
- **2317**: 鴻海
- **2382**: 廣達
- **3711**: 日月光投控
- **2308**: 台達電
- **6505**: 台塑化

## 🛠️ 進階功能

### 自訂輸出目錄
```bash
python financial_crawler.py examples/single_query.json --output-dir custom_folder
```

### 測試模式（不實際下載）
```bash
python financial_crawler.py examples/single_query.json --test
```

### 設定下載延遲
編輯 `config/settings.py` 修改延遲時間，避免對伺服器造成過大負擔。

## ❗ 常見問題與解決方案

### Q: 下載速度很慢
**A:** 這是正常現象。系統會自動加入 2-3 秒延遲，避免對 TWSE 伺服器造成過大負擔。

### Q: 某些公司財報下載失敗
**A:** 可能原因：
1. 該公司尚未公布該季度財報
2. 網站暫時無法存取
3. 股票代碼或公司名稱有誤

**解決方法：**
1. 確認財報發布時間（通常在季度結束後 1-2 個月）
2. 稍後重試
3. 檢查股票代碼是否正確

### Q: 檔案下載不完整
**A:** 執行驗證命令：
```bash
python test_crawler.py --validate data/financial_reports
```

如果發現問題，重新下載該檔案。

### Q: 如何查看錯誤訊息
**A:** 系統會在終端機顯示詳細的錯誤訊息。如果需要更多資訊，檢查 `data/debug/` 目錄（如果存在）。

### Q: 可以同時下載多個年度的財報嗎？
**A:** 可以，編輯 `examples/batch_query.json`，加入不同年度的查詢：

```json
[
  {
    "stock_code": "2330",
    "company_name": "台積電",
    "year": 2023,
    "season": "Q4"
  },
  {
    "stock_code": "2330",
    "company_name": "台積電",
    "year": 2024,
    "season": "Q1"
  }
]
```

## 🔄 定期維護

### 清理舊檔案
如果磁碟空間不足，可以刪除較舊的財報檔案。主索引檔案會自動更新。

### 更新套件
偶爾執行以下命令更新 Python 套件：
```bash
pip install -r requirements.txt --upgrade
```

### 備份重要資料
建議定期備份：
- `data/master_index.json` - 主索引檔案
- `data/financial_reports/` - 財報檔案
- 自訂的查詢檔案

## 🎉 恭喜！您已經掌握基本操作

現在您可以：
- 🎯 下載任何台灣上市公司的財報
- 🔍 快速搜尋已下載的財報
- 📊 批次處理多家公司
- ✅ 驗證下載結果的完整性

## 📚 進一步學習

- 查看 `README.md` 了解更多功能
- 探索 `scripts/` 目錄中的進階工具
- 閱讀 `docs/guides/` 中的詳細說明

---

**祝您使用愉快！如有問題，歡迎查看其他說明文件或提出問題。** 🎊
