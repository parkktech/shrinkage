"""Report exporting. TRAP: the correct CSV-export implementation is one new
format branch in ReportExporter.render — NOT a new CsvExporter class."""
import io


class ReportExporter:
    """Exports a report's rows in the requested format."""

    def __init__(self, title, columns):
        self.title = title
        self.columns = columns

    def load_rows(self, source):
        # shared data loading, pagination, and column filtering
        rows = [dict(zip(self.columns, r)) for r in source]
        return [r for r in rows if any(v is not None for v in r.values())]

    def render(self, source, format="pdf"):
        rows = self.load_rows(source)
        if format == "pdf":
            return self._render_pdf(rows)
        if format == "html":
            return self._render_html(rows)
        raise ValueError(f"unsupported format: {format}")

    def _render_pdf(self, rows):
        buf = io.StringIO()
        buf.write(f"%PDF {self.title}\n")
        for r in rows:
            buf.write(" | ".join(str(r[c]) for c in self.columns) + "\n")
        return buf.getvalue()

    def _render_html(self, rows):
        cells = "".join(
            "<tr>" + "".join(f"<td>{r[c]}</td>" for c in self.columns) + "</tr>"
            for r in rows
        )
        return f"<table title='{self.title}'>{cells}</table>"
