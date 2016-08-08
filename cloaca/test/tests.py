#!/usr/bin/env python

import unittest
import logging
import logging.config
import sys

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


def main(pattern_):
    setup_logging()

    print 'Testing only files matching : \''+str(pattern_)+'\''

    loader = unittest.defaultTestLoader
    suites = loader.discover('.', pattern=pattern_)
    test_suite = unittest.TestSuite(suites)
    test_runner = unittest.TextTestRunner().run(test_suite)

if __name__ == '__main__':
    try:
        pattern = sys.argv[1]
    except IndexError:
        pattern = '*.py'

    main(pattern)
