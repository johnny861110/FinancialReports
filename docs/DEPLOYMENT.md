# 部署指南

## 🚀 部署選項

### 1. 本地部署

#### 系統需求
- Python 3.8+
- 2GB+ RAM
- 10GB+ 磁碟空間
- 網路連線

#### 安裝步驟

```bash
# 1. 克隆專案
git clone <repository-url>
cd FinancialReports

# 2. 安裝UV (如未安裝)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. 安裝依賴
uv sync

# 4. 建立必要目錄
mkdir -p data/financial_reports data/processed logs

# 5. 設定配置
cp config/crawler_config.json.example config/crawler_config.json
# 編輯配置檔案...

# 6. 測試安裝
uv run python main.py --help
```

### 2. Docker 部署

#### 建立映像

```bash
# 建立Docker映像
docker build -t financial-reports:latest .

# 或使用docker-compose
docker-compose build
```

#### 執行容器

```bash
# 基本執行
docker run -d \
  --name financial-reports \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/config:/app/config \
  financial-reports:latest

# 使用docker-compose
docker-compose up -d
```

#### Docker Compose 配置

建立 `docker-compose.yml`:

```yaml
version: '3.8'

services:
  financial-reports:
    build: .
    container_name: financial-reports
    volumes:
      - ./data:/app/data
      - ./config:/app/config
      - ./logs:/app/logs
    environment:
      - PYTHONPATH=/app
    restart: unless-stopped
    command: ["tail", "-f", "/dev/null"]  # 保持容器運行

  # 可選：資料庫服務
  postgres:
    image: postgres:13
    container_name: financial-db
    environment:
      POSTGRES_DB: financial_reports
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

volumes:
  postgres_data:
```

### 3. 雲端部署

#### AWS 部署

使用 AWS EC2 + ECS:

```bash
# 1. 建立ECR倉庫
aws ecr create-repository --repository-name financial-reports

# 2. 建立並推送映像
docker build -t financial-reports .
docker tag financial-reports:latest <account-id>.dkr.ecr.<region>.amazonaws.com/financial-reports:latest
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/financial-reports:latest

# 3. 建立ECS任務定義
aws ecs register-task-definition --cli-input-json file://task-definition.json
```

#### Google Cloud 部署

使用 Cloud Run:

```bash
# 1. 建立映像並推送到GCR
gcloud builds submit --tag gcr.io/PROJECT-ID/financial-reports

# 2. 部署到Cloud Run
gcloud run deploy financial-reports \
  --image gcr.io/PROJECT-ID/financial-reports \
  --platform managed \
  --region asia-east1 \
  --allow-unauthenticated
```

## ⚙️ 環境配置

### 1. 環境變數

建立 `.env` 檔案:

```bash
# 應用設定
APP_ENV=production
LOG_LEVEL=INFO
DATA_DIR=/app/data
CONFIG_DIR=/app/config

# 資料庫設定 (可選)
DATABASE_URL=postgresql://user:password@localhost:5432/financial_reports

# OCR設定
OCR_ENGINE=easyocr
USE_GPU=false

# 爬蟲設定
DOWNLOAD_DELAY=2
MAX_RETRY=3
TIMEOUT=30
```

### 2. 配置檔案

#### `config/crawler_config.json`
```json
{
  "base_url": "https://doc.twse.com.tw",
  "output_dir": "data/financial_reports",
  "download_delay": 2,
  "max_retry": 3,
  "timeout": 30,
  "user_agent": "Mozilla/5.0 (compatible; FinancialReportsCrawler/2.0)",
  "headers": {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8"
  }
}
```

#### `config/processor_config.json`
```json
{
  "ocr_engine": "easyocr",
  "languages": ["ch_tra", "en"],
  "use_gpu": false,
  "confidence_threshold": 0.7,
  "text_threshold": 0.3,
  "batch_size": 10
}
```

## 📊 監控與日誌

### 1. 日誌配置

建立 `config/logging.json`:

```json
{
  "version": 1,
  "formatters": {
    "default": {
      "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    }
  },
  "handlers": {
    "console": {
      "class": "logging.StreamHandler",
      "formatter": "default"
    },
    "file": {
      "class": "logging.FileHandler",
      "filename": "logs/app.log",
      "formatter": "default"
    }
  },
  "root": {
    "level": "INFO",
    "handlers": ["console", "file"]
  }
}
```

### 2. 健康檢查

建立健康檢查端點 (`health_check.py`):

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import sys
from pathlib import Path
from datetime import datetime

def health_check():
    """系統健康檢查"""
    status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "checks": {}
    }
    
    # 檢查目錄是否存在
    required_dirs = ["data", "config", "logs"]
    for dir_name in required_dirs:
        if Path(dir_name).exists():
            status["checks"][f"{dir_name}_dir"] = "ok"
        else:
            status["checks"][f"{dir_name}_dir"] = "missing"
            status["status"] = "unhealthy"
    
    # 檢查配置檔案
    config_file = Path("config/crawler_config.json")
    if config_file.exists():
        status["checks"]["config"] = "ok"
    else:
        status["checks"]["config"] = "missing"
        status["status"] = "unhealthy"
    
    return status

if __name__ == "__main__":
    result = health_check()
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["status"] == "healthy" else 1)
```

### 3. 系統監控

使用 Prometheus + Grafana 進行監控:

建立 `monitoring/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'financial-reports'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: /metrics
    scrape_interval: 30s
```

## 🔒 安全性配置

### 1. 檔案權限

```bash
# 設定正確的檔案權限
chmod 600 config/*.json
chmod 700 logs/
chmod 755 scripts/*.py
```

### 2. 防火牆設定

```bash
# Ubuntu/Debian
ufw allow 22/tcp
ufw allow 8000/tcp
ufw enable

# CentOS/RHEL
firewall-cmd --permanent --add-port=22/tcp
firewall-cmd --permanent --add-port=8000/tcp
firewall-cmd --reload
```

### 3. SSL/TLS 配置

如需要HTTPS，使用nginx反向代理:

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /path/to/certificate.crt;
    ssl_certificate_key /path/to/private.key;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 🔧 維護任務

### 1. 定期備份

建立備份腳本 (`scripts/backup.sh`):

```bash
#!/bin/bash

BACKUP_DIR="/backup/financial-reports"
DATE=$(date +%Y%m%d_%H%M%S)

# 建立備份目錄
mkdir -p $BACKUP_DIR

# 備份資料
tar -czf $BACKUP_DIR/data_$DATE.tar.gz data/
tar -czf $BACKUP_DIR/config_$DATE.tar.gz config/

# 保留最近30天的備份
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "備份完成: $DATE"
```

### 2. 日誌輪轉

設定logrotate (`/etc/logrotate.d/financial-reports`):

```
/app/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    copytruncate
}
```

### 3. 系統更新

建立更新腳本 (`scripts/update.sh`):

```bash
#!/bin/bash

echo "開始更新系統..."

# 停止服務
docker-compose down

# 拉取最新代碼
git pull origin main

# 重建映像
docker-compose build

# 重啟服務
docker-compose up -d

echo "更新完成"
```

## 🚨 故障排除

### 1. 常見問題

#### 記憶體不足
```bash
# 檢查記憶體使用量
free -h
docker stats

# 增加swap空間
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

#### 磁碟空間不足
```bash
# 清理Docker
docker system prune -a

# 清理舊日誌
find logs/ -name "*.log" -mtime +7 -delete

# 清理處理過的檔案
find data/processed/ -mtime +30 -delete
```

### 2. 除錯模式

啟用除錯模式:

```bash
# 設定環境變數
export LOG_LEVEL=DEBUG
export APP_ENV=development

# 執行應用
uv run python main.py --debug
```

### 3. 效能調優

調整處理參數:

```json
{
  "batch_size": 5,
  "max_workers": 2,
  "memory_limit": "1GB",
  "timeout": 60
}
```

---

**需要協助？請查看 [開發指南](DEVELOPMENT.md) 或聯繫系統管理員。**
