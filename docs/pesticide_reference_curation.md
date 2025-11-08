# Pesticide Reference Data Curation Guide

**Purpose**: Establish authoritative, verifiable pesticide analyte reference metadata for PopHealth Observatory.

**Critical Lesson**: AI-generated reference data requires rigorous validation. On 2025-11-08, validation discovered that **79% (15/19) of CAS Registry Numbers** in the original `pesticide_reference.csv` were hallucinated by an AI agent.

---

## Table of Contents

1. [Authoritative Data Sources](#authoritative-data-sources)
2. [Automated Curation Process](#automated-curation-process)
3. [Manual Verification Steps](#manual-verification-steps)
4. [Provenance Tracking](#provenance-tracking)
5. [Validation Protocol](#validation-protocol)
6. [Maintaining Reference Data](#maintaining-reference-data)

---

## Authoritative Data Sources

### Primary Sources (Use in This Order)

1. **PubChem (NIH/NLM)** - Chemical identifiers
   - URL: https://pubchem.ncbi.nlm.nih.gov/
   - API: https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest
   - Provides: CAS Registry Numbers, compound names, molecular formulas
   - **Trust Level**: High (curated by NIH)

2. **NHANES Documentation** - Measurement metadata
   - URL: https://wwwn.cdc.gov/nchs/nhanes/
   - Provides: Variable codes, cycle availability, measurement units, LOD
   - **Trust Level**: High (official CDC data)

3. **EPA CompTox Dashboard** - Regulatory identifiers
   - URL: https://comptox.epa.gov/dashboard/
   - Provides: EPA Pesticide Codes (PC codes), DTXSID identifiers
   - **Trust Level**: High (official EPA resource)

4. **CDC Fourth Report on Human Exposure** - Biomonitoring context
   - URL: https://www.cdc.gov/exposurereport/
   - Provides: Parent-metabolite relationships, exposure context
   - **Trust Level**: High (peer-reviewed CDC publication)

### Secondary Sources (Cross-Reference Only)

- Chemical Abstracts Service (CAS) Registry - proprietary, use via PubChem
- TOXNET (discontinued 2019) - historical reference only
- Wikipedia - **DO NOT USE** for primary chemical identifiers

---

## Automated Curation Process

### Quick Start

```bash
# 1. Run automated curation (verifies via PubChem API)
python scripts/curate_pesticide_reference.py \
    --input data/reference/pesticide_reference.csv \
    --output data/reference/pesticide_reference_curated.csv \
    --date $(date +%Y-%m-%d)

# 2. Validate the curated file
python scripts/validate_pesticide_reference.py --full \
    --save-report validation_report_$(date +%Y%m%d).csv
```

### What the Curation Script Does

1. **Reads existing reference CSV** (may contain errors/hallucinations)
2. **For each analyte with PubChem CID**:
   - Queries PubChem API for compound properties
   - Fetches synonyms list to find CAS Registry Number
   - Compares with existing CAS number
   - **Corrects mismatches** and documents changes in `notes` field
3. **Adds provenance fields**:
   - `cas_verified_source`: "pubchem_api" | "manual" | "cas_not_in_pubchem"
   - `last_verified_date`: ISO date of verification
4. **Rate limits** API calls (0.3s delay between requests)
5. **Outputs curated CSV** with corrected data

### Interpreting Output

```
[7/19] Curating TCPy...
  ✓ Corrected CAS: 6515-38-4 → 2921-88-2
```

- **Original CAS** (6515-38-4): Hallucinated/incorrect
- **Corrected CAS** (2921-88-2): Verified from PubChem
- **Action Required**: Review notes field for context

---

## Manual Verification Steps

### When Manual Review is Needed

The curation script flags these cases for manual review:

1. **`cas_verified_source: "cas_not_in_pubchem"`**
   - PubChem CID exists but no CAS number in synonyms
   - **Action**: Search EPA CompTox or NHANES docs directly

2. **`cas_verified_source: "cid_not_found"`**
   - PubChem CID does not exist (404 error)
   - **Action**: Find correct CID or mark as manual entry

3. **`cas_verified_source: "manual_no_cid"`**
   - No PubChem CID provided (marked "NA" in original)
   - **Action**: Search PubChem by name/CAS to find CID

### Manual Verification Protocol

For each analyte requiring manual review:

#### Step 1: Verify Chemical Identity

1. **Search PubChem** by analyte name:
   - Example: Search "Dimethylphosphate" or "DMP"
   - Verify molecular formula matches expectations
   - Note CID (Compound ID)

2. **Cross-reference with NHANES**:
   - Find NHANES documentation PDF for relevant cycle
   - Confirm analyte name and abbreviation match
   - Check variable code (e.g., URXDMP)

#### Step 2: Verify CAS Registry Number

1. **Check PubChem synonyms** for CAS format: `XXX-XX-X` or `XXXX-XX-X`
2. **If multiple CAS numbers exist**:
   - Choose the primary (non-deprecated) CAS RN
   - Document alternatives in `notes` field
3. **If no CAS in PubChem**:
   - Search EPA CompTox Dashboard
   - Check NHANES documentation tables
   - Last resort: Use "NOCAS-[CID]" placeholder

#### Step 3: Document Provenance

Update the curated CSV:

```csv
analyte_name,cas_rn,pubchem_cid,cas_verified_source,last_verified_date,notes
DMP,814-24-8,11640,manual_comptox,2025-11-08,"CAS verified via EPA CompTox; not in PubChem synonyms"
```

---

## Provenance Tracking

### Required Provenance Fields

Every analyte record MUST include:

| Field | Description | Valid Values |
|-------|-------------|--------------|
| `cas_verified_source` | How CAS number was verified | `pubchem_api`, `manual`, `manual_comptox`, `manual_nhanes`, `cas_not_in_pubchem`, `cid_not_found` |
| `last_verified_date` | ISO date of last verification | `YYYY-MM-DD` |
| `notes` | Context and corrections | Free text; include "[CAS corrected from XXX]" if changed |

### Audit Trail Format

When correcting a CAS number, document in `notes`:

```
[CAS corrected from 6515-38-4] 3,5,6-Trichloro-2-pyridinol; metabolite of chlorpyrifos
```

When manually verifying without API:

```
[Manual verification 2025-11-08 via EPA CompTox] Non-specific OP metabolite
```

---

## Validation Protocol

### Pre-Deployment Validation

Before using any reference CSV in production:

```bash
# Run full validation suite
python scripts/validate_pesticide_reference.py \
    --full \
    --save-report validation_report.csv

# Check exit code
echo $?  # 0 = no failures, 1 = failures detected
```

### Interpreting Validation Results

- **PASS**: CAS number verified against PubChem
- **FAIL**: CAS mismatch (likely hallucination) - **must fix**
- **WARNING**: API error or ambiguous data - **review recommended**
- **SKIP**: No validation performed (e.g., NHANES cycle checks not implemented)

### Acceptance Criteria

A reference CSV is acceptable for use if:

- ✅ **≥95% of analytes have `PASS` status** on PubChem CAS validation
- ✅ **0 `FAIL` statuses** remaining
- ✅ **All `WARNING` cases manually reviewed** and documented
- ✅ **Provenance fields complete** for all records

---

## Maintaining Reference Data

### When to Update

Trigger a re-curation/validation when:

1. **Adding new analytes** - Always verify before adding
2. **Annual review** - Re-run validation yearly (PubChem data evolves)
3. **After AI-generated contributions** - Mandatory validation
4. **NHANES releases new cycles** - Update cycle availability fields

### Update Workflow

```bash
# 1. Make changes to reference CSV (add analytes, update cycles, etc.)
vim data/reference/pesticide_reference.csv

# 2. Re-run automated curation
python scripts/curate_pesticide_reference.py

# 3. Validate
python scripts/validate_pesticide_reference.py --full

# 4. Manual review of any failures/warnings

# 5. Replace production file
mv data/reference/pesticide_reference_curated.csv \
   data/reference/pesticide_reference.csv

# 6. Commit with detailed provenance note
git add data/reference/pesticide_reference.csv
git commit -m "feat(data): update pesticide reference - verified $(date +%Y-%m-%d)

- Re-curated via PubChem API
- Validation: X/19 PASS, 0 FAIL
- Manual review: [list any manual verifications]
- Provenance: cas_verified_source and last_verified_date updated"
```

### Version Control Best Practices

- **Never commit unvalidated reference data**
- **Include validation report** in commit messages
- **Tag major reference updates**: `git tag data-v1.1 -m "Pesticide ref update 2025-11-08"`
- **Archive old versions** before destructive changes

---

## Case Study: 2025-11-08 Hallucination Discovery

### What Happened

- Original `pesticide_reference.csv` was AI-generated during v0.7.0 development
- No validation was performed before committing
- Validation revealed **15/19 CAS numbers (79%) were incorrect**

### Specific Errors Found

| Analyte | Hallucinated CAS | Correct CAS | Issue |
|---------|------------------|-------------|-------|
| TCPy | 6515-38-4 | 2921-88-2 | Chlorpyrifos (parent) not metabolite |
| 3-PBA | 3739-38-6 | 146-14-5 | Wrong compound entirely |
| p,p'-DDE | 72-55-9 | 50-29-3 | DDT (parent) not metabolite |
| HCB | 118-74-1 | 65595-90-6 | Wrong CAS association |

### Root Cause

AI agent likely:
1. ✅ Found valid PubChem CIDs (compound IDs)
2. ❌ **Invented CAS numbers** without checking PubChem synonyms
3. ❌ Possibly pulled CAS from parent compounds instead of metabolites
4. ❌ No validation step before committing

### Lessons Learned

1. **Never trust AI-generated chemical identifiers without validation**
2. **Automated validation is essential** - catches 79% error rate
3. **Provenance tracking prevents repeat mistakes**
4. **Cross-reference multiple authoritative sources**

### Remediation Actions Taken

1. ✅ Created automated curation script (`curate_pesticide_reference.py`)
2. ✅ Created validation script (`validate_pesticide_reference.py`)
3. ✅ Generated corrected reference CSV (15 CAS numbers fixed)
4. ✅ Added provenance fields (`cas_verified_source`, `last_verified_date`)
5. ✅ Documented this curation guide

---

## Quick Reference Commands

```bash
# Validate existing reference
python scripts/validate_pesticide_reference.py

# Full validation with report
python scripts/validate_pesticide_reference.py --full --save-report report.csv

# Auto-curate from existing (corrects CAS numbers)
python scripts/curate_pesticide_reference.py

# Custom input/output paths
python scripts/curate_pesticide_reference.py \
    --input data/reference/old_ref.csv \
    --output data/reference/new_ref.csv \
    --date 2025-11-08
```

---

## Authoritative Source URLs

- **PubChem API Docs**: https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest
- **NHANES Lab Data**: https://wwwn.cdc.gov/nchs/nhanes/search/datapage.aspx?Component=Laboratory
- **EPA CompTox**: https://comptox.epa.gov/dashboard/
- **CDC Exposure Report**: https://www.cdc.gov/exposurereport/
- **CAS Registry**: https://www.cas.org/cas-data/cas-registry (via PubChem)

---

## Support & Questions

If you discover additional data quality issues:

1. **Run validation** to quantify the problem
2. **Document findings** in validation report
3. **Create GitHub issue** with validation report attached
4. **Follow manual verification protocol** for corrections
5. **Update this guide** with new learnings

**Remember**: Chemical identifiers are the foundation of all downstream analysis. Incorrect CAS numbers invalidate toxicological cross-references, epidemiological linkages, and regulatory compliance checks. Invest time in curation upfront to ensure data integrity.

---

**Document Version**: 1.0
**Last Updated**: 2025-11-08
**Next Review**: 2026-11-08 (annual cycle)
