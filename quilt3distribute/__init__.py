# -*- coding: utf-8 -*-

"""Top-level package for quilt3distribute."""

__author__ = 'Jackson Maxfield Brown'
__email__ = 'jacksonb@alleninstitute.org'
__version__ = '0.1.0'


def get_module_version():
    return __version__


from .dataset import Dataset  # noqa: F401
from .validation import FeatureDefinition  # noqa: F401
