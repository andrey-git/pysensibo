"""A setuptools based setup module."""

from setuptools import setup, find_packages

print(find_packages())
setup(
    name='pysensibo',
    version='1.0.0',
    description='asyncio-friendly python API for Sensibo',
    long_description='asyncio-friendly python API for Sensibo (https://sensibo.com). Requires Python 3.4+',
    url='https://github.com/andrey-git/pysensibo',
    license='MIT',
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    keywords='Sensibo',
    install_requires=['aiohttp'],
    packages=find_packages()
)
