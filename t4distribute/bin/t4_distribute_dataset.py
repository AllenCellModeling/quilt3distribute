#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This sample script will get deployed in the bin directory of the
users' virtualenv when the parent module is installed using pip.
"""

import sys
import argparse
import logging
from pathlib import Path
import traceback

from t4distribute import Dataset

###############################################################################

log = logging.getLogger()
logging.basicConfig(level=logging.INFO,
                    format='[%(levelname)4s:%(lineno)4s %(asctime)s] %(message)s')

###############################################################################


class Args(argparse.Namespace):

    def __init__(self):
        self.__parse()

    def __parse(self):
        p = argparse.ArgumentParser(prog='t4_distribute_dataset',
                                    description=('A wrapper around t4 package distribution to make it even easier. '
                                                 'As default, this will attempt to do basic data cleaning tasks '
                                                 'and additionally, attempts to guess which file should be sent '
                                                 'out with the package. Lastly, will parse the provided README for '
                                                 'any referenced files and will package those them up as well so that '
                                                 'the README will be properly rendered on the quiltdata catalog.'))
        p.add_argument('dataset_path', action='store', dest='dataset', type=Path,
                       help='Filepath to a csv dataset to distribute.')
        p.add_argument('name', action='store', dest='name',
                       help='A name for the dataset. May only include alphabetic and underscore characters.')
        p.add_argument('package_owner', action='store', dest='owner',
                       help='The name of the dataset owner. This will be attached to the name. Example: "aics"')
        p.add_argument('readme_path', action='store', dest='readme_path', type=Path,
                       help='Filepath to a markdown readme for the dataset.')
        p.add_argument('build_location', action='store', dest='build_location', type=Path,
                       help='A filepath for where the package manifest should be stored locally.')
        p.add_argument('-p', '--push-location', action='store', dest='push_location', default=None,
                       help='The S3 bucket URI you want to push to. Talk to your Quilt admin for details and support.')
        p.add_argument('-m', '--message', action='store', dest='message', default=None,
                       help='A message to attach to the built/ released dataset version.')
        p.add_argument('-u', '--usage-doc', action='store', dest='usage_doc_or_link', default=None,
                       help=('Filepath or URL for dataset usage details/ instructions. '
                             'If your README already includes usage details, this can be ignored.'))
        p.add_argument('-l', '--license', action='store', dest='license_doc_or_link', default=None,
                       help=('Filepath or URL for dataset license details. '
                             'If your README already includes license details, this can be ignored.'))
        p.add_argument('-i', '--ic', '--index-columns', action='store', nargs='+', dest='index_columns', default=None,
                       help=('List of columns to use for metadata attachment. '
                             'The values in each row for the columns provided will be attached as metadata, '
                             'meaning, users will be able to search and filter the files sent using that metadata. '
                             'Example: "t4_distribute_dataset ... -i drug_name structure_name ..."'))
        p.add_argument('-f', '--fc', '--file-columns', action='store', nargs='+', dest='path_columns', default=None,
                       help=('List of columns that contains filepaths to be sent out in the package. '
                             'Example: "t4_distribute_dataset ... -p fov_read_path structure_segmentation_path ..."'))
        p.add_argument('--debug', action='store_true', dest='debug', help=argparse.SUPPRESS)
        p.parse_args(namespace=self)


###############################################################################

def main():
    try:
        args = Args()

        # Create dataset
        ds = Dataset(dataset=args.dataset, name=args.name, package_owner=args.owner, eadme_path=args.readme_path)

        # Handle optional provided
        if args.usage_doc_or_link:
            ds.add_usage_doc(args.usage_doc_or_link)
        if args.license_doc_or_link:
            ds.add_license(args.license_doc_or_link)
        if args.index_columns:
            ds.index_on_columns(args.index_columns)
        if args.path_columns:
            ds.set_path_columns(args.path_columns)

        # Distribute
        pkg = ds.distribute(build_location=args.build_location, push_location=args.push_location, message=args.message)
        log.info(f"Completed distribution. Package [name: '{args.owner}/{args.name}', version: {pkg.top_hash}]")

    except Exception as e:
        log.error("=============================================")
        if args.debug:
            log.error("\n\n" + traceback.format_exc())
            log.error("=============================================")
        log.error("\n\n" + str(e) + "\n")
        log.error("=============================================")
        sys.exit(1)


###############################################################################
# Allow caller to directly run this module (usually in development scenarios)

if __name__ == '__main__':
    main()