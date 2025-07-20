#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
數據驗證器 - 確保財報數據品質
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
from dataclasses import dataclass

from ..core import ProcessingResult


@dataclass
class ValidationRule:
    """驗證規則"""
    field_name: str
    rule_type: str  # required, type, range, format, custom
    parameters: Dict[str, Any]
    error_message: str
    severity: str = "error"  # error, warning, info


@dataclass
class ValidationResult:
    """驗證結果"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    info: List[str]
    score: float  # 0-100 品質分數
    suggestions: List[str]


class FinancialDataValidator:
    """財務數據驗證器"""
    
    def __init__(self):
        self.validation_rules = self._setup_validation_rules()
        self.required_financial_fields = [
            'net_revenue', 'gross_profit', 'operating_income', 
            'net_income', 'total_assets', 'total_liabilities', 'equity'
        ]
        
    def _setup_validation_rules(self) -> List[ValidationRule]:
        """設置驗證規則"""
        return [
            # 基本欄位驗證
            ValidationRule(
                "stock_code", "required", {},
                "股票代碼為必要欄位"
            ),
            ValidationRule(
                "stock_code", "format", {"pattern": r"^\d{4}$"},
                "股票代碼應為4位數字"
            ),
            ValidationRule(
                "company_name", "required", {},
                "公司名稱為必要欄位"
            ),
            ValidationRule(
                "report_year", "type", {"expected_type": int},
                "報告年度應為整數"
            ),
            ValidationRule(
                "report_year", "range", {"min": 2000, "max": 2030},
                "報告年度應在合理範圍內(2000-2030)"
            ),
            ValidationRule(
                "report_season", "format", {"pattern": r"^Q[1-4]$"},
                "報告季度應為Q1-Q4格式"
            ),
            
            # 財務數據驗證
            ValidationRule(
                "financials", "required", {},
                "財務數據欄位為必要", "warning"
            ),
            ValidationRule(
                "income_statement", "required", {},
                "損益表數據為必要", "warning"
            ),
            ValidationRule(
                "balance_sheet", "required", {},
                "資產負債表數據為必要", "warning"
            ),
            
            # 檔案大小驗證
            ValidationRule(
                "metadata.file_size", "range", {"min": 10000, "max": 50000000},
                "檔案大小異常", "warning"
            )
        ]
    
    def validate_financial_report(self, data: Dict[str, Any]) -> ValidationResult:
        """驗證財務報表數據"""
        errors = []
        warnings = []
        info = []
        
        # 執行基本規則驗證
        for rule in self.validation_rules:
            result = self._apply_rule(data, rule)
            if not result[0]:  # 驗證失敗
                if rule.severity == "error":
                    errors.append(result[1])
                elif rule.severity == "warning":
                    warnings.append(result[1])
                else:
                    info.append(result[1])
        
        # 執行自訂驗證
        custom_results = self._custom_validations(data)
        errors.extend(custom_results['errors'])
        warnings.extend(custom_results['warnings'])
        info.extend(custom_results['info'])
        
        # 計算品質分數
        score = self._calculate_quality_score(data, errors, warnings)
        
        # 生成改進建議
        suggestions = self._generate_suggestions(data, errors, warnings)
        
        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            info=info,
            score=score,
            suggestions=suggestions
        )
    
    def _apply_rule(self, data: Dict[str, Any], rule: ValidationRule) -> Tuple[bool, str]:
        """應用單一驗證規則"""
        try:
            # 取得欄位值
            field_value = self._get_nested_value(data, rule.field_name)
            
            if rule.rule_type == "required":
                if field_value is None:
                    return False, rule.error_message
                # 檢查是否為空字典或空列表
                if isinstance(field_value, (dict, list)) and len(field_value) == 0:
                    return False, f"{rule.error_message} (欄位為空)"
            
            elif rule.rule_type == "type":
                expected_type = rule.parameters["expected_type"]
                if field_value is not None and not isinstance(field_value, expected_type):
                    return False, f"{rule.error_message} (實際類型: {type(field_value).__name__})"
            
            elif rule.rule_type == "range":
                if field_value is not None:
                    min_val = rule.parameters.get("min")
                    max_val = rule.parameters.get("max")
                    if min_val is not None and field_value < min_val:
                        return False, f"{rule.error_message} (值太小: {field_value})"
                    if max_val is not None and field_value > max_val:
                        return False, f"{rule.error_message} (值太大: {field_value})"
            
            elif rule.rule_type == "format":
                if field_value is not None:
                    pattern = rule.parameters["pattern"]
                    if not re.match(pattern, str(field_value)):
                        return False, f"{rule.error_message} (格式不符: {field_value})"
            
            return True, ""
            
        except Exception as e:
            return False, f"驗證規則執行錯誤: {e}"
    
    def _get_nested_value(self, data: Dict[str, Any], field_path: str) -> Any:
        """取得巢狀欄位值"""
        keys = field_path.split('.')
        value = data
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        
        return value
    
    def _custom_validations(self, data: Dict[str, Any]) -> Dict[str, List[str]]:
        """自訂驗證邏輯"""
        errors = []
        warnings = []
        info = []
        
        # 檢查財務數據完整性
        financials = data.get('financials', {})
        missing_fields = []
        for field in self.required_financial_fields:
            if field not in financials or financials[field] is None:
                missing_fields.append(field)
        
        if missing_fields:
            warnings.append(f"缺少重要財務數據: {', '.join(missing_fields)}")
        
        # 檢查數據邏輯一致性
        if financials:
            logical_errors = self._check_financial_logic(financials)
            errors.extend(logical_errors)
        
        # 檢查時間一致性
        report_year = data.get('report_year')
        created_at = data.get('metadata', {}).get('created_at')
        if report_year and created_at:
            try:
                created_year = datetime.fromisoformat(created_at.replace('Z', '+00:00')).year
                if abs(created_year - report_year) > 2:
                    warnings.append(f"報告年度({report_year})與建立時間({created_year})差距過大")
            except:
                pass
        
        # 檢查檔案完整性
        metadata = data.get('metadata', {})
        if metadata.get('file_size', 0) < 10000:
            warnings.append("PDF檔案過小，可能不完整")
        
        return {
            'errors': errors,
            'warnings': warnings,
            'info': info
        }
    
    def _check_financial_logic(self, financials: Dict[str, Any]) -> List[str]:
        """檢查財務數據邏輯一致性"""
        errors = []
        
        try:
            # 檢查資產負債表平衡
            total_assets = financials.get('total_assets')
            total_liabilities = financials.get('total_liabilities')
            equity = financials.get('equity')
            
            if all(x is not None for x in [total_assets, total_liabilities, equity]):
                calculated_total = total_liabilities + equity
                if abs(total_assets - calculated_total) / total_assets > 0.01:  # 1%容錯
                    errors.append("資產負債表不平衡：資產 ≠ 負債 + 權益")
            
            # 檢查損益數據合理性
            net_revenue = financials.get('net_revenue')
            gross_profit = financials.get('gross_profit')
            operating_income = financials.get('operating_income')
            net_income = financials.get('net_income')
            
            if net_revenue and gross_profit:
                if gross_profit > net_revenue:
                    errors.append("毛利不應大於營收")
            
            if gross_profit and operating_income:
                if operating_income > gross_profit:
                    errors.append("營業利益不應大於毛利")
            
        except Exception:
            pass  # 數據類型錯誤等，已在其他驗證中處理
        
        return errors
    
    def _calculate_quality_score(self, data: Dict[str, Any], errors: List[str], warnings: List[str]) -> float:
        """計算數據品質分數 (0-100)"""
        base_score = 100.0
        
        # 錯誤扣分
        base_score -= len(errors) * 20
        
        # 警告扣分
        base_score -= len(warnings) * 5
        
        # 財務數據完整度加分
        financials = data.get('financials', {})
        completion_ratio = len([f for f in self.required_financial_fields if f in financials and financials[f] is not None]) / len(self.required_financial_fields)
        completeness_bonus = completion_ratio * 20
        
        # 元數據完整度
        metadata = data.get('metadata', {})
        metadata_fields = ['source', 'file_name', 'file_path', 'file_size', 'created_at']
        metadata_completion = len([f for f in metadata_fields if f in metadata]) / len(metadata_fields)
        metadata_bonus = metadata_completion * 10
        
        final_score = base_score + completeness_bonus + metadata_bonus
        return max(0.0, min(100.0, final_score))
    
    def _generate_suggestions(self, data: Dict[str, Any], errors: List[str], warnings: List[str]) -> List[str]:
        """生成改進建議"""
        suggestions = []
        
        # 基於錯誤的建議
        if any("股票代碼" in error for error in errors):
            suggestions.append("檢查股票代碼格式，應為4位數字")
        
        if any("財務數據" in warning for warning in warnings):
            suggestions.append("建議重新處理PDF以提取更完整的財務數據")
        
        # 基於數據完整性的建議
        financials = data.get('financials', {})
        if not financials:
            suggestions.append("財務數據為空，建議：1) 檢查PDF是否為掃描版 2) 啟用OCR處理 3) 手動驗證數據提取")
        
        # 基於檔案大小的建議
        file_size = data.get('metadata', {}).get('file_size', 0)
        if file_size > 20000000:  # 20MB
            suggestions.append("PDF檔案較大，建議檢查是否包含不必要的圖片或內容")
        elif file_size < 100000:  # 100KB
            suggestions.append("PDF檔案較小，可能內容不完整")
        
        return suggestions


class DataQualityReporter:
    """數據品質報告生成器"""
    
    def __init__(self):
        self.validator = FinancialDataValidator()
    
    def generate_batch_quality_report(self, data_dir: Path) -> Dict[str, Any]:
        """生成批次品質報告"""
        if not data_dir.exists():
            return {"error": f"目錄不存在: {data_dir}"}
        
        json_files = list(data_dir.glob("*.json"))
        results = []
        summary = {
            "total_files": len(json_files),
            "valid_files": 0,
            "files_with_warnings": 0,
            "files_with_errors": 0,
            "average_score": 0.0,
            "common_issues": {},
            "generated_at": datetime.now().isoformat()
        }
        
        total_score = 0.0
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                validation_result = self.validator.validate_financial_report(data)
                
                # 統計
                if validation_result.is_valid:
                    summary["valid_files"] += 1
                else:
                    summary["files_with_errors"] += 1
                
                if validation_result.warnings:
                    summary["files_with_warnings"] += 1
                
                total_score += validation_result.score
                
                # 收集常見問題
                for error in validation_result.errors + validation_result.warnings:
                    key = error.split('(')[0].strip()  # 移除詳細資訊
                    summary["common_issues"][key] = summary["common_issues"].get(key, 0) + 1
                
                results.append({
                    "filename": json_file.name,
                    "is_valid": validation_result.is_valid,
                    "score": validation_result.score,
                    "errors": validation_result.errors,
                    "warnings": validation_result.warnings,
                    "suggestions": validation_result.suggestions
                })
                
            except Exception as e:
                results.append({
                    "filename": json_file.name,
                    "is_valid": False,
                    "score": 0.0,
                    "errors": [f"處理檔案時發生錯誤: {e}"],
                    "warnings": [],
                    "suggestions": ["檢查檔案格式是否正確"]
                })
                summary["files_with_errors"] += 1
        
        if summary["total_files"] > 0:
            summary["average_score"] = total_score / summary["total_files"]
        
        return {
            "summary": summary,
            "detailed_results": results
        }
    
    def save_quality_report(self, report: Dict[str, Any], output_path: Path):
        """儲存品質報告"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    # 測試驗證器
    validator = FinancialDataValidator()
    
    # 測試數據
    test_data = {
        "stock_code": "2330",
        "company_name": "台積電",
        "report_year": 2024,
        "report_season": "Q4",
        "financials": {},  # 空的財務數據
        "metadata": {
            "file_size": 9814510,
            "created_at": "2025-07-01T01:00:30.978072"
        }
    }
    
    result = validator.validate_financial_report(test_data)
    
    print(f"驗證結果: {'✅ 通過' if result.is_valid else '❌ 失敗'}")
    print(f"品質分數: {result.score:.1f}/100")
    
    if result.errors:
        print("\n🔥 錯誤:")
        for error in result.errors:
            print(f"  - {error}")
    
    if result.warnings:
        print("\n⚠️ 警告:")
        for warning in result.warnings:
            print(f"  - {warning}")
    
    if result.suggestions:
        print("\n💡 建議:")
        for suggestion in result.suggestions:
            print(f"  - {suggestion}")
