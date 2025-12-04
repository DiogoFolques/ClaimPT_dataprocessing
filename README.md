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

   This will create a *jsons* folder where it will rename and bundle all the UIMA CAS JSON files containing the annotation data.

   The bundling of these files facilitates the dataset building in the next step.

2. **Building the ClaimPT-style Dataset**

   Inside the *jsons* folder we place the *build_claimpt_dataset.py* file and run it as:

   ```bash
   python3 build_claimpt_dataset.py \
     --input_dir . \
     --output_json claimpt_dataset.pretty.json \
     --output_jsonl claimpt_dataset.jsonl
     ```
   This step will output the ClaimPT-style dataset in both JSON and JSONL formats.
   
3. **Creating document-level train/test splits** with preserved Claim / Non-Claim ratios.

   In order to create the train/test splits we just need to run *build_claimpt_splits.py* as follows:

   
   ```bash
   python3 build_claimpt_splits.py \
     --input claimpt_dataset.pretty.json \
     --keep-ratio \
     --seed 42
   ```
   This will create 80/20 train/test splits, with no document overlap to prevent contamination, along with preserved Claim:Non-Claim ratios.
