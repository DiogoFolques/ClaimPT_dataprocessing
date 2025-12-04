# ClaimPT_dataprocessing

This repository provides a small pipeline to build the **ClaimPT-style dataset** from
INCEpTION annotation exports and to derive reproducible **train/test splits**.

The workflow has two main steps:

1. **Build the full dataset** from INCEpTION CAS JSON files.
2. **Create document-level train/test splits** with preserved Claim / Non-Claim ratios.
