"""A setuptools based setup module."""

from setuptools import setup, find_packages

print(find_packages())
setup(
    name="pysensibo",
    version="1.0.23",
    description="asyncio-friendly python API for Sensibo",
    long_description="asyncio-friendly python API for Sensibo"
    "(https://sensibo.com). Requires Python 3.9+",
    url="https://github.com/andrey-git/pysensibo",
    license="MIT",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    keywords="Sensibo",
    install_requires=["aiohttp"],
    zip_safe=False,
    author="andrey-git",
    author_email="andrey-git@users.noreply.github.com",
    packages=find_packages(),
    package_data={"pysensibo": ["py.typed"]},
)
