#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re
from pathlib import Path
from typing import List, NamedTuple, Optional, Union

from markdown2 import markdown

###############################################################################

log = logging.getLogger(__name__)

###############################################################################


class ReferencedFiles(NamedTuple):
    target: str
    resolved: Path


class README(object):
    def __init__(self, fp: Union[str, Path]):
        """
        Initialize a README object.

        :param fp: Filepath to a markdown readme document.
        """
        # Check filepath
        fp = Path(fp).expanduser().resolve(strict=True)
        if fp.is_dir():
            raise IsADirectoryError(fp)

        # Store
        self._fp = fp

        # Lazy loaded
        self._text = None

    @property
    def fp(self) -> Path:
        return self._fp

    @property
    def referenced_files(self) -> List[Path]:
        # Find all link matches
        # Link matches look like the following in markdown
        # [hello world](https://allencell.org/myfile.png)
        # [hello world](../mydir/myfile.png)
        matches = re.findall(r"\[[^\]]*\]\([^\)]*\)", self.text)

        # Determine if the links are files or external references
        files = set()
        for match in matches:
            # Look for file...
            # This may look a bit odd but because links in markdown follow the []() structure as shown above
            # we need to first find the index of the ending bracket.
            # "But why not look for the first opening paranthesis?"
            # Because sweet summer child, you can use paranthesis inside the brackets like so: [()]()
            # Because of this we want to first find the ending bracket, then we know where the real link begins.
            # From there we will have just the () contents.
            # However, links can have alternate text that displays on hover in many markdown renderers.
            # To find the real link inside the link portion of the paranthesis we can split the string by spaces
            # and use the first component available.
            target = match[match.index("]") + 2: -1].split(" ")[0]

            # Check for common external
            if not any(sub in target.lower() for sub in ["https://", "http://", "s3://", "gs://"]) and target[0] != "#":
                # Check if it is a file
                resolved = Path(target).resolve()
                if resolved.is_file() or resolved.is_dir():
                    files.add(ReferencedFiles(target, resolved))
                else:
                    log.warn(f"Could not find file referenced in readme: {target}")

        return list(files)

    def append_readme_standards(
        self,
        usage_doc_or_link: Optional[Union[str, Path]] = None,
        license_doc_or_link: Optional[Union[str, Path]] = None
    ) -> str:
        """
        Attach a standard document or link to the readme. If the provided value is an external resource, a default
        message is attached before linking to the external resource. Additionally, updates the underlying text attribute
        for this object to retain prior document attachments.

        :param usage_doc_or_link: A document or link to external resource with details on dataset usage.
        :param license_doc_or_link: A document or link to external resource with details on licensing.
        :return: The entire contents of the readme returned as a string.
        """
        # Get current text if available
        if self._text:
            text = self._text
        # Read in the current readme otherwise
        else:
            with open(self.fp, "r") as readme:
                text = readme.read()

        # Add usage if provided
        if usage_doc_or_link:
            usage_doc_or_link = str(usage_doc_or_link)
            # Check if the usage doc is a link
            if any(sub in usage_doc_or_link.lower() for sub in ["https://", "http://", "s3://", "gs://"]):
                text += (
                    f"\n### Usage\nFor documenation on how to use and interact with this dataset please "
                    f"refer to [{usage_doc_or_link}]({usage_doc_or_link})."
                )

            # Append usage contents
            else:
                usage_doc_or_link = Path(usage_doc_or_link).expanduser().resolve(strict=True)
                with open(usage_doc_or_link, "r") as usage_doc:
                    text += f"\n{usage_doc.read()}"

        if license_doc_or_link:
            license_doc_or_link = str(license_doc_or_link)
            # Check if the license doc is a link
            if any(sub in license_doc_or_link.lower() for sub in ["https://", "http://", "s3://", "gs://"]):
                text += (
                    f"\n### License\nFor questions on licensing please "
                    f"refer to [{license_doc_or_link}]({license_doc_or_link})."
                )

            # Append license contents
            else:
                license_doc_or_link = Path(license_doc_or_link).expanduser().resolve(strict=True)
                with open(license_doc_or_link, "r") as license_doc:
                    text += f"\n{license_doc.read()}"

        # Store and return
        self._text = text
        return self._text

    @property
    def text(self) -> str:
        if self._text:
            return self._text

        return self.append_readme_standards()

    def __str__(self):
        return f"<README [file: {self.fp}]>"

    def __repr__(self):
        return str(self)

    def _repr_html_(self):
        return markdown(self.text)
