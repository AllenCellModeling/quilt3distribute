# quilt3distribute

[![build status](https://travis-ci.com/AllenCellModeling/quilt3distribute.svg?branch=master)](https://travis-ci.com/AllenCellModeling/quilt3distribute)
[![codecov](https://codecov.io/gh/AllenCellModeling/quilt3distribute/branch/master/graph/badge.svg)](https://codecov.io/gh/AllenCellModeling/quilt3distribute)


![dataset packaging and distribution](http://www.allencell.org/uploads/8/1/9/9/81996008/published/automatingaccess-button-3_2.png?1549322257)

People commonly work with tabular datasets, people want to share their data, this makes that easier through Quilt3.

---

## Features
* Automatically determines which files to upload based off csv headers. (Explicit override available)
* Simple interface for attaching metadata to each file based off the manifest contents.
* Groups metadata for files that are referenced multiple times.
* Validates and runs basic cleaning operations on your dataset manifest csv.
* Optionally add license details and usage instructions to your dataset README.
* Parses README for any referenced files and packages them up as well. (Please use full paths)
* Support for adding extra files not contained in the manifest.

## Quick Start
Construct a csv (or pandas dataframe) dataset manifest ([Example](quilt3distribute/tests/data/example.csv)):

| CellId | Structure | 2dReadPath | 3dReadPath |
|--------|-----------|------------|------------|
| 1      | lysosome  | 2d/1.png   | 3d/1.tiff  |
| 2      | laminb1   | 2d/2.png   | 3d/2.tiff  |
| 3      | golgi     | 2d/3.png   | 3d/3.tiff  |
| 4      | myosin    | 2d/4.png   | 3d/4.tiff  |

***Python:***
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
ds.set_index_columns(["Structure"])

# Distribute
pkg = ds.distribute(push_uri="s3://quilt-jacksonb", message="Initial dataset example")
```

***Bin Script:***

Using the bin script offers easy dataset distribution, simply provide (in order):

1. The filepath to the csv dataset manifest
2. A name for the dataset
3. The owner of the dataset (which account to place it in on Quilt)
4. The filepath to a markdown readme for the dataset
5. The S3 bucket URI you want to push the dataset to.

Layout:<br>
`quilt3_distribute_dataset {dataset_path} {dataset_name} {dataset_owner} {readme_path} {s3_uri}`

Filled:<br>
`quilt3_distribute_dataset single_cell_examples.csv single_cell_examples jacksonb single_cell_examples.md s3://quilt-jacksonb`

Use `quilt3_distribute_dataset -h` to bring up more details about each parameter and all the options available.
If you don't know the details for items 3 or 5, talk to your Quilt account admin for help.

***index columns:***

A note on the bin script parameter and the Python dataset function `set_index_columns`:<br>
Using the small example dataframe above as an example, if we provided `["Structure"]` as the list of columns to index
on in Python (using the bin script this would be `-i "Structure"`). `{"Structure": "lysosome"}` gets added as metadata
for both `2d/1.png` and `3d/1.tiff` files; `{"Structure": "laminb1"}` gets added as metadata for both `2d/2.png` and
`3d/2.tiff` files; etc.

In short: the values in each column provided will be used for metadata attachment for every file found.

## Installation
PyPI installation not available at this time, please install using git.

`pip install git+https://github.com/AllenCellModeling/quilt3distribute.git`


### Credits

This package was created with Cookiecutter. [Original repository](https://github.com/audreyr/cookiecutter)


***Free software: Allen Institute Software License***
