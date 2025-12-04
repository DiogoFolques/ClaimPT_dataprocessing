# ClaimPT_dataprocessing

This repository provides a small pipeline to build the **ClaimPT-style dataset** from
INCEpTION annotation exports and to derive reproducible **train/test splits**.

1. **Extracting CAS JSON files from INCEpTION.** \n
   While on the INCEpTION platform we go to *Settings > Export* and select the format *UIMA CAS JSON 0.4.0* and then click *Export curated documents*
    
3. **Create document-level train/test splits** with preserved Claim / Non-Claim ratios.
