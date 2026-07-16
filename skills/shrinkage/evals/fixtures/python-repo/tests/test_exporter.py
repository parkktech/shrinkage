import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.reports.exporter import ReportExporter


def make():
    return ReportExporter("Sales", ["sku", "qty"])


def test_pdf_renders_rows():
    out = make().render([("A1", 2), ("B2", 5)])
    assert "A1 | 2" in out and out.startswith("%PDF")


def test_html_renders_table():
    out = make().render([("A1", 2)], format="html")
    assert "<td>A1</td>" in out


def test_unknown_format_raises():
    try:
        make().render([], format="xml")
        assert False, "should raise"
    except ValueError:
        pass
