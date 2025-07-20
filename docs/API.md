# API 文檔

## 核心API參考

### 1. 財報爬蟲 API

#### FinancialCrawler 類別

```python
from src.core.crawler import FinancialCrawler

crawler = FinancialCrawler(config)
result = crawler.process(query_data, output_path)
```

**參數:**
- `query_data`: 查詢資料字典或列表
- `output_path`: 可選的輸出路徑

**查詢資料格式:**
```json
{
  "stock_code": "2330",
  "company_name": "台積電", 
  "year": 2024,
  "season": "Q1",
  "test_mode": false
}
```

#### 方法

##### `download_report(stock_code, company_name, year, season)`
下載單一財報

**返回:** `ProcessingResult` 物件

##### `batch_download(queries)`
批次下載財報

**參數:**
- `queries`: 查詢資料列表

### 2. PDF處理器 API

#### SmartProcessor 類別

```python
from src.processors.smart_processor import SmartProcessor

processor = SmartProcessor(config)
result = processor.process(pdf_path, json_path)
```

**方法:**

##### `analyze_pdf_type(pdf_path)`
分析PDF類型

**返回:**
```json
{
  "type": "text_based|scanned|mixed",
  "text_ratio": 0.95,
  "total_pages": 10,
  "confidence": "high|medium|low"
}
```

##### `process_pdf_intelligently(pdf_path, json_path)`
智慧處理PDF

**返回:** 增強的JSON資料

### 3. 工具函數 API

#### helpers.py

```python
from src.utils.helpers import (
    setup_logging, validate_stock_code, 
    validate_season, load_json, save_json
)
```

**可用函數:**
- `setup_logging(name)`: 設置日誌
- `validate_stock_code(code)`: 驗證股票代碼  
- `validate_season(season)`: 驗證季度
- `load_json(path)`: 載入JSON檔案
- `save_json(data, path)`: 儲存JSON檔案
- `create_progress_reporter()`: 建立進度報告器

### 4. 設定管理 API

#### ConfigManager 類別

```python
from src.core import ConfigManager

config = ConfigManager.load_config("config/settings.json")
```

**設定項目:**
- `download_delay`: 下載延遲（秒）
- `max_retry`: 最大重試次數
- `timeout`: 超時時間
- `output_dir`: 輸出目錄
- `ocr_engine`: OCR引擎選擇

### 5. 資料模型 API

#### FinancialReport 類別

```python
from src.core import FinancialReport

report = FinancialReport("2330", "台積電", 2024, "Q1")
```

**屬性:**
- `stock_code`: 股票代碼
- `company_name`: 公司名稱
- `year`: 年份
- `season`: 季度
- `data`: 財報資料

#### ProcessingResult 類別

```python
from src.core import ProcessingResult

result = ProcessingResult(success=True, message="處理完成", data=data)
```

**屬性:**
- `success`: 處理是否成功
- `message`: 處理訊息
- `data`: 處理結果資料
- `metadata`: 元資料

## 使用範例

### 基本使用

```python
# 下載財報
from src.core.crawler import FinancialCrawler

crawler = FinancialCrawler()
result = crawler.process({
    "stock_code": "2330",
    "company_name": "台積電",
    "year": 2024,
    "season": "Q1"
})

if result.success:
    print(f"下載成功: {result.data['pdf_path']}")
```

### 智慧處理

```python
# 處理PDF
from src.processors.smart_processor import SmartProcessor

processor = SmartProcessor()
result = processor.process("report.pdf", "report.json")

print(f"處理類型: {result.metadata['pdf_type']}")
print(f"置信度: {result.metadata['confidence']}")
```

### 批次處理

```python
# 批次處理
queries = [
    {"stock_code": "2330", "company_name": "台積電", "year": 2024, "season": "Q1"},
    {"stock_code": "2454", "company_name": "聯發科", "year": 2024, "season": "Q1"}
]

crawler = FinancialCrawler()
results = crawler.process(queries)

for result in results:
    if result.success:
        print(f"✓ {result.data['company_name']} 處理成功")
    else:
        print(f"✗ {result.data['company_name']} 處理失敗: {result.message}")
```

## 錯誤處理

所有API都會返回標準的 `ProcessingResult` 物件，包含:
- 成功/失敗狀態
- 錯誤訊息
- 處理結果資料
- 元資料（如處理時間、檔案大小等）

```python
result = processor.process(pdf_path, json_path)

if not result.success:
    print(f"處理失敗: {result.message}")
    # 處理錯誤...
else:
    # 處理成功，使用result.data
    pass
```

## 配置參數

### 爬蟲配置 (crawler_config.json)
```json
{
  "base_url": "https://doc.twse.com.tw",
  "download_delay": 2,
  "max_retry": 3,
  "timeout": 30,
  "user_agent": "Mozilla/5.0...",
  "output_dir": "data/financial_reports"
}
```

### 處理器配置
```json
{
  "ocr_engine": "easyocr",
  "use_gpu": true,
  "languages": ["ch_tra", "en"],
  "confidence_threshold": 0.7,
  "text_threshold": 0.3
}
```
