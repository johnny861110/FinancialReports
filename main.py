#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
財務報告處理工具主程式
現代化架構的統一入口點
"""

import argparse
from pathlib import Path
from typing import Optional
import logging

from src.app_factory import setup_application, get_processor, create_financial_report
from src.core import get_config, handle_errors, FinancialReportsException


@handle_errors
def process_pdf_file(pdf_path: Path, output_path: Optional[Path] = None) -> dict:
    """處理單個PDF檔案"""
    
    # 獲取PDF處理器
    pdf_processor = get_processor('pdf')
    
    # 處理PDF
    logging.info(f"開始處理PDF: {pdf_path}")
    result = pdf_processor.process(pdf_path, output_path)
    
    return result


@handle_errors
def process_financial_report(pdf_path: Path, stock_code: str, 
                           company_name: str, year: int, season: str,
                           output_dir: Optional[Path] = None) -> dict:
    """處理完整的財務報告"""
    
    # 獲取智慧處理器
    smart_processor = get_processor('smart')
    
    # 創建財報實例
    report = create_financial_report(stock_code, company_name, year, season)
    
    # 處理財報
    logging.info(f"開始處理財務報告: {company_name} ({stock_code}) {year}年{season}")
    
    # 確保有輸出目錄
    if output_dir is None:
        output_dir = Path("data/financial_reports")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成輸出路徑 - 使用季度編號格式: YYYY + 季度編號(01-04)
    season_num = season.replace('Q', '').zfill(2)
    json_path = output_dir / f"{year}{season_num}_{stock_code}_AI1.json"
    
    # 輸出到processed目錄，使用標準命名格式
    processed_dir = output_dir / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    output_file = processed_dir / f"{year}{season_num}_{stock_code}_AI1_enhanced.json"
    
    # 使用 process 方法處理
    result = smart_processor.process(pdf_path, json_path, output_file)
    
    return result


@handle_errors
def batch_process_pdfs(pdf_dir: Path, output_dir: Optional[Path] = None) -> list:
    """批次處理PDF檔案"""
    
    if not pdf_dir.is_dir():
        raise ValueError(f"輸入路徑不是目錄: {pdf_dir}")
    
    pdf_files = list(pdf_dir.glob("*.pdf"))
    if not pdf_files:
        logging.warning(f"在 {pdf_dir} 中找不到PDF檔案")
        return []
    
    results = []
    pdf_processor = get_processor('pdf')
    
    for pdf_file in pdf_files:
        try:
            output_path = None
            if output_dir:
                output_path = output_dir / f"{pdf_file.stem}_processed.json"
            
            result = pdf_processor.process(pdf_file, output_path)
            results.append({
                'file': str(pdf_file),
                'success': True,
                'result': result
            })
            
            logging.info(f"✅ 處理完成: {pdf_file.name}")
            
        except Exception as e:
            logging.error(f"❌ 處理失敗: {pdf_file.name} - {e}")
            results.append({
                'file': str(pdf_file),
                'success': False,
                'error': str(e)
            })
    
    return results


def show_system_info():
    """顯示系統資訊"""
    config = get_config()
    
    print("\n" + "="*60)
    print("📊 財務報告處理工具 v2.0")
    print("="*60)
    
    print(f"📁 工作目錄: {config.paths.base_dir}")
    print(f"📊 數據目錄: {config.paths.absolute_data_dir}")
    print(f"📤 輸出目錄: {config.paths.absolute_output_dir}")
    print(f"🔧 PDF引擎: {config.processing.pdf_engine}")
    print(f"👁️ OCR引擎: {config.processing.ocr_engine}")
    print(f"🎯 自動驗證: {'啟用' if config.auto_validation else '停用'}")
    print(f"📝 日誌等級: {config.log_level}")
    
    print("\n🛠️ 可用處理器:")
    try:
        pdf_processor = get_processor('pdf')
        print("   ✅ PDF處理器 (pdfplumber)")
    except:
        print("   ❌ PDF處理器")
    
    try:
        smart_processor = get_processor('smart')
        print("   ✅ 智慧財務處理器")
    except:
        print("   ❌ 智慧財務處理器")
    
    print("="*60)


def main():
    """主函數"""
    parser = argparse.ArgumentParser(
        description="財務報告處理工具 v2.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用範例:
  # 顯示系統資訊
  python main.py --info
  
  # 處理單個PDF
  python main.py --pdf path/to/file.pdf
  
  # 處理完整財務報告
  python main.py --financial --pdf path/to/file.pdf --stock 2330 --company "台積電" --year 2024 --season Q1
  
  # 批次處理
  python main.py --batch path/to/pdf/directory
        """
    )
    
    # 基本選項
    parser.add_argument('--config', type=Path, help='配置檔案路徑')
    parser.add_argument('--info', action='store_true', help='顯示系統資訊')
    parser.add_argument('--output', type=Path, help='輸出目錄')
    
    # 處理模式
    parser.add_argument('--pdf', type=Path, help='處理單個PDF檔案')
    parser.add_argument('--batch', type=Path, help='批次處理PDF目錄')
    parser.add_argument('--financial', action='store_true', help='財務報告處理模式')
    
    # 財務報告參數
    parser.add_argument('--stock', help='股票代碼')
    parser.add_argument('--company', help='公司名稱')
    parser.add_argument('--year', type=int, help='年份')
    parser.add_argument('--season', help='季度 (Q1, Q2, Q3, Q4)')
    
    args = parser.parse_args()
    
    try:
        # 初始化應用程式
        config = setup_application(args.config)
        
        # 顯示系統資訊
        if args.info:
            show_system_info()
            return
        
        # 處理模式
        if args.pdf:
            if args.financial:
                # 財務報告處理模式
                if not all([args.stock, args.company, args.year, args.season]):
                    print("❌ 財務報告處理模式需要指定 --stock, --company, --year, --season")
                    return
                
                result = process_financial_report(
                    args.pdf, args.stock, args.company, 
                    args.year, args.season, args.output
                )
                print(f"✅ 財務報告處理完成")
                
            else:
                # 單純PDF處理
                output_path = None
                if args.output:
                    output_path = args.output / f"{args.pdf.stem}_processed.json"
                
                result = process_pdf_file(args.pdf, output_path)
                print(f"✅ PDF處理完成")
        
        elif args.batch:
            # 批次處理
            results = batch_process_pdfs(args.batch, args.output)
            
            success_count = sum(1 for r in results if r['success'])
            total_count = len(results)
            
            print(f"\n📊 批次處理完成: {success_count}/{total_count} 成功")
            
            if success_count < total_count:
                print("\n❌ 處理失敗的檔案:")
                for result in results:
                    if not result['success']:
                        print(f"   - {Path(result['file']).name}: {result['error']}")
        
        else:
            # 沒有指定處理模式，顯示幫助
            show_system_info()
            print("\n請使用 --help 查看使用說明")
    
    except FinancialReportsException as e:
        print(f"❌ 應用程式錯誤 [{e.code.value}]: {e}")
        if e.context:
            print(f"   詳情: {e.context}")
    
    except Exception as e:
        print(f"❌ 未知錯誤: {e}")
        logging.exception("未捕獲的異常")


if __name__ == '__main__':
    main()
