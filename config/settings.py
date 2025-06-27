# Configuration settings for the Financial Report Scraper

import os

# Path to ChromeDriver executable
CHROMEDRIVER_PATH = "C:/chromedriver/chromedriver.exe"

# Base URL for the Taiwan Stock Exchange financial reports
BASE_URL = "https://doc.twse.com.tw/server-java/t57sb01"

# Directory to save downloaded reports
REPORTS_DIR = os.path.abspath("./reports/")

# Log file path
LOG_FILE = os.path.abspath("../logs/scraper.log")

# 注意：此專案已切換為 requests-based 架構，不再使用 Selenium
# 以下配置為歷史遺留，可以刪除
# SELENIUM_OPTIONS = {
#     "headless": True,
#     "disable_gpu": True,
#     "no_sandbox": True
# }
