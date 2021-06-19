#!/usr/bin/env python
# -*- coding: utf-8 -*-

import hashlib
from pathlib import Path
from typing import Union


def create_unique_logical_key(physical_key: Union[str, Path]) -> str:
    # Fully resolve the phyiscal key
    pk = Path(physical_key).expanduser().resolve(strict=True)

    # Creat short hash from fully resolved physical key
    short_hash = hashlib.sha256(str(pk).encode("utf-8")).hexdigest()

    # Return the unique logical key
    return f"{short_hash}_{pk.name}"
