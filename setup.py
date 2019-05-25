#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

test_requirements = [
    'codecov',
    'flake8',
    'pytest',
    'pytest-cov',
    'pytest-raises',
]

setup_requirements = ['pytest-runner', ]

dev_requirements = [
    'bumpversion>=0.5.3',
    'wheel>=0.33.1',
    'flake8>=3.7.7',
    'tox>=3.5.2',
    'coverage>=5.0a4',
    'Sphinx>=2.0.0b1',
    'twine>=1.13.0',
    'pytest>=4.3.0',
    'pytest-cov==2.6.1',
    'pytest-raises>=0.10',
    'pytest-runner>=4.4',
]

interactive_requirements = [
    'altair',
    'jupyterlab',
    'matplotlib',
]

requirements = [
    'markdown2==2.3.7',
    'pandas',
    't4==0.1.3',
    'tabulate==0.8.3',
    'tqdm==4.32.1',
]

extra_requirements = {
    'test': test_requirements,
    'setup': setup_requirements,
    'dev': dev_requirements,
    'interactive': interactive_requirements,
    'all': [
        *requirements,
        *test_requirements,
        *setup_requirements,
        *dev_requirements,
        *interactive_requirements
    ]
}

setup(
    author="Jackson Maxfield Brown",
    author_email='jacksonb@alleninstitute.org',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: Allen Institute Software License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    description="A small wrapper around T4 to make dataset distribution even easier.",
    entry_points={
        'console_scripts': [
            # 'my_example=t4distribute.bin.my_example:main'
        ],
    },
    install_requires=requirements,
    license="Allen Institute Software License",
    long_description=readme + '\n\n' + history,
    include_package_data=True,
    keywords='t4distribute',
    name='t4distribute',
    packages=find_packages(),
    python_requires=">=3.6",
    setup_requires=setup_requirements,
    test_suite='t4distribute/tests',
    tests_require=test_requirements,
    extras_require=extra_requirements,
    url='https://github.com/AllenCellModeling/t4distribute',
    version='0.1.0',
    zip_safe=False,
)
