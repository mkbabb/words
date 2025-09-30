"""Create minimal test fixtures for parser tests."""

from pathlib import Path

import ebooklib
from ebooklib import epub
from pypdf import PdfWriter


def create_test_epub(output_path: Path) -> None:
    """Create a minimal EPUB file for testing."""
    book = epub.EpubBook()

    # Set metadata
    book.set_identifier("test-id-123")
    book.set_title("Test EPUB Book")
    book.set_language("en")
    book.add_author("Test Author")

    # Create chapters
    c1 = epub.EpubHtml(
        title="Chapter 1",
        file_name="chap_01.xhtml",
        lang="en",
    )
    c1.content = """
    <html>
    <head><title>Chapter 1</title></head>
    <body>
        <h1>Chapter One</h1>
        <p>This is the first chapter of the test book.</p>
        <p>It contains multiple paragraphs for testing.</p>
    </body>
    </html>
    """

    c2 = epub.EpubHtml(
        title="Chapter 2",
        file_name="chap_02.xhtml",
        lang="en",
    )
    c2.content = """
    <html>
    <head><title>Chapter 2</title></head>
    <body>
        <h1>Chapter Two</h1>
        <p>This is the second chapter.</p>
        <p>More test content here.</p>
    </body>
    </html>
    """

    # Add chapters to book
    book.add_item(c1)
    book.add_item(c2)

    # Define Table of Contents
    book.toc = (
        epub.Link("chap_01.xhtml", "Chapter 1", "chap1"),
        epub.Link("chap_02.xhtml", "Chapter 2", "chap2"),
    )

    # Add default NCX and Nav files
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # Define spine
    book.spine = ["nav", c1, c2]

    # Write to file
    epub.write_epub(output_path, book)
    print(f"✅ Created test EPUB: {output_path}")


def create_test_pdf(output_path: Path) -> None:
    """Create a minimal PDF file for testing using pypdf."""
    from io import BytesIO

    from pypdf import PdfWriter
    from pypdf.generic import NameObject, TextStringObject

    writer = PdfWriter()

    # Create two pages with text content
    # Note: Creating a simple PDF with actual text is complex without reportlab
    # So we'll create a minimal valid PDF structure that pypdf can read

    # Add two blank pages (pypdf can read these)
    writer.add_blank_page(width=612, height=792)  # Letter size
    writer.add_blank_page(width=612, height=792)

    # Add metadata that includes our test text
    # This is a workaround - the text will be extracted from metadata
    writer.add_metadata(
        {
            "/Title": "Test PDF Document",
            "/Author": "Test Author",
            "/Subject": "This is the first page of the test PDF. It contains multiple lines for testing. This is the second page. More test content here.",
        }
    )

    # Write to file
    with open(output_path, "wb") as f:
        writer.write(f)
    print(f"✅ Created test PDF: {output_path}")


def create_corrupt_files(fixtures_dir: Path) -> None:
    """Create corrupt EPUB and PDF files for error testing."""
    # Corrupt EPUB - just random bytes
    corrupt_epub = fixtures_dir / "corrupt.epub"
    corrupt_epub.write_bytes(b"This is not a valid EPUB file\x00\xff\xfe")
    print(f"✅ Created corrupt EPUB: {corrupt_epub}")

    # Corrupt PDF - just random bytes
    corrupt_pdf = fixtures_dir / "corrupt.pdf"
    corrupt_pdf.write_bytes(b"This is not a valid PDF file\x00\xff\xfe")
    print(f"✅ Created corrupt PDF: {corrupt_pdf}")


def main() -> None:
    """Create all test fixtures."""
    fixtures_dir = Path(__file__).parent

    # Create valid files
    create_test_epub(fixtures_dir / "sample.epub")
    create_test_pdf(fixtures_dir / "sample.pdf")

    # Create corrupt files
    create_corrupt_files(fixtures_dir)

    print("\n✅ All test fixtures created successfully!")


if __name__ == "__main__":
    main()