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
    parser = argparse.ArgumentParser(
            description=DESCRIPTION,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--all', action='store_true',
            help='Run all tests instead of matching pattern.')
    parser.add_argument('pattern', nargs='*',
            help=('pattern(s) to match against, eg. "buildings" or '
                '"architect.TestArchitect.test_lead_architect".'))
    parser.add_argument('-v', '--verbose', action='store_true',
            help='Use verbose test result reporting.')
    parser.add_argument('-q', '--quiet', action='store_true',
            help=('Suppress individual test result reporting. Still reports '
                  'summary information. Overrides --verbose.'))
    parser.add_argument('--log-level', default='WARNING',
            help=('Set app log level during tests. Valid arguments are: '
                  'DEBUG, INFO, WARNING, ERROR, CRITICAL. See logging module '
                  'documentation.'))
    args = parser.parse_args()

    setup_logging()

    numeric_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: {0!s}'.format(args.log_level))

    # This catches the children loggers like cloaca.game
    logging.getLogger('cloaca').setLevel(numeric_level)

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
    
    # TextTestRunner takes verbosity that can be 0 (quiet), 1 (default),
    # or 2 (verbose). Quiet overrides verbose.
    if args.quiet:
        verbosity = 0
    elif args.verbose:
        verbosity = 2
    else:
        verbosity=1

    test_runner = unittest.TextTestRunner(verbosity=verbosity).run(test_suite)

if __name__ == '__main__':
    main()
