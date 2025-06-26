# 🚀 財報爬蟲 - 快速開始指南

## 30秒快速測試

### 1️⃣ 下載台積電2025Q1財報
```bash
cd scripts/tests/
python improved_2330_test.py
```

### 2️⃣ 驗證下載結果
```bash
cd ../validation/
python validate_download.py
```

### 3️⃣ 檢查檔案
```bash
ls ../../data/test_results/
# 應該看到: 202501_2330_AI1.pdf 和 202501_2330_AI1.json
```

---

## 📊 批次下載多家公司

### 執行批次爬蟲
```bash
cd scripts/crawlers/
python comprehensive_financial_crawler.py
```

---

## 🎯 修改目標公司

編輯測試腳本來下載其他公司:

### 下載聯發科(2454)
編輯 `scripts/tests/improved_2330_test.py`：
```python
# 修改第25-26行:
'co_id': '2454',           # 改為2454
'company_name': '聯發科',   # 改為聯發科
```

### 下載鴻海(2317) 
編輯 `scripts/tests/improved_2330_test.py`：
```python
# 修改第25-26行:
'co_id': '2317',           # 改為2317  
'company_name': '鴻海',     # 改為鴻海
```

---

## 📁 重要檔案位置

| 類型 | 位置 | 說明 |
|------|------|------|
| 測試結果 | `data/test_results/` | 下載的PDF和JSON檔案 |
| 主要數據 | `data/financial_reports/` | 批次下載的財報數據 |
| 使用指南 | `docs/guides/` | 詳細說明文件 |
| 測試報告 | `docs/reports/` | 各種測試和狀態報告 |

---

## 🔧 主要腳本功能

| 腳本檔案 | 功能說明 | 適用對象 |
|----------|----------|----------|
| `improved_2330_test.py` | 單一公司測試下載 | 新手用戶 ⭐ |
| `comprehensive_financial_crawler.py` | 批次多公司下載 | 進階用戶 |
| `validate_download.py` | 下載結果驗證 | 所有用戶 ⭐ |
| `diagnostic_batch_crawler.py` | 診斷問題排除 | 開發者 |

---

## 🎯 使用流程建議

### 新手用戶 (第一次使用)
1. 執行 `improved_2330_test.py` 測試單一下載
2. 用 `validate_download.py` 驗證結果
3. 查看 `data/test_results/` 中的檔案
4. 閱讀 `docs/guides/HOW_TO_CRAWL.md` 了解更多

### 進階用戶 (批次下載)
1. 執行 `comprehensive_financial_crawler.py` 批次下載
2. 檢查 `data/financial_reports/` 中的結果
3. 使用 `diagnostic_batch_crawler.py` 診斷問題
4. 查看 `docs/reports/` 中的報告

---

## ❓ 常見問題

### Q: 下載失敗怎麼辦？
**A:** 
1. 檢查網路連線是否正常
2. 確認 TWSE 網站可正常存取
3. 重新執行測試腳本
4. 使用 `diagnostic_batch_crawler.py` 診斷

### Q: 檔案下載不完整？
**A:**
1. 執行 `validate_download.py` 檢查
2. 查看檔案大小是否合理
3. 檢查 PDF 是否可正常開啟
4. 重新下載該檔案

### Q: 如何下載其他公司財報？
**A:**
1. 修改 `improved_2330_test.py` 中的股票代碼
2. 更改公司名稱
3. 重新執行測試腳本
4. 驗證下載結果

### Q: 如何下載歷史財報？
**A:**
1. 使用 `comprehensive_financial_crawler.py`
2. 修改目標期間設定
3. 執行批次下載
4. 檢查結果完整性

---

## 🎉 成功案例

### ✅ 已驗證功能
- 台積電(2330) 2025Q1財報下載成功
- PDF檔案大小: 5,715,493 bytes
- JSON元數據自動生成
- 6/6項驗證測試通過

### 📊 支援的公司與期間
- **公司**: 台積電(2330)、聯發科(2454)、鴻海(2317)
- **期間**: 2022Q1 - 2025Q1
- **格式**: PDF財報 + JSON結構化數據

---

## 📖 更多資源

- **完整使用說明**: `docs/guides/HOW_TO_CRAWL.md`
- **專案結構說明**: `PROJECT_STRUCTURE.md`
- **測試報告**: `docs/reports/TEST_REPORT_2330_2025Q1.md`
- **專案狀態**: `docs/reports/PROJECT_STATUS.md`

---

## 🚀 立即開始

**推薦第一次使用者：**

```bash
# 1. 測試下載台積電財報
cd scripts/tests/
python improved_2330_test.py

# 2. 驗證下載結果  
cd ../validation/
python validate_download.py

# 3. 查看結果
explorer ../../data/test_results/
```

**成功後會看到：**
- `202501_2330_AI1.pdf` - 台積電2025Q1財報PDF
- `202501_2330_AI1.json` - 對應的JSON元數據檔案

---

**最後更新**: 2025-06-27 01:30  
**版本**: v3.2  
**狀態**: ✅ 可立即使用
