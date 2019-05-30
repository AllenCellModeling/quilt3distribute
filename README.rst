============
T4Distribute
============

.. image:: https://travis-ci.com/AllenCellModeling/t4distribute.svg?branch=master
        :target: https://travis-ci.com/AllenCellModeling/t4distribute
        :alt: Build Status

.. image:: https://codecov.io/gh/AllenCellModeling/t4distribute/branch/master/graph/badge.svg
        :target: https://codecov.io/gh/AllenCellModeling/t4distribute
        :alt: Codecov Status


A small wrapper around Quilt 3/ T4 to make dataset distribution even easier.

Quick Start
-----------




* Free software: Allen Institute Software License


Features
--------

* Automatically adds license details and bare minimum T4 usage instructions to your dataset README.
* Attempts to determine which files to upload based off csv contents. (Explicit override available)
* Validates and runs basic cleaning operations on your features and/ or metadata csv.
* Attempts to parse README for any referenced files and packages them up as well.


Credits
-------

This package was created with Cookiecutter_.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
