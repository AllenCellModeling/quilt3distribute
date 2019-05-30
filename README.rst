============
T4Distribute
============

.. image:: https://travis-ci.com/AllenCellModeling/t4distribute.svg?branch=master
        :target: https://travis-ci.com/AllenCellModeling/t4distribute
        :alt: Build Status

.. image:: https://codecov.io/gh/AllenCellModeling/t4distribute/branch/master/graph/badge.svg
        :target: https://codecov.io/gh/AllenCellModeling/t4distribute
        :alt: Codecov Status


.. image:: http://www.allencell.org/uploads/8/1/9/9/81996008/published/automatingaccess-button-3_2.png?1549322257
        :alt: Dataset packaging and distribution

A small wrapper around Quilt 3/ T4 to make dataset distribution even easier while enforcing some basic standards.

Features
--------

* Attempts to determine which files to upload based off csv contents. (Explicit override available)
* Simple interface for attaching metadata to each file based off the manifest contents.
* Validates and runs basic cleaning operations on your features and metadata csv.
* Optionally add license details and usage instructions to your dataset README.
* Attempts to parse README for any referenced files and packages them up as well. (Please use full paths)

Quick Start
-----------
Construct a csv (or pandas dataframe) dataset manifest (Example_):

+-------------+-------------+-------------+-------------+
| CellId      | Structure   | 2dReadPath  | 3dReadPath  |
+=============+=============+=============+=============+
| 1           | lysosome    | /allen/...  | /allen/...  |
+-------------+-------------+-------------+-------------+
| 2           | laminb2     | /allen/...  | /allen/...  |
+-------------+-------------+-------------+-------------+
| 3           | golgi       | /allen/...  | /allen/...  |
+-------------+-------------+-------------+-------------+
| 4           | myosin      | /allen/...  | /allen/...  |
+-------------+-------------+-------------+-------------+

Using the bin script offers easy dataset distribution, simply provide (in order):

1. The filepath to the csv dataset manifest
2. A name for the dataset
3. The owner of the dataset (which account to place it in on Quilt)
4. The filepath to a markdown readme for the dataset
5. The S3 bucket URI you want to push the dataset to.

If you don't know the details for #3 or #5, talk to your Quilt account admin for help.

```bash
t4_distribute_dataset my_dataset.csv test_dataset jacksonb readme.md s3://quilt-jacksonb
```

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


.. _Example: t4distribute/tests/data/example.csv

To simply get data

Installation
------------

* pypi releases: `pip install t4distribute`
* master branch: `pip install git+https://github.com/AllenCellModeling/t4distribute.git`



Free software: Allen Institute Software License


Credits
-------

This package was created with Cookiecutter_.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
