#!/usr/bin/env python3
from setuptools import setup
from icnsutil import __doc__, __version__

with open('README.md') as fp:
    longdesc = fp.read()

setup(
    name='icnsutil',
    description=__doc__.strip(),
    version=__version__,
    author='relikd',
    url='https://github.com/relikd/icnsutil',
    license='MIT',
    packages=['icnsutil'],
    entry_points={
        'console_scripts': [
            'icnsutil=icnsutil.cli:main'
        ]
    },
    extras_require={
        'convert': ['Pillow'],
    },
    long_description_content_type="text/markdown",
    long_description=longdesc,
    python_requires='>=3.5',
    keywords=[
        'icns',
        'icon',
        'extract',
        'compose',
        'create',
    ],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Environment :: MacOS X',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Topic :: Desktop Environment',
        'Topic :: Multimedia :: Graphics :: Graphics Conversion',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Utilities',
    ],
)
