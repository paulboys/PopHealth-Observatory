from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="pophealth-observatory",
    version="0.1.1",
    author="PopHealth Observatory Team",
    author_email="your.email@example.com",
    description="Open-source population health & nutrition analytics toolkit (current focus: NHANES)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/paulboys/PopHealth-Observatory",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
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
