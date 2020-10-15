#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import setuptools


try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


with open('README.md') as readme_file:
    readme = readme_file.read()

tag = ""

try:
    tag = os.popen("git describe --tag")._stream.read().strip()
except:
    tag = "develpment"

requirements = [
]

test_requirements = [
    # TODO: put package test requirements here
]

setup(
    name='svg2mod',
    version=tag,
    description="Convert an SVG file to a KiCad footprint.",
    long_description_content_type='text/markdown',
    long_description=readme,
    author='https://github.com/svg2mod',
    author_email='',
    url='https://github.com/svg2mod/svg2mod',
    packages=setuptools.find_packages(),
    entry_points={'console_scripts':['svg2mod = svg2mod.svg2mod:main']},
    package_dir={'svg2mod':'svg2mod'},
    include_package_data=True,
    package_data={'kipart': ['*.gif', '*.png']},
    scripts=[],
    install_requires=requirements,
    license="CC0-1.0",
    zip_safe=False,
    keywords='svg2mod, KiCAD',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'License :: CC0 1.0 Universal (CC0 1.0) Public Domain Dedication',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
    ],
    test_suite='tests',
    tests_require=test_requirements
)
