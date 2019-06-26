#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################

# Use this file to generate the fake data files used for testing

###############################################################################

import json
import random
from pathlib import Path

import numpy as np
import pandas as pd
import tifffile

###############################################################################


BASE_PATH = Path(__file__).parent


def main():
    # Create fake unique dataset
    rows = []
    for i in range(1, 10):
        # Generate random features
        meta = {
            "nuc_volume": random.random() * 5,
            "cell_volume": random.random() * 40 + 5,
        }

        # Save random features
        meta_path = (BASE_PATH / "fake_metadata_files" / f"{i}.json").resolve()
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        with open(meta_path, "w") as write_out:
            json.dump(meta, write_out)

        # Generate and write random tiffs
        # This is 1/10 of our normal image size
        # Also our normal images are uint16, making these uint8 to again reduce size
        three_d = np.random.rand(7, 62, 92)
        three_d *= 255
        three_d = three_d.astype(np.uint8)

        # Save 3d
        three_d_path = (BASE_PATH / "fake_images" / "3d" / f"{i}.tiff").resolve()
        three_d_path.parent.mkdir(parents=True, exist_ok=True)
        tifffile.imsave(three_d_path, three_d)

        # Max project to 2d
        two_d = three_d.max(0)
        two_d_path = (BASE_PATH / "fake_images" / "2d" / f"{i}.tiff").resolve()
        two_d_path.parent.mkdir(parents=True, exist_ok=True)
        tifffile.imsave(two_d_path, two_d)

        # Write row
        rows.append({
            "CellId": i,
            "Structure": "Fake Data",
            "3dReadPath": three_d_path,
            "2dReadPath": two_d_path,
            "MetadataReadPath": meta_path
        })

    # Create fake manifest (dataset)
    data = pd.DataFrame(rows)
    data.to_csv((BASE_PATH / "example.csv"), index=False)

    ###############################################################################

    # Create fake repeated dataset
    cell_ids = [i for i in range(1, 10)]
    source_read_paths_1 = [(BASE_PATH / "fake_images" / "3d" / "1.tiff").resolve() for i in range(4)]
    source_read_paths_2 = [(BASE_PATH / "fake_images" / "3d" / "2.tiff").resolve() for i in range(3)]
    source_read_paths_3 = [(BASE_PATH / "fake_images" / "3d" / "3.tiff").resolve() for i in range(2)]
    source_read_paths = [*source_read_paths_1, *source_read_paths_2, *source_read_paths_3]
    structures_1 = ["lamin"] * 4
    structures_2 = ["mito"] * 3
    structures_3 = ["pax"] * 2
    structures = [*structures_1, *structures_2, *structures_3]

    data = pd.DataFrame({"CellId": cell_ids, "SourceReadPath": source_read_paths, "Structure": structures})
    data.to_csv((BASE_PATH / "repeated_values_example.csv"), index=False)

    ###############################################################################

    # Create same filenames dataset
    three_d_paths = [(BASE_PATH / "fake_images" / "3d" / f"{i}.tiff").resolve() for i in range(1, 10)]
    two_d_paths = [(BASE_PATH / "fake_images" / "2d" / f"{i}.tiff").resolve() for i in range(1, 10)]
    paths = [*three_d_paths, *two_d_paths]

    data = pd.DataFrame({"SourceReadPath": paths})
    data.to_csv((BASE_PATH / "same_filenames_example.csv"), index=False)

###############################################################################
# Allow caller to directly run this module (usually in development scenarios)


if __name__ == '__main__':
    main()
