#!/usr/bin/env python

from setuptools import setup
import foo
import glob
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(current_dir, 'README.rst')) as fp:
    long_description = fp.read()

install_requires = []
try:
    import argparse
except ImportError:
    install_requires.append('argparse')


setup(
    name='foo-tools',
    version=foo.__version__,
    license=foo.__license__,
    description=foo.__description__,
    long_description=long_description,
    author=foo.__author__,
    author_email=foo.__email__,
    url=foo.__url__,
    py_modules=['foo'],
    install_requires=install_requires,
    tests_require=['mock'],
    test_suite='test_foo',
    data_files=[('libexec/foo-tools', glob.glob('modules/*'))],
    zip_safe=False,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Unix Shell',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: System',
    ],
    entry_points={'console_scripts': ['foo = foo:main']},
)
