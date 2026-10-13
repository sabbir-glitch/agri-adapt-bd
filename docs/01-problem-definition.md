# 01. Problem Definition

This document separates **FACT** (independently verifiable, stated plainly), **EVIDENCE** (something a cited source states, not independently re-derived by me), **ASSUMPTION** (unverified but reasonable, stated as such), **HYPOTHESIS** (a claim this project could test but hasn't), and **PROPOSED DESIGN** (a decision made for this prototype). Every claim below is labelled. See `docs/data-provenance/provenance-register.md` for dataset-level source detail.

## Problem statement

**PROPOSED DESIGN framing:** Bangladesh smallholder farmers and the field-level institutions that support them (e.g. Department of Agricultural Extension officers) often make planting and climate-risk decisions without easy access to localized, synthesized agricultural and climate information — not because the underlying data doesn't exist, but because it is distributed across separate institutional systems (meteorological records, agricultural statistics, climate research datasets) that are not combined into a single, interpretable, field-usable form.

## Context

- **FACT:** Bangladesh is a predominantly agrarian economy with high exposure to climate variability (flooding, cyclones, salinity intrusion, irregular monsoon timing) — this is well-established and not specific to any single source cited here.
- **EVIDENCE:** Bangladesh's national open data portal (data.gov.bd) hosts a climate database covering daily temperature, humidity, rainfall, and sunshine from 1948–2014, and an agriculture data group including crop area/production datasets (per search-verified portal description; see provenance register #3).
- **EVIDENCE:** The Bangladesh Bureau of Statistics (BBS) publishes agricultural statistics including crop area, production, and yield rates, including recent minor-crop statistics for 2023–24 and 2024–25 (per BBS's own site, search-verified; see provenance register #4).
- **EVIDENCE:** A 2026 research dataset (AgriClimateBD) exists combining BBS agricultural statistics, crop phenology, NASA POWER climate data, and a 223-farmer field survey across all 64 districts (per independently cross-referenced search descriptions; see provenance register #1). This is evidence that combining these data types for Bangladesh is methodologically established elsewhere, even though I could not access the file myself in this sandbox.

## Affected users

- **PROPOSED DESIGN (user categories for this prototype):** smallholder farmers (primary, indirect beneficiary); Department of Agricultural Extension (DAE) field officers (primary intended user of any decision-support output); programme/policy staff at agricultural institutions such as DAE or BBS (secondary users, for monitoring and programme design); data/technical administrators maintaining the system (operational user).
- **ASSUMPTION:** Field officers have more consistent digital access (smartphone, intermittent internet) than individual farmers, making them a more realistic first-line user for a digital decision-support tool than farmers directly. This is a reasonable planning assumption, not something this project has tested.

## System-level causes (why this gap persists)

- **HYPOTHESIS:** Agricultural and climate data in Bangladesh exist in institutionally separate systems (BBS statistics, BAMIS/DAE meteorological advisories, BARC research databases, academic datasets like AgriClimateBD) that are not joined into a single analytical resource accessible to a field officer. This project does not have evidence this is *the* cause, only that the institutional separation itself is evidenced (different owning bodies, different publication channels — see provenance register).
- **ASSUMPTION:** Even where data exists, it is often published in formats (PDF statistical yearbooks, static web tables) that require manual extraction before analysis — this is a reasonable assumption given how most national statistical offices publish, but was not independently verified for BBS's specific current publication format in this session.

## Current workflow (as currently assumed, not verified)

- **ASSUMPTION:** A DAE field officer currently relies primarily on BAMIS advisories, personal experience, and localized observation, without a synthesized predictive or multi-source decision-support tool. This is a reasonable baseline assumption for a country without a known widely-deployed AI decision-support tool for agriculture, but this project has not conducted the field research to confirm it.

## Digital / data opportunity

- **PROPOSED DESIGN:** Combine (a) institutional agricultural outcome data (BBS-style: district, crop, season, area, production/yield) with (b) climate variables (temperature, rainfall, humidity — NASA POWER-style or BAMIS-style) into a single analytical pipeline that produces interpretable, uncertainty-aware decision support, with a governance layer ensuring the output is never presented as a guaranteed instruction.

## Constraints

- **FACT (this project's own, confirmed through direct testing):** The development environment used to build this prototype cannot directly download files from Kaggle, Mendeley Data, or data.gov.bd, and cannot make live queries to the NASA POWER API. This materially constrains what could be empirically validated in this repository as it currently stands — see `docs/data-provenance/provenance-register.md` for the specific access attempts and results.
- **ASSUMPTION:** A developer running this project's code from a normal internet-connected machine (not this sandbox) would not face the same access constraints, since Kaggle, Mendeley, and NASA POWER are all normally publicly reachable services.

## Assumptions register (consolidated)

| ID | Assumption | Status |
|---|---|---|
| A-001 | Field officers are a more realistic first-line digital user than individual farmers | Unvalidated, reasonable |
| A-002 | Institutional data fragmentation (not data absence) is the main barrier to decision support | Unvalidated hypothesis |
| A-003 | BBS data is at least partly available in a format requiring manual/semi-structured extraction | Unvalidated |
| A-004 | Real data access (Kaggle/Mendeley/NASA POWER) is normal outside this specific sandboxed environment | Reasonable, not tested in this project |

## Out of scope (explicit)

- This project does **not** claim to produce validated agronomic advice.
- This project does **not** claim any field validation, farmer testing, or officer testing has occurred — none has.
- This project does **not** integrate with any live government or institutional system.
- This project does **not** collect or process any real personal farmer data.

## Measurable objectives (for this prototype, not for a real deployment)

1. Produce a documented, runnable pipeline and a source adapter mapped against an observed agricultural CSV schema (implemented); source lineage, units and rainfall semantics remain unresolved (see `docs/data-card.md`).
2. Produce honest, labelled evidence of what data access is and isn't achievable from this environment (met — see provenance register).
3. Produce a governance framework addressing the risk categories relevant to this specific use case (met — see `docs/04-governance-framework.md`).
4. Produce decision-support design (not implementation) that never presents a model output as a guaranteed instruction (met in documentation; not field-tested).

## Research questions this prototype can inform (not answer)

- Does combining district-level agricultural statistics with separately sourced climate variables produce a tractable modelling problem? The historical agricultural dataset has been modelled, but a multi-source climate join remains untested and is outside the current implementation.
- What data-quality issues (missingness, coverage gaps, known anomalies like the NASA POWER precipitation step-change flagged in provenance register #6) would need resolving before any real modelling claim could be made?

## Theory of change (illustrative, not validated)

```
Fragmented agricultural + climate data
        ↓ (PROPOSED DESIGN: this project's pipeline)
Combined, quality-checked analytical dataset
        ↓
Interpretable model output with uncertainty
        ↓ (ASSUMPTION: requires human-oversight layer, untested)
Field-officer-mediated decision support
        ↓ (HYPOTHESIS: unvalidated)
Better-informed, not automated, farmer decisions
```

Every arrow after the first is unvalidated by this project. The theory of change is documented to make explicit what *would* need testing, not to claim it has been tested.

## Limitations of this document

This problem definition is built from search-verified descriptions of institutions and datasets, not from primary fieldwork, interviews, or direct inspection of BBS/data.gov.bd/Mendeley source files (blocked — see provenance register). It should be treated as a well-sourced starting hypothesis for a pilot scoping exercise, not as completed needs assessment.
