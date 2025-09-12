# README.md - NHANES Local Data Directory

## Overview

This directory contains locally stored NHANES data files organized by survey cycle. This structure allows for:
1. Working with NHANES data offline
2. Ensuring reproducibility with specific dataset versions
3. Avoiding repeated downloads of large datasets
4. Circumventing issues with CDC data servers

## Directory Structure

```
data/
├── 1999-2000/
├── 2007-2008/
├── 2017-2018/
├── 2021-2022/
└── ...other cycles as needed
```

## How to Use

1. Download .XPT files from the NHANES website
2. Save them in the appropriate cycle folder
3. Use the `load_local_data()` function from the notebook to access the data

## File Naming Convention

For consistency, follow the NHANES component naming convention:
- `DEMO_X.xpt` - Demographics data (where X is the cycle letter code)
- `BMX_X.xpt` - Body measurement data
- `BPX_X.xpt` - Blood pressure data
- etc.

## Cycle Letter Codes

- 2021-2022: L
- 2019-2020: K
- 2017-2018: J
- 2015-2016: I
- 2013-2014: H
- 2011-2012: G
- 2009-2010: F
- 2007-2008: E
- 2005-2006: D
- 2003-2004: C
- 2001-2002: B
- 1999-2000: A
