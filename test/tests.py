#!/usr/bin/env python

import unittest
import logging
import logging.config

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
    setup_logging()

    loader = unittest.defaultTestLoader
    suites = loader.discover('.', pattern='*.py')
    test_suite = unittest.TestSuite(suites)
    test_runner = unittest.TextTestRunner().run(test_suite)

if __name__ == '__main__':
    main()
