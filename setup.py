"""Legacy setup.py kept for compatibility with tooling that expects it.

Primary build configuration lives in pyproject.toml. This file only delegates
to setuptools.setup when invoked directly. Version is synchronized manually.
"""

from setuptools import find_packages, setup

with open("README.md", encoding="utf-8") as fh:  # mode arg optional (ruff UP015)
    long_description = fh.read()

DESCRIPTION = (
    "Open-source population health & nutrition analytics toolkit "
    "(current focus: NHANES)"
)

setup(
    name="pophealth-observatory",
    version="0.2.0",  # keep in sync with pyproject.toml
    author="PopHealth Observatory Team",
    author_email="your.email@example.com",
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/paulboys/PopHealth-Observatory",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "pandas>=1.3.0",
        "numpy>=1.20.0",
        "requests>=2.25.0",
        "matplotlib>=3.4.0",
        "seaborn>=0.11.0",
        "plotly>=5.3.0",
        "ipywidgets>=7.6.0",
    ],
    extras_require={
        "dev": ["pytest>=7.0.0", "build", "twine"],
    },
    include_package_data=True,
)
