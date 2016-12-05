#!/usr/bin/env python

import unittest
import logging
import logging.config
import sys
import argparse

DESCRIPTION="""
Harness for tests in the cloaca/tests/ directory.
Run all tests with '--all' or provide a list dotted names
of specific tests (eg. legionary.TestLegionary.test_legionary).
"""

# Set up logging. See logging.json for config
def setup_logging(
        default_path='test_logging.json',
        default_level=logging.INFO):
    """Setup logging configuration
    """
    import sys, os, json

    path = default_path
    if os.path.exists(path):
        with open(path, 'rt') as f:
            config = json.load(f)
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=default_level)


def main():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument('--all', action='store_true',
            help='Run all tests.')
    parser.add_argument('pattern', nargs='*',
            help=('pattern(s) to match against, eg. "buildings" or '
                '"architect.TestArchitect.test_lead_architect".'))
    parser.add_argument('--verbose', action='store_true',
            help='Enable INFO/DEBUG logging output.')
    args = parser.parse_args()

    setup_logging()

    if args.verbose:
        # This catches the children loggers like cloaca.game
        logging.getLogger('cloaca').setLevel(logging.DEBUG)

    loader = unittest.defaultTestLoader

    if args.all:
        sys.stderr.write('Running all tests.\n')
        suites = loader.discover('.', pattern='*.py')

    else:
        if len(args.pattern) == 0:
            sys.stderr.write('ERROR: No tests specified.\n\n')
            parser.print_help(file=sys.stderr)
            return

        sys.stderr.write('Running all tests matching the patterns ('
                + ', '.join(args.pattern) + ')\n')
        suites = loader.loadTestsFromNames(args.pattern)

    test_suite = unittest.TestSuite(suites)
    test_runner = unittest.TextTestRunner().run(test_suite)

if __name__ == '__main__':
    main()
