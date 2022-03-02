"""A setuptools based setup module."""

from setuptools import setup, find_packages

print(find_packages())
setup(
    name='pysensibo',
    version='1.0.8',
    description='asyncio-friendly python API for Sensibo',
    long_description='asyncio-friendly python API for Sensibo'
                     '(https://sensibo.com). Requires Python 3.4+',
    url='https://github.com/andrey-git/pysensibo',
    license='MIT',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    keywords='Sensibo',
    install_requires=['aiohttp'],
    zip_safe=True,
    author='andrey-git',
    author_email='andrey-git@users.noreply.github.com',
    packages=find_packages()
)
