#!/usr/bin/env python3
import os
from setuptools import setup, find_packages

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name='iagitbetter',
    version='1.0.0',
    author='Andres99',
    description='Archiving any git repository to the Internet Archive',
    long_description=read('README.md'),
    long_description_content_type='text/markdown',
    url='https://github.com/Andres9890/iagitbetter',
    packages=find_packages(),
    license='GPL-3.0',
    keywords='git archive internet-archive github gitlab bitbucket repository backup',
    platforms='any',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Software Development :: Version Control :: Git',
        'Topic :: System :: Archiving',
    ],
    python_requires='>=3.9',
    entry_points={
        'console_scripts': [
            'iagitbetter=iagitbetter:main',
        ],
    },
    install_requires=[
        'requests>=2.32.5',
        'internetarchive>=5.5.1',
        'GitPython>=3.1.45',
        'markdown2>=2.5.4',
    ],
    extras_require={
        'dev': [
            'pytest>=6.0',
            'black',
            'flake8',
        ],
    },
)