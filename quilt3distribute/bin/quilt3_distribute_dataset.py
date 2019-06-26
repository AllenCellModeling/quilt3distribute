#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import logging
import sys
import traceback
from pathlib import Path

from quilt3distribute import Dataset

###############################################################################

log = logging.getLogger()
logging.basicConfig(level=logging.INFO,
                    format='[%(levelname)4s:%(lineno)4s %(asctime)s] %(message)s')

###############################################################################


class Args(argparse.Namespace):

    def __init__(self):
        self.__parse()

    def __parse(self):
        p = argparse.ArgumentParser(prog='quilt3_distribute_dataset',
                                    description=('A wrapper around quilt3 package distribution to make it even easier. '
                                                 'As default, this will attempt to do basic data cleaning tasks '
                                                 'and additionally, attempts to guess which file should be sent '
                                                 'out with the package. Lastly, will parse the provided README for '
                                                 'any referenced files and will package those them up as well so that '
                                                 'the README will be properly rendered on the quiltdata catalog.'))
        p.add_argument('dataset_path', action='store', type=Path,
                       help='Filepath to a csv dataset to distribute.')
        p.add_argument('dataset_name', action='store',
                       help=('A name for the dataset. May only include lowercase alphanumeric, '
                             'underscore, and hyphen characters.'))
        p.add_argument('package_owner', action='store',
                       help='The name of the dataset owner. This will be attached to the name. Example: "aics"')
        p.add_argument('readme_path', action='store', type=Path,
                       help='Filepath to a markdown readme for the dataset.')
        p.add_argument('push_uri', action='store',
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
                             'Example: "quilt3_distribute_dataset ... -i drug_name structure_name ..."'))
        p.add_argument('-f', '--fc', '--file-columns', action='store', nargs='+', dest='path_columns', default=None,
                       help=('List of columns that contains filepaths to be sent out in the package. '
                             'Example: '
                             '"quilt3_distribute_dataset ... -p fov_read_path structure_segmentation_path ..."'))
        p.add_argument('--debug', action='store_true', dest='debug', help=argparse.SUPPRESS)
        p.parse_args(namespace=self)


###############################################################################

def main():
    try:
        args = Args()

        # Create dataset
        ds = Dataset(
            dataset=args.dataset_path,
            name=args.dataset_name,
            package_owner=args.package_owner,
            readme_path=args.readme_path
        )

        # Handle optional provided
        if args.usage_doc_or_link:
            ds.add_usage_doc(args.usage_doc_or_link)
        if args.license_doc_or_link:
            ds.add_license(args.license_doc_or_link)
        if args.index_columns:
            ds.set_index_columns(args.index_columns)
        if args.path_columns:
            ds.set_path_columns(args.path_columns)

        # Distribute
        pkg = ds.distribute(push_uri=args.push_uri, message=args.message)
        log.info(
            f"Completed distribution. "
            f"Package [name: '{args.package_owner}/{args.dataset_name}', version: {pkg.top_hash}]"
        )

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
