import tempfile
import unittest
from pathlib import Path

from citegraph.importers import parse_bibtex


class BibTeXImporterTests(unittest.TestCase):
    def parse(self, text: str):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "papers.bib"
            path.write_text(text, encoding="utf-8")
            return parse_bibtex(path)

    def test_parses_single_line_entry_and_numeric_year(self):
        papers = self.parse(
            "@article{key, title={A {Very} Good Paper}, author={Doe, Jane and Roe, John}, year=2024}"
        )

        self.assertEqual(len(papers), 1)
        self.assertEqual(papers[0]["title"], "A Very Good Paper")
        self.assertEqual(papers[0]["authors"], "Doe, Jane, Roe, John")
        self.assertEqual(papers[0]["year"], 2024)

    def test_parses_parenthesized_and_quoted_entry(self):
        papers = self.parse('@book(key, title="Quoted title", doi="10.1000/test")')

        self.assertEqual(len(papers), 1)
        self.assertEqual(papers[0]["doi"], "10.1000/test")
        self.assertEqual(papers[0]["url"], "https://doi.org/10.1000/test")

    def test_ignores_bibtex_directives(self):
        papers = self.parse(
            '@comment{title={Not a paper}}\n@string{journal = "Journal"}\n'
            "@article{real, title={Real paper}}"
        )

        self.assertEqual([paper["title"] for paper in papers], ["Real paper"])

    def test_reports_unterminated_entry(self):
        with self.assertRaisesRegex(ValueError, "Unterminated BibTeX"):
            self.parse("@article{key, title={Broken}")


if __name__ == "__main__":
    unittest.main()
