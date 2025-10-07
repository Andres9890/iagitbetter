#!/usr/bin/env python3
import os
import re

from setuptools import find_packages, setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


def get_version():
    init_path = os.path.join(os.path.dirname(__file__), "iagitbetter", "__init__.py")
    with open(init_path, "r") as f:
        content = f.read()
    version_match = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]', content, re.MULTILINE)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string")


setup(
    name="iagitbetter",
    version=get_version(),
    author="Andres99",
    description="Archiving any git repository to the Internet Archive",
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    url="https://github.com/Andres9890/iagitbetter",
    packages=find_packages(),
    license="GPL-3.0",
    keywords="git archive internet-archive github gitlab bitbucket repository self-hosted gitea forgejo",
    platforms="any",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Version Control :: Git",
        "Topic :: System :: Archiving",
    ],
    python_requires=">=3.9",
    entry_points={
        "console_scripts": [
            "iagitbetter=iagitbetter:main",
        ],
    },
    install_requires=[
        "requests>=2.32.5",
        "internetarchive>=5.5.1",
        "GitPython>=3.1.45",
        "markdown2>=2.5.4",
        "docutils>=0.22.2",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "black",
            "flake8",
        ],
    },
)
