#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import find_packages, setup

with open("README.md") as readme_file:
    readme = readme_file.read()

test_requirements = [
    "codecov",
    "flake8",
    "numpy",
    "pytest",
    "pytest-cov",
    "pytest-raises",
    "tifffile==0.15.1",
]

setup_requirements = ["pytest-runner", ]

dev_requirements = [
    "bumpversion>=0.5.3",
    "wheel>=0.33.1",
    "flake8>=3.7.7",
    "tox>=3.5.2",
    "coverage>=5.0a4",
    "Sphinx>=2.0.0b1",
    "twine>=1.13.0",
    "pytest>=4.3.0",
    "pytest-cov==2.6.1",
    "pytest-raises>=0.10",
    "pytest-runner>=4.4",
]

interactive_requirements = [
    "altair",
    "jupyterlab",
    "matplotlib",
]

requirements = [
    "markdown2==2.3.7",
    "pandas",
    "quilt3>=3.0.4",
    "tabulate==0.8.3",
    "tqdm==4.32.1",
]

extra_requirements = {
    "test": test_requirements,
    "setup": setup_requirements,
    "dev": dev_requirements,
    "interactive": interactive_requirements,
    "all": [
        *requirements,
        *test_requirements,
        *setup_requirements,
        *dev_requirements,
        *interactive_requirements
    ]
}

setup(
    author="Jackson Maxfield Brown",
    author_email="jacksonb@alleninstitute.org",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: Allen Institute Software License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
    description="A small wrapper around Quilt3 to make dataset distribution even easier.",
    entry_points={
        "console_scripts": [
            "quilt3_distribute_dataset=quilt3distribute.bin.quilt3_distribute_dataset:main"
        ],
    },
    install_requires=requirements,
    license="Allen Institute Software License",
    long_description=readme,
    include_package_data=True,
    keywords="quilt3distribute",
    name="quilt3distribute",
    packages=find_packages(exclude=["tests", "*.tests", "*.tests.*"]),
    python_requires=">=3.6",
    setup_requires=setup_requirements,
    test_suite="quilt3distribute/tests",
    tests_require=test_requirements,
    extras_require=extra_requirements,
    url="https://github.com/AllenCellModeling/quilt3distribute",
    version="0.1.0",
    zip_safe=False,
)
