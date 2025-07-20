# 開發指南

## 🛠️ 開發環境設定

### 前置條件
- Python 3.8+
- UV套件管理器
- Git

### 1. 安裝UV套件管理器

```bash
# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. 克隆專案

```bash
git clone <repository-url>
cd FinancialReports
```

### 3. 設定開發環境

```bash
# 安裝依賴
uv sync

# 啟動虛擬環境
uv shell

# 或直接執行
uv run python main.py --help
```

## 📁 專案結構說明

### 核心模組 (`src/`)

```
src/
├── core/           # 核心功能
├── processors/     # 處理器
└── utils/          # 工具函數
```

#### `src/core/`
- `__init__.py`: 基礎類別與資料模型
- `crawler.py`: 財報爬蟲實作

#### `src/processors/`
- `pdf_processor.py`: PDF處理器
- `smart_processor.py`: 智慧處理器

#### `src/utils/`
- `helpers.py`: 輔助函數與工具

### 執行腳本 (`scripts/`)

獨立的執行腳本，可直接運行：
- `financial_crawler.py`: 爬蟲腳本
- `smart_processor.py`: 處理腳本

### 測試 (`tests/`)

```
tests/
├── test_all.py      # 主測試套件
├── test_crawler.py  # 爬蟲測試
├── test_processor.py # 處理器測試
└── fixtures/        # 測試資料
```

## 🔧 開發工作流程

### 1. 新增功能

1. 在對應模組中實作功能
2. 撰寫測試案例
3. 執行測試確保通過
4. 更新文檔

### 2. 測試

```bash
# 執行所有測試
uv run python -m pytest tests/

# 執行特定測試
uv run python -m pytest tests/test_crawler.py

# 執行測試並顯示覆蓋率
uv run python -m pytest tests/ --cov=src/
```

### 3. 程式碼品質

```bash
# 格式化程式碼
uv run black src/ scripts/ tests/

# 檢查程式碼風格
uv run flake8 src/ scripts/ tests/

# 類型檢查（可選）
uv run mypy src/
```

## 📚 程式碼指引

### 1. 編程風格

- 遵循 PEP 8 規範
- 使用 Black 進行程式碼格式化
- 函數和類別需要 docstring
- 使用 type hints

### 2. 命名規範

```python
# 類別名稱: PascalCase
class FinancialCrawler:
    pass

# 函數名稱: snake_case
def download_report():
    pass

# 常數: UPPER_CASE
MAX_RETRY_COUNT = 3

# 變數: snake_case
stock_code = "2330"
```

### 3. 錯誤處理

```python
# 使用統一的錯誤處理模式
try:
    result = process_data(data)
    return ProcessingResult(True, "處理成功", result)
except ValueError as e:
    logger.error(f"資料格式錯誤: {e}")
    return ProcessingResult(False, f"資料格式錯誤: {e}")
except Exception as e:
    logger.error(f"未預期錯誤: {e}")
    return ProcessingResult(False, f"處理失敗: {e}")
```

### 4. 日誌記錄

```python
from src.utils.helpers import setup_logging

class MyClass:
    def __init__(self):
        self.logger = setup_logging(self.__class__.__name__)
    
    def process(self):
        self.logger.info("開始處理")
        try:
            # 處理邏輯
            self.logger.info("處理完成")
        except Exception as e:
            self.logger.error(f"處理失敗: {e}")
```

## 🧪 測試指引

### 1. 測試結構

```python
import pytest
from src.core.crawler import FinancialCrawler

class TestFinancialCrawler:
    def setup_method(self):
        """每個測試前的設置"""
        self.crawler = FinancialCrawler()
    
    def test_download_success(self):
        """測試成功下載"""
        result = self.crawler.download_report("2330", "台積電", 2024, "Q1")
        assert result.success
    
    def test_invalid_stock_code(self):
        """測試無效股票代碼"""
        result = self.crawler.download_report("INVALID", "公司", 2024, "Q1")
        assert not result.success
```

### 2. 測試資料

將測試資料放在 `tests/fixtures/` 目錄：

```
tests/fixtures/
├── sample_report.pdf
├── sample_data.json
└── test_config.json
```

### 3. Mock和假資料

```python
from unittest.mock import patch, MagicMock

@patch('requests.get')
def test_download_with_mock(self, mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"fake pdf content"
    mock_get.return_value = mock_response
    
    result = self.crawler.download_report("2330", "台積電", 2024, "Q1")
    assert result.success
```

## 🚀 部署指引

### 1. 本地部署

```bash
# 建立生產環境
uv sync --no-dev

# 執行應用
uv run python main.py crawl --stock-code 2330 --company "台積電" --year 2024 --season Q1
```

### 2. Docker部署

```bash
# 建立映像
docker build -t financial-reports .

# 執行容器
docker run -v $(pwd)/data:/app/data financial-reports
```

### 3. 設定檔案

確保設定檔案存在：
- `config/crawler_config.json`
- `config/settings.py`
- `config/xbrl_tags.json`

## 🐛 除錯技巧

### 1. 開啟詳細日誌

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 2. 使用除錯器

```python
import pdb
pdb.set_trace()  # 在需要的地方設置斷點
```

### 3. 檢查資料流

```python
# 在處理過程中輸出中間結果
print(f"處理狀態: {result}")
print(f"資料大小: {len(data)}")
```

## 📦 發布流程

### 1. 版本更新

更新 `pyproject.toml` 中的版本號：

```toml
[project]
version = "2.1.0"
```

### 2. 建立標籤

```bash
git tag v2.1.0
git push origin v2.1.0
```

### 3. 建立發布

使用 GitHub Releases 或其他平台建立正式發布。

## 🤝 貢獻指引

### 1. 分支策略

- `main`: 主分支，穩定版本
- `develop`: 開發分支
- `feature/*`: 功能分支
- `hotfix/*`: 緊急修復分支

### 2. Pull Request 流程

1. Fork 專案
2. 建立功能分支
3. 實作功能並撰寫測試
4. 提交 Pull Request
5. 代碼審查
6. 合併至主分支

### 3. 代碼審查清單

- [ ] 程式碼符合風格指引
- [ ] 所有測試通過
- [ ] 新功能有對應測試
- [ ] 文檔已更新
- [ ] 無安全漏洞

## 🔍 常見問題

### Q: 如何新增新的處理器？

A: 
1. 在 `src/processors/` 建立新檔案
2. 繼承 `BaseProcessor` 類別
3. 實作 `process` 方法
4. 新增對應測試

### Q: 如何修改設定？

A: 編輯 `config/` 目錄下的設定檔案，或在程式中傳入設定字典。

### Q: 測試失敗怎麼辦？

A: 
1. 檢查錯誤訊息
2. 確認測試環境設定正確
3. 檢查測試資料是否存在
4. 使用除錯器進行詳細分析

---

**需要協助？請查看 [API文檔](API.md) 或提交 Issue。**
