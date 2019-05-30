# T4Distribute

[![build status](https://travis-ci.com/AllenCellModeling/t4distribute.svg?branch=master)](https://travis-ci.com/AllenCellModeling/t4distribute)
[![codecov](https://codecov.io/gh/AllenCellModeling/t4distribute/branch/master/graph/badge.svg)](https://codecov.io/gh/AllenCellModeling/t4distribute)


![dataset packaging and distribution](http://www.allencell.org/uploads/8/1/9/9/81996008/published/automatingaccess-button-3_2.png?1549322257)

A small wrapper around Quilt 3/ T4 to make dataset distribution even easier while enforcing some basic standards.

---

## Features
* Automatically determines which files to upload based off csv headers. (Explicit override available)
* Simple interface for attaching metadata to each file based off the manifest contents.
* Validates and runs basic cleaning operations on your features and metadata csv.
* Optionally add license details and usage instructions to your dataset README.
* Parses README for any referenced files and packages them up as well. (Please use full paths)

## Quick Start
Construct a csv (or pandas dataframe) dataset manifest ([Example](t4distribute/tests/data/example.csv)):

| CellId | Structure | 2dReadPath | 3dReadPath |
|--------|-----------|------------|------------|
| 1      | lysosome  | 2d/1.png   | 3d/1.tiff  |
| 2      | laminb1   | 2d/2.png   | 3d/2.tiff  |
| 3      | golgi     | 2d/3.png   | 3d/3.tiff  |
| 4      | myosin    | 2d/4.png   | 3d/4.tiff  |

Using the bin script offers easy dataset distribution, simply provide (in order):

1. The filepath to the csv dataset manifest
2. A name for the dataset
3. The owner of the dataset (which account to place it in on Quilt)
4. The filepath to a markdown readme for the dataset
5. The S3 bucket URI you want to push the dataset to.

If you don't know the details for items 3 or 5, talk to your Quilt account admin for help.

`t4_distribute_dataset my_dataset.csv test_dataset jacksonb readme.md s3://quilt-jacksonb`

Use `t4_distribute_dataset -h` to bring up more details about each parameter and all the options available.

If you want more iterative control over how the dataset is created import the package in python:
```python
from t4distribute import Dataset

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
ds.index_on_columns(["Structure"])

# Distribute
pkg = ds.distribute(push_uri="s3://quilt-jacksonb", message="Initial dataset example")
```

## Installation
Pypi installation not available at this time, please install using git.

`pip install git+https://github.com/AllenCellModeling/t4distribute.git`


### Credits

This package was created with Cookiecutter. [Original repository](https://github.com/audreyr/cookiecutter)


***Free software: Allen Institute Software License***
