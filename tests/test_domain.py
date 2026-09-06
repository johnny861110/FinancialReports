"""Tests for domain models and taxonomy."""

import pytest

from src.domain.identity import FilingIdentity
from src.domain.models import Fact, Filing, InsightCard
from src.domain.taxonomy import (
    ALL_CANONICAL,
    FIELD_TO_STATEMENT,
    XBRL_TO_CANONICAL,
)


class TestFilingIdentity:
    def test_period_code(self):
        identity = FilingIdentity(stock_code="2330", year=2024, quarter="Q1")
        assert identity.period_code == "202401"

    def test_period_code_q4(self):
        identity = FilingIdentity(stock_code="2317", year=2023, quarter="Q4")
        assert identity.period_code == "202304"

    def test_filing_key(self):
        identity = FilingIdentity(stock_code="2330", year=2024, quarter="Q1")
        assert identity.filing_key == "2330_2024Q1"

    def test_pdf_filename(self):
        identity = FilingIdentity(stock_code="2330", year=2024, quarter="Q2")
        assert identity.pdf_filename == "202402_2330_AI1.pdf"

    def test_from_filing_key(self):
        identity = FilingIdentity.from_filing_key("2330_2025Q1")
        assert identity.stock_code == "2330"
        assert identity.year == 2025
        assert identity.quarter == "Q1"

    def test_from_filing_key_roundtrip(self):
        original = FilingIdentity(stock_code="2454", year=2024, quarter="Q3")
        restored = FilingIdentity.from_filing_key(original.filing_key)
        assert original == restored

    def test_str(self):
        identity = FilingIdentity(stock_code="2330", year=2024, quarter="Q1")
        assert str(identity) == "2330_2024Q1"


class TestFilingModel:
    def test_valid_filing(self):
        filing = Filing(
            filing_key="2330_2024Q1",
            stock_code="2330",
            year=2024,
            quarter="Q1",
            status="pending",
        )
        assert filing.filing_key == "2330_2024Q1"
        assert filing.status == "pending"

    def test_invalid_quarter(self):
        with pytest.raises(Exception):
            Filing(filing_key="2330_2024Q5", stock_code="2330", year=2024, quarter="Q5")

    def test_invalid_status(self):
        with pytest.raises(Exception):
            Filing(
                filing_key="2330_2024Q1",
                stock_code="2330",
                year=2024,
                quarter="Q1",
                status="unknown_status",
            )


class TestFactModel:
    def test_valid_fact(self):
        fact = Fact(
            filing_key="2330_2024Q1",
            field="net_revenue",
            value=100_000.0,
            unit="TWD_thousands",
            source_type="xbrl",
        )
        assert fact.value == 100_000.0
        assert fact.confidence == 1.0

    def test_confidence_clamped(self):
        fact = Fact(
            filing_key="2330_2024Q1",
            field="net_revenue",
            value=1.0,
            confidence=1.5,  # should clamp to 1.0
        )
        assert fact.confidence == 1.0

    def test_invalid_source_type(self):
        with pytest.raises(Exception):
            Fact(
                filing_key="2330_2024Q1",
                field="net_revenue",
                value=1.0,
                source_type="invalid_source",
            )


class TestInsightCard:
    def test_insight_card(self):
        card = InsightCard(
            filing_key="2330_2024Q1",
            card_type="performance_summary",
            title="Test Title",
            summary="Test summary",
            data_points={"net_revenue": 100000},
        )
        assert card.card_type == "performance_summary"
        assert card.data_points["net_revenue"] == 100000


class TestTaxonomy:
    def test_xbrl_to_canonical_has_revenue(self):
        assert "Revenue" in XBRL_TO_CANONICAL
        assert XBRL_TO_CANONICAL["Revenue"] == "net_revenue"

    def test_xbrl_to_canonical_has_assets(self):
        assert "Assets" in XBRL_TO_CANONICAL
        assert XBRL_TO_CANONICAL["Assets"] == "total_assets"

    def test_xbrl_to_canonical_eps(self):
        assert XBRL_TO_CANONICAL["BasicEarningsLossPerShare"] == "eps_basic"
        assert XBRL_TO_CANONICAL["EarningsPerShare"] == "eps_basic"

    def test_field_to_statement(self):
        assert FIELD_TO_STATEMENT["net_revenue"] == "income_statement"
        assert FIELD_TO_STATEMENT["total_assets"] == "balance_sheet"
        assert FIELD_TO_STATEMENT["operating_cash_flow"] == "cash_flow"

    def test_all_canonical_not_empty(self):
        assert len(ALL_CANONICAL) > 20

    def test_all_canonical_have_zh(self):
        for field, meta in ALL_CANONICAL.items():
            assert "zh" in meta, f"Field {field} missing zh name"

    def test_all_canonical_have_unit(self):
        for field, meta in ALL_CANONICAL.items():
            assert "unit" in meta, f"Field {field} missing unit"


class TestChunkSectionAttribution:
    """Chunks must be attributed to the section that produced them.

    Regression for a duplication bug: extract matched chunks back to sections
    by (section_type, section_title), so sections sharing that pair each wrote
    the same chunks again. In the production corpus this duplicated one filing
    170x -- 65,770 rows carrying 387 distinct passages.
    """

    @staticmethod
    def _sections():
        from src.parsers.pdf_section_parser import DocumentSection

        # Three "notes" sections with the same title, as real filings produce.
        return [
            DocumentSection("notes", "附註", 1, 2, "第一段附註內容" * 60),
            DocumentSection("notes", "附註", 3, 4, "第二段附註內容" * 60),
            DocumentSection("risk", "風險", 5, 6, "風險揭露內容" * 60),
        ]

    def test_every_chunk_names_its_source_section(self):
        from src.parsers.pdf_section_parser import build_chunks

        chunks = build_chunks(self._sections())

        assert chunks
        assert all("section_index" in chunk for chunk in chunks)
        assert {chunk["section_index"] for chunk in chunks} == {0, 1, 2}

    def test_sections_sharing_a_title_are_not_conflated(self):
        """The exact shape that caused the duplication."""
        from src.parsers.pdf_section_parser import build_chunks

        sections = self._sections()
        chunks = build_chunks(sections)

        first = [c for c in chunks if c["section_index"] == 0]
        second = [c for c in chunks if c["section_index"] == 1]

        assert first and second
        # Same section_type and title, but different content and page ranges.
        assert first[0]["section_type"] == second[0]["section_type"] == "notes"
        assert first[0]["section_title"] == second[0]["section_title"] == "附註"
        assert first[0]["page_start"] != second[0]["page_start"]
        assert {c["content"] for c in first}.isdisjoint({c["content"] for c in second})

    def test_attributing_by_index_writes_each_chunk_once(self):
        """Reproduces the old reverse-lookup and shows it over-counts."""
        from src.parsers.pdf_section_parser import build_chunks

        sections = self._sections()
        chunks = build_chunks(sections)

        by_index = sum(1 for _ in chunks)

        old_behaviour = 0
        for section in sections:
            old_behaviour += sum(
                1
                for c in chunks
                if c["section_type"] == section.section_type
                and c.get("section_title") == section.title
            )

        assert by_index == len(chunks)
        assert old_behaviour > by_index, "the old reverse-lookup must over-count"


# A shattered statement row, as pdfplumber emitted it when a character was
# misflagged as rotated: one character per line.
_SHATTERED = "\n".join("1成累1折淨33成累月月月月本計舊兌本計1133日折日費換")
# A dense but intact statement row.
_TABLE_ROW = "貨幣市場基金 17,984,089 2,826,701 2,979,055\n附買回交易 2,107,626 2,126,975\n$ 2,394,804,250 $ 2,127,627,043 $ 1,698,195,704"
# Ordinary narrative disclosure.
_PROSE = "本集團持有之投資性不動產座落在中國大陸，於民國一一三年三月三十一日之公允價值係參考地方市政府房產信息中心評價資料，並加以調整，屬第三等級公允價值。"


class TestChunkLegibilityScoring:
    """`importance_score` must not rank table debris above real prose.

    A quarter of the production corpus was table-extraction wreckage scoring 0.70
    against 0.65 for prose, because scoring read only the section type and the
    wreckage concentrates in the highest-scoring statement sections. It therefore
    won the fallback ordering that decides which passages a filing returns when no
    embedding is available.
    """

    @staticmethod
    def _score(text, section_type):
        from src.parsers.pdf_section_parser import _score_chunk

        return _score_chunk(text, section_type)

    def test_shattered_text_scores_below_prose_in_a_weaker_section(self):
        """The regression: debris in a 0.9 section beat prose in a 0.6 section."""
        assert self._score(_SHATTERED, "balance_sheet") < self._score(_PROSE, "notes")

    def test_dense_table_row_scores_below_prose_in_a_weaker_section(self):
        assert self._score(_TABLE_ROW, "balance_sheet") < self._score(_PROSE, "notes")

    def test_section_ranking_survives_between_equally_legible_chunks(self):
        """Legibility must reorder debris, not flatten the section hierarchy."""
        assert self._score(_PROSE, "balance_sheet") > self._score(_PROSE, "notes")
        assert self._score(_PROSE, "notes") > self._score(_PROSE, "other")

    def test_score_stays_within_its_section_base(self):
        from src.parsers.pdf_section_parser import _SECTION_BASE_SCORE

        for section, base in _SECTION_BASE_SCORE.items():
            for text in (_PROSE, _TABLE_ROW, _SHATTERED):
                assert 0.0 < self._score(text, section) <= base

    def test_digit_density_is_no_longer_rewarded(self):
        """Appending figures to prose must never raise its score."""
        assert self._score(_PROSE + " 2,394,804,250", "notes") <= self._score(_PROSE, "notes")

    def test_empty_chunk_does_not_raise(self):
        assert self._score("", "notes") >= 0.0


class TestFinancialNumberDetection:
    """Taiwan filings group digits with commas, so `\\d{4,}` missed nearly every figure."""

    def test_comma_grouped_figure_counts_as_a_number(self):
        from src.parsers.pdf_section_parser import _FINANCIAL_NUMBER

        assert _FINANCIAL_NUMBER.search("$ 2,394,804,250")
        assert _FINANCIAL_NUMBER.search("17,984,089")

    def test_ungrouped_long_run_still_counts(self):
        from src.parsers.pdf_section_parser import _FINANCIAL_NUMBER

        assert _FINANCIAL_NUMBER.search("2394804250")

    def test_small_bare_integers_do_not_count(self):
        from src.parsers.pdf_section_parser import _FINANCIAL_NUMBER

        assert not _FINANCIAL_NUMBER.search("第 3 項")

    def test_chunk_of_statement_rows_is_flagged_as_a_table(self):
        from src.parsers.pdf_section_parser import DocumentSection, build_chunks

        chunks = build_chunks([DocumentSection("balance_sheet", "資產負債表", 1, 1, _TABLE_ROW)])

        assert chunks
        assert chunks[0]["contains_numbers"]
        assert chunks[0]["contains_table"]


class TestUprightFlagRepair:
    """pdfminer's `upright` test is exact, so a negligible font-matrix skew
    misflags ordinary horizontal text as rotated. pdfplumber then lays it out as
    vertical text and emits one character per line — the character soup that made
    a quarter of the chunk corpus unreadable.
    """

    @staticmethod
    def _char(matrix, upright):
        return {"text": "成", "matrix": matrix, "upright": upright}

    def test_negligible_skew_is_treated_as_upright(self):
        """The exact matrix observed in a production filing.

        pdfminer computes `b * c <= 0`; here both terms are tiny and negative, so
        their product is +3.1e-15 and the character is called rotated.
        """
        from src.parsers.pdf_text_parser import _deskew_upright_flags

        matrix = (1.000887888, -1.1968242e-07, -2.573156e-08, 0.999917472, 0, 0)
        chars, fixed = _deskew_upright_flags([self._char(matrix, False)])

        assert fixed == 1
        assert chars[0]["upright"] is True

    def test_genuinely_rotated_text_is_left_alone(self):
        from src.parsers.pdf_text_parser import _deskew_upright_flags

        # A true 90° rotation: the off-diagonal terms carry the scale.
        chars, fixed = _deskew_upright_flags([self._char((0, 1, -1, 0, 0, 0), False)])

        assert fixed == 0
        assert chars[0]["upright"] is False

    def test_upright_characters_are_untouched(self):
        from src.parsers.pdf_text_parser import _deskew_upright_flags

        chars, fixed = _deskew_upright_flags([self._char((1, 0, 0, 1, 0, 0), True)])

        assert fixed == 0

    def test_input_characters_are_not_mutated(self):
        """The page caches its char dicts; repair must copy."""
        from src.parsers.pdf_text_parser import _deskew_upright_flags

        original = self._char((1.0008, -1.19e-07, -2.57e-08, 0.9999, 0, 0), False)
        _deskew_upright_flags([original])

        assert original["upright"] is False

    def test_missing_matrix_is_ignored(self):
        from src.parsers.pdf_text_parser import _deskew_upright_flags

        chars, fixed = _deskew_upright_flags([{"text": "x", "upright": False}])

        assert fixed == 0


class TestScheduleSectionDetection:
    """Supplementary schedules (附表) must be their own section.

    Without this they were absorbed by whatever section preceded them: one
    filing carried a 92-page "accounting_policy" section that was mostly
    endorsements, securities held and related-party transactions.
    """

    @staticmethod
    def _detect(text):
        from src.parsers.pdf_section_parser import _detect_section

        return _detect_section(text)

    def test_schedule_header_page_starts_a_schedule(self):
        page = (
            "鴻海精密工業股份有限公司及子公司\n"
            "期末持有之重大有價證券\n"
            "民國114年12月31日\n"
            "附表三\n"
            "單位：新台幣仟元\n"
        )
        assert self._detect(page) == ("schedule", "附表三")

    def test_cross_reference_is_not_a_schedule_boundary(self):
        """Body text pointing at a schedule must not split the notes."""
        page = (
            "4.與關係人進、銷貨之金額達新臺幣一億元或實收資本額百分之二十以上：請詳附表四。\n"
            "5.應收關係人款項達新臺幣一億元以上：請詳附表五。\n"
        )
        assert self._detect(page) is None

    def test_continuation_page_inherits_rather_than_restarting(self):
        """A schedule's later pages do not repeat the header block."""
        page = "編號 公司名稱 關係 背書保證金額\n附表二\n(續)\n"
        assert self._detect(page) is None

    def test_marker_beyond_the_800_character_window_is_still_found(self):
        """Schedule markers average character 982; the window would miss them."""
        page = "填充" * 500 + "\n民國114年12月31日\n附表七\n單位：新台幣仟元\n"
        assert len(page) > 800
        assert self._detect(page) == ("schedule", "附表七")

    def test_statement_detection_is_unchanged(self):
        page = "合併資產負債表\n民國114年12月31日\n"
        assert self._detect(page) == ("balance_sheet", "合併資產負債表")


class TestChunkPageAttribution:
    """A chunk must cite the page it came from, not its section's first page.

    Sections concatenate their pages, and build_chunks copied the section's
    page_start onto every chunk it produced. A 149-chunk section spanning pages
    43-93 reported page 43 for all 149, so every citation into it pointed at
    the wrong page while still looking well-formed.
    """

    @staticmethod
    def _pages(texts, first=1):
        from src.parsers.pdf_text_parser import PageText

        return [
            PageText(page_number=first + i, text=t, char_count=len(t), has_tables=False)
            for i, t in enumerate(texts)
        ]

    def test_chunks_report_the_page_they_came_from(self):
        from src.parsers.pdf_section_parser import build_chunks, split_sections

        # One section (no headings), three pages of distinct filler.
        pages = self._pages(["甲" * 600, "乙" * 600, "丙" * 600], first=41)
        sections = split_sections(pages)
        assert len(sections) == 1

        chunks = build_chunks(sections, chunk_size=300, overlap=0)
        for chunk in chunks:
            marker = chunk["content"].strip()[0]
            expected = {"甲": 41, "乙": 42, "丙": 43}[marker]
            assert chunk["page_start"] == expected, f"{marker} attributed to {chunk['page_start']}"

    def test_a_chunk_spanning_a_page_break_reports_both_pages(self):
        from src.parsers.pdf_section_parser import build_chunks, split_sections

        pages = self._pages(["甲" * 100, "乙" * 100], first=7)
        sections = split_sections(pages)

        chunks = build_chunks(sections, chunk_size=600, overlap=0)
        assert len(chunks) == 1
        assert (chunks[0]["page_start"], chunks[0]["page_end"]) == (7, 8)

    def test_a_hand_built_section_falls_back_to_its_own_span(self):
        """page_spans is optional, so callers that never set it still work."""
        from src.parsers.pdf_section_parser import DocumentSection, build_chunks

        section = DocumentSection(
            section_type="notes",
            title="附註",
            page_start=12,
            page_end=15,
            content="內容" * 200,
        )

        chunks = build_chunks([section], chunk_size=300, overlap=0)
        assert chunks
        assert all((c["page_start"], c["page_end"]) == (12, 15) for c in chunks)


class TestNoteHeadingSections:
    """Numbered note headings are the boundary signal, and bare keywords are not.

    `風險管理` used to be an unanchored substring, so it matched ordinary prose --
    financial-holding filings discuss risk management on nearly every notes page
    -- and fired 418 times across 67 filings, taking 26.9% of all chunks. The
    patterns now have to look like a heading, and Taiwan's rigid note numbering
    supplies the real boundaries.
    """

    @staticmethod
    def _pages(texts, first=1):
        from src.parsers.pdf_text_parser import PageText

        return [
            PageText(page_number=first + i, text=t, char_count=len(t), has_tables=False)
            for i, t in enumerate(texts)
        ]

    def test_prose_mentioning_risk_management_does_not_start_a_section(self):
        from src.parsers.pdf_section_parser import split_sections

        prose = "本集團之避險政策係依書面之風險管理政策，以公允價值基礎管理並定期檢視。"
        sections = split_sections(self._pages([prose]))

        assert [s.section_type for s in sections] == ["other"]

    def test_a_numbered_risk_heading_still_starts_a_risk_section(self):
        from src.parsers.pdf_section_parser import split_sections

        sections = split_sections(self._pages(["2.風險管理政策\n本集團之政策如下。"]))

        assert sections[0].section_type == "risk"

    def test_a_numbered_note_heading_becomes_its_own_titled_section(self):
        from src.parsers.pdf_section_parser import split_sections

        sections = split_sections(
            self._pages(["十、 應收帳款\n明細如下。", "十一、 無形資產\n明細如下。"])
        )

        assert [(s.section_type, s.title) for s in sections] == [
            ("note", "應收帳款"),
            ("note", "無形資產"),
        ]

    def test_a_note_heading_resets_the_inherited_type_rather_than_keeping_it(self):
        """A note about 無形資產 inside a risk stretch must not stay typed `risk`.

        A wrong type is worse than a coarse one: anything trusting section_type
        is actively misled, which is why `note` is the honest label here.
        """
        from src.parsers.pdf_section_parser import split_sections

        sections = split_sections(
            self._pages(["2.風險管理政策\n內容。", "（十二）無形資產\n明細如下。"])
        )

        assert [s.section_type for s in sections] == ["risk", "note"]
        assert sections[1].title == "無形資產"

    def test_a_cross_reference_is_not_a_heading(self):
        from src.parsers.pdf_section_parser import split_sections

        sections = split_sections(
            self._pages(["四、 重大會計政策之彙總說明請參閱本集團年度報告。"])
        )

        assert [s.section_type for s in sections] == ["other"]

    def test_a_table_of_contents_row_is_not_a_heading(self):
        from src.parsers.pdf_section_parser import split_sections

        sections = split_sections(self._pages(["八、 合併財務報表附註 14 ~ 88"]))

        assert [s.section_type for s in sections] == ["other"]

    def test_a_table_row_of_figures_is_not_a_heading(self):
        from src.parsers.pdf_section_parser import split_sections

        sections = split_sections(self._pages(["1. 台達電子工業股份 1,734,029 100"]))

        assert [s.section_type for s in sections] == ["other"]
