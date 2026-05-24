"""
Canonical financial taxonomy for Taiwan XBRL-based financial reports.
Maps XBRL tags to canonical field names and provides metadata.
"""

CANONICAL_INCOME: dict[str, dict] = {
    "net_revenue": {
        "unit": "TWD_thousands",
        "xbrl_tags": ["Revenue"],
        "zh": "營業收入",
    },
    "gross_profit": {
        "unit": "TWD_thousands",
        "xbrl_tags": ["GrossProfit"],
        "zh": "營業毛利",
    },
    "operating_income": {
        "unit": "TWD_thousands",
        "xbrl_tags": ["OperatingIncome"],
        "zh": "營業利益",
    },
    "profit_before_tax": {
        "unit": "TWD_thousands",
        "xbrl_tags": ["ProfitBeforeTax"],
        "zh": "稅前淨利",
    },
    "net_income": {
        "unit": "TWD_thousands",
        "xbrl_tags": ["ProfitLoss", "NetIncome"],
        "zh": "本期淨利",
    },
    "net_income_attributable_to_parent": {
        "unit": "TWD_thousands",
        "xbrl_tags": ["ProfitLossAttributableToOwnersOfParent"],
        "zh": "母公司業主淨利",
    },
    "eps_basic": {
        "unit": "TWD_per_share",
        "xbrl_tags": ["BasicEarningsLossPerShare", "EarningsPerShare"],
        "zh": "基本每股盈餘",
    },
    "eps_diluted": {
        "unit": "TWD_per_share",
        "xbrl_tags": ["DilutedEarningsLossPerShare"],
        "zh": "稀釋每股盈餘",
    },
    "operating_expenses": {
        "unit": "TWD_thousands",
        "xbrl_tags": ["OperatingExpenses"],
        "zh": "營業費用",
    },
    "rd_expenses": {
        "unit": "TWD_thousands",
        "xbrl_tags": ["ResearchAndDevelopmentExpenses"],
        "zh": "研究發展費用",
    },
    "tax_expense": {
        "unit": "TWD_thousands",
        "xbrl_tags": ["TaxExpense"],
        "zh": "所得稅費用",
    },
    "comprehensive_income": {
        "unit": "TWD_thousands",
        "xbrl_tags": ["ComprehensiveIncome"],
        "zh": "綜合損益總額",
    },
}

CANONICAL_BALANCE: dict[str, dict] = {
    "cash_and_equivalents": {
        "unit": "TWD_thousands",
        "xbrl_tags": ["CashAndCashEquivalents"],
        "zh": "現金及約當現金",
    },
    "accounts_receivable": {
        "unit": "TWD_thousands",
        "xbrl_tags": ["AccountsReceivable"],
        "zh": "應收帳款",
    },
    "inventory": {
        "unit": "TWD_thousands",
        "xbrl_tags": ["Inventory"],
        "zh": "存貨",
    },
    "current_assets": {
        "unit": "TWD_thousands",
        "xbrl_tags": ["CurrentAssets"],
        "zh": "流動資產合計",
    },
    "total_assets": {
        "unit": "TWD_thousands",
        "xbrl_tags": ["Assets"],
        "zh": "資產總額",
    },
    "accounts_payable": {
        "unit": "TWD_thousands",
        "xbrl_tags": ["AccountsPayable"],
        "zh": "應付帳款",
    },
    "current_liabilities": {
        "unit": "TWD_thousands",
        "xbrl_tags": ["CurrentLiabilities"],
        "zh": "流動負債合計",
    },
    "total_liabilities": {
        "unit": "TWD_thousands",
        "xbrl_tags": ["Liabilities"],
        "zh": "負債總額",
    },
    "equity": {
        "unit": "TWD_thousands",
        "xbrl_tags": ["Equity"],
        "zh": "權益總額",
    },
    "equity_attributable_to_parent": {
        "unit": "TWD_thousands",
        "xbrl_tags": ["EquityAttributableToOwnersOfParent"],
        "zh": "母公司業主權益",
    },
    "retained_earnings": {
        "unit": "TWD_thousands",
        "xbrl_tags": ["RetainedEarnings"],
        "zh": "保留盈餘",
    },
    "share_capital": {
        "unit": "TWD_thousands",
        "xbrl_tags": ["ShareCapital"],
        "zh": "股本",
    },
}

CANONICAL_CASHFLOW: dict[str, dict] = {
    "operating_cash_flow": {
        "unit": "TWD_thousands",
        "xbrl_tags": ["CashFlowsFromOperatingActivities"],
        "zh": "營業活動現金流量",
    },
    "investing_cash_flow": {
        "unit": "TWD_thousands",
        "xbrl_tags": ["CashFlowsFromInvestingActivities"],
        "zh": "投資活動現金流量",
    },
    "financing_cash_flow": {
        "unit": "TWD_thousands",
        "xbrl_tags": ["CashFlowsFromFinancingActivities"],
        "zh": "籌資活動現金流量",
    },
    "capex": {
        "unit": "TWD_thousands",
        "xbrl_tags": ["AcquisitionOfPropertyPlantAndEquipment"],
        "zh": "購買不動產廠房設備",
    },
    "free_cash_flow": {
        "unit": "TWD_thousands",
        "xbrl_tags": [],
        "zh": "自由現金流量",
    },  # computed
    "cash_beginning": {
        "unit": "TWD_thousands",
        "xbrl_tags": ["CashAndCashEquivalentsAtBeginningOfPeriod"],
        "zh": "期初現金及約當現金",
    },
    "cash_ending": {
        "unit": "TWD_thousands",
        "xbrl_tags": ["CashAndCashEquivalentsAtEndOfPeriod"],
        "zh": "期末現金及約當現金",
    },
}

ALL_CANONICAL: dict[str, dict] = {
    **CANONICAL_INCOME,
    **CANONICAL_BALANCE,
    **CANONICAL_CASHFLOW,
}

# Reverse mapping: xbrl_tag -> canonical field name
XBRL_TO_CANONICAL: dict[str, str] = {}
for field, meta in ALL_CANONICAL.items():
    for tag in meta.get("xbrl_tags", []):
        XBRL_TO_CANONICAL[tag] = field

# Known XBRL tags
KNOWN_XBRL_TAGS: set[str] = {
    "Revenue",
    "ProfitLoss",
    "Assets",
    "Liabilities",
    "Equity",
    "OperatingIncome",
    "OperatingExpenses",
    "EarningsPerShare",
    "NetIncome",
    "GrossProfit",
    "CurrentAssets",
    "CurrentLiabilities",
    "CashAndCashEquivalents",
    "Inventory",
    "AccountsReceivable",
    "AccountsPayable",
    "ResearchAndDevelopmentExpenses",
    "SellingAndMarketingExpenses",
    "GeneralAndAdministrativeExpenses",
    "FinancialCosts",
    "TaxExpense",
    "ComprehensiveIncome",
    "RetainedEarnings",
    "ShareCapital",
    "BookValuePerShare",
    "ReturnOnAssets",
    "ReturnOnEquity",
    "DebtToEquityRatio",
    "CurrentRatio",
    "QuickRatio",
    "BasicEarningsLossPerShare",
    "DilutedEarningsLossPerShare",
    "ProfitBeforeTax",
    "ProfitLossAttributableToOwnersOfParent",
    "EquityAttributableToOwnersOfParent",
    "CashFlowsFromOperatingActivities",
    "CashFlowsFromInvestingActivities",
    "CashFlowsFromFinancingActivities",
    "AcquisitionOfPropertyPlantAndEquipment",
    "CashAndCashEquivalentsAtBeginningOfPeriod",
    "CashAndCashEquivalentsAtEndOfPeriod",
}

# Statement type classification
FIELD_TO_STATEMENT: dict[str, str] = {}
for _field in CANONICAL_INCOME:
    FIELD_TO_STATEMENT[_field] = "income_statement"
for _field in CANONICAL_BALANCE:
    FIELD_TO_STATEMENT[_field] = "balance_sheet"
for _field in CANONICAL_CASHFLOW:
    FIELD_TO_STATEMENT[_field] = "cash_flow"
