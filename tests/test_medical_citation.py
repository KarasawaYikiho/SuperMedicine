from plugins.standards.medical_citation.ama_format import AMAFormatter, JournalArticle, Book
from plugins.standards.medical_citation.vancouver_format import VancouverFormatter


class TestAMAFormatter:
    def test_journal_article(self):
        formatter = AMAFormatter()
        article = JournalArticle(
            authors=["John Smith", "Jane Doe"],
            title="Cardiovascular Risk Factors",
            journal="JAMA",
            year=2024,
            volume="331",
            issue="5",
            pages="401-410",
            doi="10.1001/jama.2024.1234",
        )
        result = formatter.format_journal(article)
        assert "Smith J" in result
        assert "Doe J" in result
        assert "JAMA" in result
        assert "2024" in result

    def test_book(self):
        formatter = AMAFormatter()
        book = Book(
            authors=["Robert Jones"],
            title="Medical Statistics",
            publisher="Springer",
            year=2023,
            edition="3rd",
        )
        result = formatter.format_book(book)
        assert "Jones R" in result
        assert "Medical Statistics" in result


class TestVancouverFormatter:
    def test_journal_article(self):
        formatter = VancouverFormatter()
        article = JournalArticle(
            authors=["John Smith", "Jane Doe"],
            title="Cardiovascular Risk Factors",
            journal="JAMA",
            year=2024,
            volume="331",
            issue="5",
            pages="401-410",
        )
        result = formatter.format_journal(article)
        assert "Smith J" in result
        assert "JAMA" in result
