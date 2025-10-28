"""
StratVal Package Setup
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="stratval",
    version="1.0.0",
    author="Quantitative Trading Team",
    author_email="team@quant-trading.com",
    description="AI-powered trading strategy validation system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/VontariusF/testing-and-tuning-market-trading-systems",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Office/Business :: Financial",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires='>=3.8',
    install_requires=[
        "psycopg2-binary>=2.9.0",
        "numpy>=1.21.0",
    ],
    entry_points={
        'console_scripts': [
            'stratval=stratval.cli.stratval:main',
        ],
    },
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'black>=23.0.0',
            'flake8>=6.0.0',
        ],
    },
)
