# ClaimPT_dataprocessing

This repository provides a small pipeline to build the **ClaimPT-style dataset** from
INCEpTION annotation exports and to derive reproducible **train/test splits**.

1. **Extracting CAS JSON files from INCEpTION.**

   While on the INCEpTION platform we go to *Settings > Export* and select format *UIMA CAS JSON 0.4.0* and then click *Export curated documents*

   Once the download and unzip process is complete, we open the resulting folder.

   Inside the *curation* folder we place the *bundle_cas_json.py* file and we just run it as:

   ```bash
   python3 bundle_cas_json.py
   ```

   This will create a *jsons* folder where it will rename and bundle all the UIMA CAS JSON files.

2. **Building the Dataset**

   Inside the *jsons* folder we place the *build_claimpt_dataset.py* file and run it as:

   ```bash
   python3 build_claimpt_dataset.py \
     --input_dir jsons \
     --output_json claimpt_dataset.pretty.json \
     --output_jsonl claimpt_dataset.jsonl
     ```
   
3. **Create document-level train/test splits** with preserved Claim / Non-Claim ratios.
