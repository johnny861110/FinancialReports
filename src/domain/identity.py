from dataclasses import dataclass


@dataclass(frozen=True)
class FilingIdentity:
    stock_code: str  # "2330"
    year: int  # 2025 (CE year)
    quarter: str  # "Q1"|"Q2"|"Q3"|"Q4"

    QUARTER_MAP = {"Q1": "01", "Q2": "02", "Q3": "03", "Q4": "04"}

    @property
    def period_code(self) -> str:
        return f"{self.year}{self.QUARTER_MAP[self.quarter]}"

    @property
    def filing_key(self) -> str:
        return f"{self.stock_code}_{self.year}{self.quarter}"

    @property
    def pdf_filename(self) -> str:
        return f"{self.period_code}_{self.stock_code}_AI1.pdf"

    @classmethod
    def from_filing_key(cls, key: str) -> "FilingIdentity":
        """Parse '2330_2025Q1' into FilingIdentity."""
        parts = key.split("_")
        stock_code = parts[0]
        year = int(parts[1][:4])
        quarter = parts[1][4:]
        return cls(stock_code=stock_code, year=year, quarter=quarter)

    def __str__(self) -> str:
        return self.filing_key
