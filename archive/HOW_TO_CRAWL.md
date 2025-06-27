# 台灣ETF財報爬蟲系統 - 完整使用說明

## 📋 專案概述

這是一個專為台灣ETF 0050成分股設計的自動化財報收集系統，能夠批次下載、驗證、分類與索引上市公司的季度財報，重點關注台積電(2330)、聯發科(2454)、鴻海(2317)等重要成分股。

**支援期間**: 2022Q1 - 2025Q1  
**資料來源**: 台灣證券交易所(TWSE) doc.twse.com.tw  
**檔案格式**: PDF財報 + JSON結構化數據  

---

## 🚀 快速開始

### 1. 環境設定

```bash
# 安裝Python套件
pip install -r requirements.txt

# 檢查專案結構
ls scripts/
```

### 2. 立即測試 - 下載台積電2025Q1財報

```bash
# 進入測試目錄
cd scripts/tests/

# 執行改進版測試（推薦）
python improved_2330_test.py

# 驗證下載結果
cd ../validation/
python validate_download.py
```

### 3. 批次下載多公司財報

```bash
# 進入爬蟲目錄
cd scripts/crawlers/

# 執行綜合批次爬蟲
python comprehensive_financial_crawler.py

# 或使用診斷模式
python diagnostic_batch_crawler.py
```

---

## 📁 專案結構

```
FinancialReports/
├── scripts/                    # 🔧 腳本檔案
│   ├── crawlers/              # 🕷️ 爬蟲腳本
│   ├── tests/                 # 🧪 測試腳本
│   ├── tools/                 # 🛠️ 工具腳本
│   └── validation/            # ✅ 驗證腳本
├── data/                      # 💾 數據檔案
│   ├── financial_reports/     # 📊 主要財報
│   ├── test_results/          # 🧪 測試結果
│   └── debug_logs/            # 🔍 調試記錄
├── docs/                      # 📚 文件資料
│   ├── guides/                # 📖 使用指南
│   └── reports/               # 📋 報告文件
├── config/                    # ⚙️ 配置檔案
├── backup/                    # 💾 備份檔案
└── output/                    # 📤 輸出檔案
```

---

## 🕷️ 爬蟲腳本使用指南

### 主要爬蟲腳本

#### 1. `comprehensive_financial_crawler.py` - 綜合批次爬蟲
**功能**: 批次下載多公司多季度財報  
**適用**: 大規模數據收集  

```bash
cd scripts/crawlers/
python comprehensive_financial_crawler.py
```

**特色**:
- ✅ 自動重試機制
- 📊 進度追蹤與報告
- 🔄 續傳功能  
- 📁 自動分類儲存
- 🔍 完整性驗證

#### 2. `diagnostic_batch_crawler.py` - 診斷批次爬蟲
**功能**: 帶診斷功能的批次下載  
**適用**: 問題排除與測試  

```bash
cd scripts/crawlers/
python diagnostic_batch_crawler.py
```

**特色**:
- 🔍 詳細的debug記錄
- ⚠️ 錯誤分析報告
- 📋 下載狀態檢查
- 🛠️ 自動修復建議

#### 3. `financial_crawler_guide.py` - 爬蟲指南
**功能**: 互動式爬蟲使用指南  
**適用**: 新手學習與操作  

```bash
cd scripts/crawlers/
python financial_crawler_guide.py
```

#### 4. `main.py` - 主程式進入點
**功能**: 統一的程式進入點  
**適用**: 標準化操作流程  

```bash
cd scripts/crawlers/
python main.py
```

---

## 🧪 測試腳本使用指南

### 單一公司測試

#### 1. `improved_2330_test.py` - 改進版台積電測試
**推薦使用** - 最穩定的測試腳本

```bash
cd scripts/tests/
python improved_2330_test.py
```

**功能**:
- 📥 完整的兩步驟下載流程
- ✅ 多層次檔案驗證
- 📊 詳細的進度報告
- 🔧 自動JSON元數據生成

#### 2. `simple_2330_test.py` - 簡化版測試
**基礎測試** - 快速驗證功能

```bash
cd scripts/tests/
python simple_2330_test.py
```

#### 3. `test_2330_2025q1.py` - 2025Q1專用測試
**特定期間** - 針對最新季度

```bash
cd scripts/tests/
python test_2330_2025q1.py
```

### 擴展測試到其他公司

```bash
# 測試聯發科(2454)
# 修改 improved_2330_test.py 中的股票代碼:
# '2330' → '2454'
# '台積電' → '聯發科'

# 測試鴻海(2317)  
# 修改 improved_2330_test.py 中的股票代碼:
# '2330' → '2317'
# '台積電' → '鴻海'
```

---

## ✅ 驗證腳本使用指南

### 下載結果驗證

#### 1. `validate_download.py` - 綜合驗證工具

```bash
cd scripts/validation/
python validate_download.py
```

**檢查項目**:
- 📄 PDF檔案存在性
- 📏 檔案大小正確性
- 🔧 JSON結構完整性
- ✅ 元數據準確性

#### 2. `check_pdf_content.py` - PDF內容檢查

```bash
cd scripts/validation/
python check_pdf_content.py
```

**檢查項目**:
- 📖 PDF格式驗證
- 🔍 關鍵字搜尋
- 📄 頁數統計
- 💾 檔案完整性

---

## 📊 數據結構說明

### 檔案命名規則

```
{年度月份}_{股票代碼}_{報告類型}.pdf
例如: 202501_2330_AI1.pdf
     └─年度  └─台積電 └─季報
```

### JSON元數據結構

```json
{
  "stock_code": "2330",
  "company_name": "台積電",
  "report_year": 2025,
  "report_season": "Q1",
  "currency": "TWD",
  "unit": "千元",
  "financials": {
    "cash_and_equivalents": null,    // 現金及約當現金
    "accounts_receivable": null,     // 應收帳款
    "inventory": null,               // 存貨
    "total_assets": null,            // 總資產
    "total_liabilities": null,       // 總負債
    "equity": null                   // 股東權益
  },
  "income_statement": {
    "net_revenue": null,             // 營業收入
    "gross_profit": null,            // 毛利
    "operating_income": null,        // 營業利益
    "net_income": null,              // 本期淨利
    "eps": null                      // 每股盈餘
  },
  "metadata": {
    "source": "doc.twse.com.tw",
    "file_name": "202501_2330_AI1.pdf",
    "file_path": "完整檔案路徑",
    "file_size": 5715493,
    "download_url": "下載連結",
    "crawled_at": "下載時間",
    "validation": {
      "file_exists": true,
      "size_reasonable": true,
      "size_match_expected": true
    }
  }
}
```

---

## 🎯 使用案例

### 案例1: 下載單一公司最新財報

```bash
# 1. 測試台積電2025Q1
cd scripts/tests/
python improved_2330_test.py

# 2. 驗證結果
cd ../validation/
python validate_download.py

# 3. 檢查數據位置
ls ../../data/test_results/
```

### 案例2: 批次下載多公司歷史財報

```bash
# 1. 執行批次爬蟲
cd scripts/crawlers/
python comprehensive_financial_crawler.py

# 2. 檢查下載進度
# (程式會自動顯示進度報告)

# 3. 查看結果
ls ../../data/financial_reports/by_company/
```

### 案例3: 診斷下載問題

```bash
# 1. 使用診斷爬蟲
cd scripts/crawlers/
python diagnostic_batch_crawler.py

# 2. 檢查debug記錄
ls ../../data/debug_logs/

# 3. 查看錯誤報告
# (程式會生成詳細的診斷報告)
```

### 案例4: 新增公司到監控清單

```python
# 修改 comprehensive_financial_crawler.py
companies = [
    {'code': '2330', 'name': '台積電'},
    {'code': '2454', 'name': '聯發科'},
    {'code': '2317', 'name': '鴻海'},
    {'code': '1234', 'name': '新公司'},  # 新增這行
]
```

---

## 🛠️ 工具腳本使用

### PDF解析設定

```bash
cd scripts/tools/
python setup_pdf_parsing.py
```

**功能**:
- 📦 安裝PDF解析庫
- ⚙️ 設定解析環境
- 🧪 測試解析功能

---

## ⚙️ 設定與配置

### 修改爬蟲設定

編輯 `config/settings/settings.py`:

```python
# 下載設定
DOWNLOAD_DELAY = 2          # 下載間隔(秒)
MAX_RETRY = 3              # 最大重試次數
TIMEOUT = 30               # 請求超時時間

# 檔案設定  
OUTPUT_DIR = "data/financial_reports"
BACKUP_ENABLED = True
AUTO_VALIDATION = True

# 目標公司
TARGET_COMPANIES = [
    '2330',  # 台積電
    '2454',  # 聯發科
    '2317',  # 鴻海
]

# 目標期間
TARGET_PERIODS = [
    '2022Q1', '2022Q2', '2022Q3', '2022Q4',
    '2023Q1', '2023Q2', '2023Q3', '2023Q4', 
    '2024Q1', '2024Q2', '2024Q3', '2024Q4',
    '2025Q1'
]
```

---

## 🔍 故障排除

### 常見問題與解決方案

#### 1. 下載失敗
**問題**: PDF下載失敗或檔案損毀  
**解決**:
```bash
# 使用診斷爬蟲檢查
cd scripts/crawlers/
python diagnostic_batch_crawler.py

# 檢查網路連線
ping doc.twse.com.tw

# 重新執行測試
cd ../tests/
python improved_2330_test.py
```

#### 2. 檔案驗證失敗
**問題**: 下載的檔案無法通過驗證  
**解決**:
```bash
# 執行詳細驗證
cd scripts/validation/
python validate_download.py

# 檢查PDF內容
python check_pdf_content.py

# 重新下載
cd ../tests/
python improved_2330_test.py
```

#### 3. 找不到財報
**問題**: 特定期間的財報無法找到  
**解決**:
- 確認財報發布時間（通常在季度結束後1-2個月）
- 檢查股票代碼是否正確
- 確認公司是否有發布該期間財報

#### 4. JSON格式錯誤
**問題**: 生成的JSON檔案格式不正確  
**解決**:
```bash
# 重新生成JSON
cd scripts/tests/
python improved_2330_test.py

# 驗證JSON結構
cd ../validation/
python validate_download.py
```

---

## 📈 數據分析建議

### 1. 數據完整性檢查

```bash
# 檢查所有下載的檔案
find data/financial_reports/ -name "*.pdf" | wc -l

# 檢查JSON檔案
find data/financial_reports/ -name "*.json" | wc -l

# 生成統計報告
cd scripts/crawlers/
python comprehensive_financial_crawler.py --report-only
```

### 2. 數據品質驗證

```bash
# 批次驗證所有檔案
cd scripts/validation/
python validate_download.py --batch-mode

# 檢查檔案大小分布
ls -la data/financial_reports/by_company/*/
```

### 3. 時間序列分析

建議使用下載的JSON數據進行:
- 📊 營收趨勢分析
- 💰 獲利能力比較  
- 📈 成長率計算
- 🔄 季節性分析

---

## 🚀 進階使用

### 1. 自訂爬蟲腳本

基於 `improved_2330_test.py` 建立自訂腳本:

```python
# my_custom_crawler.py
from pathlib import Path
import sys
sys.path.append('scripts/tests')
from improved_2330_test import download_tsmc_2025q1

def download_custom_report(company_code, company_name, year, season):
    # 修改下載邏輯
    pass

if __name__ == '__main__':
    download_custom_report('2454', '聯發科', 2025, 'Q1')
```

### 2. 批次處理腳本

```bash
# 建立批次處理腳本
#!/bin/bash
for company in 2330 2454 2317; do
    cd scripts/tests/
    python improved_2330_test.py --company=$company
    cd ../validation/
    python validate_download.py --company=$company
done
```

### 3. 定期自動更新

設定Windows工作排程器或cron job:

```bash
# 每季度第一個月的15日執行
0 9 15 1,4,7,10 * cd /path/to/FinancialReports && python scripts/crawlers/comprehensive_financial_crawler.py
```

---

## 📞 支援與維護

### 更新爬蟲

```bash
# 檢查TWSE網站變動
cd scripts/tests/
python improved_2330_test.py --debug

# 更新爬蟲邏輯
# (根據debug輸出調整爬蟲參數)
```

### 備份數據

```bash
# 建立完整備份
cp -r data/financial_reports backup/archives/backup_$(date +%Y%m%d)

# 壓縮備份
tar -czf backup_$(date +%Y%m%d).tar.gz data/financial_reports/
```

### 效能監控

```bash
# 檢查磁碟使用量
du -sh data/financial_reports/

# 監控下載速度
time python scripts/tests/improved_2330_test.py
```

---

## 📝 更新記錄

- **v3.2** (2025-06-27): 台積電2025Q1測試成功，改進版下載流程
- **v3.1** (2025-06-27): 專案結構重組，完善驗證機制
- **v3.0** (2025-06-26): 切換到requests-based爬蟲，棄用Selenium
- **v2.x** (2025-06-25): 批次爬蟲完善，支援多公司多期間
- **v1.x** (2025-06-24): 初始版本，基礎爬蟲功能

---

**文件更新時間**: 2025-06-27 01:20  
**適用版本**: v3.2+  
**維護狀態**: 🟢 積極維護中
