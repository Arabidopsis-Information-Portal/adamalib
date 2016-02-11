#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from setuptools import setup
from setuptools.command.test import test as TestCommand

import os
import sys


class PyTest(TestCommand):

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = ['--ignore', 'build']
        self.test_suite = True

    def run_tests(self):
        import pytest
        errcode = pytest.main(self.test_args)
        sys.exit(errcode)


if sys.argv[-1] == 'publish':
    os.system('python setup.py sdist upload')
    sys.exit()

readme = open('README.rst').read()

setup(
    author='John Gentle',
    author_email='jgentle@tacc.utexas.edu',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
    ],
    cmdclass={'test': PyTest},
    description='Adama library',
    include_package_data=True,
    install_requires=[
    ],
    keywords='adamalib',
    license="BSD",
    long_description=readme,
    name='adamalib',
    packages=[
        'adamalib',
    ],
    package_dir={'adamalib': 'adamalib'},
    tests_require=['pytest'],
    test_suite='tests',
    url='https://github.com/Arabidopsis-Information-Portal/adamalib',
    version='0.1.0',
    zip_safe=False,
)
