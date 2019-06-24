#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytest

from quilt3distribute.documentation import README


@pytest.fixture
def example_markdown_path(data_dir):
    return data_dir / "README.md"


@pytest.fixture
def example_readme(example_markdown_path):
    return README(example_markdown_path)


@pytest.mark.parametrize("usage_doc_or_link, license_doc_or_link", [
    (None, None),
    ("https://docs.quiltdata.com", None),
    (None, "https://www.allencell.org/terms-of-use.html"),
    ("https://docs.quiltdata.com", "https://www.allencell.org/terms-of-use.html")
])
def test_append_readme_standards_usage_links(example_readme, usage_doc_or_link, license_doc_or_link):
    example_readme.append_readme_standards(usage_doc_or_link, license_doc_or_link)


def test_append_readme_standards_usage_files(example_readme, example_markdown_path):
    example_readme.append_readme_standards(example_markdown_path)
    example_readme.append_readme_standards(license_doc_or_link=example_markdown_path)
    example_readme.append_readme_standards(example_markdown_path, example_markdown_path)
