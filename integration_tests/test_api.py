"""
Publish Markdown files to Confluence wiki.

Copyright 2022-2025, Levente Hunyadi

:see: https://github.com/hunyadi/md2conf
"""

import hashlib
import logging
import os
import shutil
import unittest
from pathlib import Path

from md2conf.api import ConfluenceAPI, ConfluenceAttachment, ConfluencePage
from md2conf.application import Application
from md2conf.converter import (
    ConfluenceDocument,
    ConfluenceDocumentOptions,
    ConfluenceSiteMetadata,
    read_qualified_id,
    sanitize_confluence,
)

TEST_PAGE_TITLE = "Publish to Confluence"
TEST_SPACE = "~hunyadi"
TEST_PAGE_ID = "1933314"

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(funcName)s [%(lineno)d] - %(message)s",
)


class TestAPI(unittest.TestCase):
    out_dir: Path
    sample_dir: Path

    def setUp(self) -> None:
        test_dir = Path(__file__).parent
        parent_dir = test_dir.parent

        self.out_dir = test_dir / "output"
        self.sample_dir = parent_dir / "sample"
        os.makedirs(self.out_dir, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.out_dir)

    def test_markdown(self) -> None:
        document = ConfluenceDocument(
            self.sample_dir / "index.md",
            ConfluenceDocumentOptions(),
            self.sample_dir,
            ConfluenceSiteMetadata("example.com", "/wiki/", "SPACE_KEY"),
            {},
        )
        self.assertListEqual(document.links, [])
        self.assertListEqual(
            document.images,
            [Path("figure/interoperability.png"), Path("figure/interoperability.png")],
        )

        with open(self.out_dir / "document.html", "w", encoding="utf-8") as f:
            f.write(document.xhtml())

    def test_find_page_by_title(self) -> None:
        with ConfluenceAPI() as api:
            page_id = api.get_page_id_by_title(TEST_PAGE_TITLE)
            self.assertEqual(page_id, TEST_PAGE_ID)

    def test_get_page(self) -> None:
        with ConfluenceAPI() as api:
            page = api.get_page(TEST_PAGE_ID)
            self.assertIsInstance(page, ConfluencePage)

        with open(self.out_dir / "page.html", "w", encoding="utf-8") as f:
            f.write(sanitize_confluence(page.content))

    def test_get_attachment(self) -> None:
        with ConfluenceAPI() as api:
            data = api.get_attachment_by_name(
                TEST_PAGE_ID, "figure_interoperability.png"
            )
            self.assertIsInstance(data, ConfluenceAttachment)

    def test_upload_attachment(self) -> None:
        with ConfluenceAPI() as api:
            api.upload_attachment(
                TEST_PAGE_ID,
                "figure_interoperability.png",
                attachment_path=self.sample_dir / "figure" / "interoperability.png",
                comment="A sample figure",
                force=True,
            )

    def test_synchronize(self) -> None:
        with ConfluenceAPI() as api:
            Application(api, ConfluenceDocumentOptions()).synchronize(
                self.sample_dir / "index.md"
            )

    def test_synchronize_page(self) -> None:
        with ConfluenceAPI() as api:
            Application(api, ConfluenceDocumentOptions()).synchronize_page(
                self.sample_dir / "index.md"
            )

    def test_synchronize_directory(self) -> None:
        with ConfluenceAPI() as api:
            Application(api, ConfluenceDocumentOptions()).synchronize_directory(
                self.sample_dir
            )

    def test_synchronize_create(self) -> None:
        "Creates a Confluence page hierarchy from a set of Markdown files."

        source_dir = self.out_dir / "markdown"

        documents: list[Path] = [
            source_dir / "index.md",
            source_dir / "doc1.md",
            source_dir / "doc2.md",
            source_dir / "nested" / "index.md",
            source_dir / "nested" / "doc3.md",
        ]

        for absolute_path in documents:
            os.makedirs(absolute_path.parent, exist_ok=True)
            relative_path = absolute_path.relative_to(source_dir).as_posix()
            unique_string = f"md2conf/{relative_path}"
            document_title = hashlib.sha1(unique_string.encode("ascii")).hexdigest()
            with open(absolute_path, "w", encoding="utf-8") as f:
                f.write(
                    "\n".join(
                        [
                            "---",
                            f'title: "{document_title}"',
                            "---",
                            "",
                            f"# {absolute_path.name}: A sample document",
                            "",
                            "This is a document without an explicitly assigned Confluence page ID or space key.",
                        ]
                    )
                )

        with ConfluenceAPI() as api:
            Application(
                api,
                ConfluenceDocumentOptions(root_page_id=TEST_PAGE_ID),
            ).synchronize_directory(source_dir)

        with ConfluenceAPI() as api:
            for absolute_path in reversed(documents):
                id = read_qualified_id(absolute_path)
                self.assertIsNotNone(id)
                if id is None:
                    continue
                api.delete_page(id.page_id)


if __name__ == "__main__":
    unittest.main()
