# quilt3distribute

[![Build Status](https://github.com/AllenCellModeling/quilt3distribute/workflows/Build/badge.svg)](https://github.com/AllenCellModeling/quilt3distribute/actions)
[![Documentation](https://github.com/AllenCellModeling/quilt3distribute/workflows/Documentation/badge.svg)](https://AllenCellModeling.github.io/quilt3distribute)
[![Code Coverage](https://codecov.io/gh/AllenCellModeling/quilt3distribute/branch/master/graph/badge.svg)](https://codecov.io/gh/AllenCellModeling/quilt3distribute)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.3382259.svg)](https://doi.org/10.5281/zenodo.3382259)
<br>

![dataset packaging and distribution](http://www.allencell.org/uploads/8/1/9/9/81996008/published/automatingaccess-button-3_2.png?1549322257)

People commonly work with tabular datasets, people want to share their data, this makes that easier through Quilt3.

---

## Features
* Automatically determines which files to upload based off CSV headers. (Explicit override available)
* Simple interface for attaching metadata to each file based off the manifest contents.
* Groups metadata for files that are referenced multiple times.
* Validates and runs basic cleaning operations on your dataset manifest CSV.
* Optionally add license details and usage instructions to your dataset README.
* Parses README for any referenced files and packages them up as well.
* Support for adding extra files not contained in the manifest.
* Constructs an "associates" map that is placed into each files metadata for quick navigation around the package.
* Enforces that the metadata attached to each file is standardized across the package for each file column.

## Quick Start
Construct a csv (or pandas dataframe) dataset manifest ([Example](quilt3distribute/tests/data/example.csv)):

| CellId | Structure | 2dReadPath | 3dReadPath |
|--------|-----------|------------|------------|
| 1      | lysosome  | 2d/1.png   | 3d/1.tiff  |
| 2      | laminb1   | 2d/2.png   | 3d/2.tiff  |
| 3      | golgi     | 2d/3.png   | 3d/3.tiff  |
| 4      | myosin    | 2d/4.png   | 3d/4.tiff  |

```python
from quilt3distribute import Dataset

# Create the dataset
ds = Dataset(
    dataset="single_cell_examples.csv",
    name="single_cell_examples",
    package_owner="jacksonb",
    readme_path="single_cell_examples.md"
)

# Optionally add common additional requirements
ds.add_usage_doc("https://docs.quiltdata.com/walkthrough/reading-from-a-package")
ds.add_license("https://www.allencell.org/terms-of-use.html")

# Optionally indicate column values to use for file metadata
ds.set_metadata_columns(["CellId", "Structure"])

# Optionally rename the columns on the package level
ds.set_column_names_map({
    "2dReadPath": "images_2d",
    "3dReadPath": "images_3d"
})

# Distribute
pkg = ds.distribute(push_uri="s3://quilt-jacksonb", message="Initial dataset example")
```

***Returns:***
```
(remote Package)
 └─README.md
 └─images_2d
   └─03cdf019_1.png
   └─148ddc09_2.png
   └─2b2cf361_3.png
   └─312a0367_4.png
 └─images_3d
   └─a0ce6e01_1.tiff
   └─c360072c_2.tiff
   └─d9b55cba_3.tiff
   └─eb29e6b3_4.tiff
 └─metadata.csv
 └─referenced_files
   └─some_file_referenced_by_the_readme.png
```

***Example Metadata:***
```python
pkg["images_2d"]["03cdf019_1.png"].meta
```
```json
{
    "CellId": 1,
    "Structure": "lysosome",
    "associates": {
        "images_2d": "images_2d/03cdf019_1.png",
        "images_3d": "images_3d/a0ce6e01_1.tiff"
    }
}
```

## Installation
**Stable Release:** `pip install quilt3distribute`<br>
**Development Head:** `pip install git+https://github.com/AllenCellModeling/quilt3distribute.git`


### Credits

This package was created with Cookiecutter. [Original repository](https://github.com/audreyr/cookiecutter)


***Free software: Allen Institute Software License***
