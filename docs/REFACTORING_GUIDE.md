# 📚 重構架構文檔 - 財務報告處理工具 v2.0

## 🎯 重構目標

將專案從單體架構重構為模組化、可維護的現代架構：

- ✅ **模組化設計** - 清晰的職責分離
- ✅ **依賴注入** - 降低模組間耦合
- ✅ **統一配置** - 集中管理所有設定
- ✅ **錯誤處理** - 標準化異常處理機制
- ✅ **向後相容** - 保持現有功能完整性

## 🏗️ 新架構概覽

```
src/
├── core/                    # 核心模組
│   ├── __init__.py         # 基礎類別和介面
│   ├── config.py           # 配置管理和依賴注入
│   └── exceptions.py       # 統一異常處理
├── processors/             # 處理器模組
│   ├── pdf_processor.py      # 重構後的PDF處理器
│   └── smart_processor.py    # 智慧財務處理器
├── app_factory.py          # 應用程式工廠
└── __init__.py            # 套件入口
```

## 📦 核心組件詳解

### 1. 配置管理系統 (`src/core/config.py`)

#### 特點
- **統一配置** - 所有設定集中管理
- **依賴注入** - 服務註冊和獲取機制
- **類型安全** - 使用 dataclass 確保類型正確性

#### 使用方式
```python
from src.core.config import get_config, register_service, get_service

# 獲取配置
config = get_config()
print(f"PDF引擎: {config.processing.pdf_engine}")

# 註冊服務
register_service('my_service', MyService())

# 獲取服務
service = get_service('my_service')
```

### 2. 異常處理系統 (`src/core/exceptions.py`)

#### 特點
- **標準化錯誤** - 統一的錯誤格式和代碼
- **上下文資訊** - 豐富的錯誤上下文
- **自動日誌** - 錯誤自動記錄到日誌

#### 使用方式
```python
from src.core.exceptions import handle_errors, PDFProcessingError, ErrorCode

@handle_errors
def process_file(file_path):
    if not file_path.exists():
        raise PDFProcessingError(
            ErrorCode.FILE_NOT_FOUND,
            f"檔案不存在: {file_path}",
            str(file_path)
        )
```

### 3. 基礎類別和介面 (`src/core/__init__.py`)

#### 特點
- **協議介面** - 使用 Protocol 定義契約
- **基礎類別** - 提供通用功能
- **類型檢查** - 支援靜態類型檢查

#### 使用方式
```python
from src.core import BaseProcessor, FinancialReport

class MyProcessor(BaseProcessor):
    def process(self, input_path, output_path=None):
        # 實現處理邏輯
        pass

# 創建財報
report = FinancialReport("2330", "台積電", 2024, "Q1")
report.add_financial_data("financials", {"revenue": 1000000})
```

## 🔧 處理器架構

### PDF處理器重構 (`src/processors/pdf_processor.py`)

#### 模組化設計
```python
class PDFTextExtractor:      # 文字提取
class PDFTableExtractor:     # 表格提取  
class PDFFinancialExtractor: # 財務數據提取
class ModernPDFProcessor:    # 主處理器
```

#### 使用方式
```python
from src.app_factory import get_processor

pdf_processor = get_processor('pdf')
result = pdf_processor.process(pdf_path, output_path)
```

## 🚀 應用程式工廠 (`src/app_factory.py`)

### 功能
- **自動設置** - 一鍵初始化整個應用程式
- **服務註冊** - 自動註冊所有核心服務
- **便利函數** - 提供快速存取方法

### 使用方式
```python
from src.app_factory import setup_application, get_processor, create_financial_report

# 初始化應用程式
config = setup_application()

# 獲取處理器
pdf_processor = get_processor('pdf')
smart_processor = get_processor('smart')

# 創建財報
report = create_financial_report("2330", "台積電", 2024, "Q1")
```

## 📋 使用指南

### 1. 基本設置

```python
from src.app_factory import setup_application

# 使用預設配置
config = setup_application()

# 使用自訂配置
config = setup_application(Path("my_config.json"))
```

### 2. 處理單個PDF

```python
from src.app_factory import get_processor

pdf_processor = get_processor('pdf')
result = pdf_processor.process(
    input_path=Path("report.pdf"),
    output_path=Path("output.json")
)
```

### 3. 處理完整財務報告

```python
from src.app_factory import get_processor, create_financial_report

# 創建財報
report = create_financial_report("2330", "台積電", 2024, "Q1")

# 獲取智慧處理器
smart_processor = get_processor('smart')

# 處理報告
result = smart_processor.process_report(
    pdf_path=Path("report.pdf"),
    financial_report=report,
    output_dir=Path("output/")
)
```

### 4. 批次處理

```python
from pathlib import Path
from src.app_factory import get_processor

pdf_processor = get_processor('pdf')

for pdf_file in Path("pdfs/").glob("*.pdf"):
    try:
        result = pdf_processor.process(pdf_file)
        print(f"✅ {pdf_file.name} 處理完成")
    except Exception as e:
        print(f"❌ {pdf_file.name} 處理失敗: {e}")
```

## 🔄 遷移指南

### 從舊架構遷移

#### 舊方式
```python
from src.processors.pdf_processor import PDFProcessor

processor = PDFProcessor(config_dict)
result = processor.process(input_path)
```

#### 新方式
```python
from src.app_factory import setup_application, get_processor

setup_application()
processor = get_processor('pdf')
result = processor.process(input_path)
```

### 相容性說明

- ✅ **向後相容** - 舊的處理器仍可使用
- ✅ **逐步遷移** - 可以混用新舊架構
- ✅ **配置相容** - 現有配置檔案仍有效

## 🧪 測試和驗證

### 執行架構測試
```bash
python test_architecture.py --test
```

### 使用主程式
```bash
# 顯示系統資訊
python main.py --info

# 處理單個PDF
python main.py --pdf file.pdf

# 財務報告處理
python main.py --financial --pdf file.pdf --stock 2330 --company "台積電" --year 2024 --season Q1

# 批次處理
python main.py --batch pdf_directory/
```

## 🔍 故障排除

### 常見問題

1. **導入錯誤**
   ```python
   # 確保正確導入
   from src.app_factory import setup_application
   
   # 初始化應用程式
   setup_application()
   ```

2. **服務未找到**
   ```python
   # 確保已初始化
   setup_application()
   
   # 再獲取服務
   processor = get_processor('pdf')
   ```

3. **配置錯誤**
   ```python
   # 檢查配置
   from src.core import get_config
   config = get_config()
   print(config.processing.pdf_engine)
   ```

## 📈 效益總結

### 開發效益
- 🔧 **可維護性** - 模組化設計，易於修改和擴展
- 🧪 **可測試性** - 依賴注入，便於單元測試
- 📚 **可讀性** - 清晰的架構和文檔

### 運行效益
- ⚡ **性能** - 優化的處理流程
- 🛡️ **穩定性** - 統一的錯誤處理
- 🔄 **相容性** - 平滑的遷移路徑

---

**更新時間**: 2025年7月7日  
**版本**: 2.0.0  
**狀態**: ✅ 重構完成，可投入使用
