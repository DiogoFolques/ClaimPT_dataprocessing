#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import json
import math
import random
from pathlib import Path
from typing import List, Dict, Any, Tuple


def load_dataset(path: Path) -> List[Dict[str, Any]]:
    """
    Load the full dataset from JSON or JSONL into a list of document dicts.
    If the file is valid JSON (list of docs), load that.
    Otherwise, treat it as JSONL (one doc per line).
    """
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"Input file {path} is empty.")

    # Try JSON first
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            data = [data]
        if not isinstance(data, list):
            raise ValueError("Top-level JSON must be a list of documents.")
        return data
    except json.JSONDecodeError:
        # Fallback to JSONL
        docs = []
        with path.open("r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    docs.append(json.loads(line))
                except json.JSONDecodeError as e:
                    raise ValueError(
                        f"Invalid JSON on line {line_no} in JSONL file {path}: {e}"
                    )
        if not docs:
            raise ValueError(f"No documents found in JSONL file {path}.")
        return docs


def count_claims_nonclaims(doc: Dict[str, Any]) -> Tuple[int, int]:
    """
    Count number of claim == True and claim == False items in a document.
    Items where 'claim' is missing or not bool are ignored in the counts.
    """
    items = doc.get("items", []) or []
    n_claims = 0
    n_nonclaims = 0
    for it in items:
        val = it.get("claim", None)
        if val is True:
            n_claims += 1
        elif val is False:
            n_nonclaims += 1
        # else: ignore (unlikely in your final dataset)
    return n_claims, n_nonclaims


def write_json(path: Path, docs: List[Dict[str, Any]]) -> None:
    """Write documents as a pretty JSON list."""
    with path.open("w", encoding="utf-8") as f:
        json.dump(docs, f, ensure_ascii=False, indent=2)


def write_jsonl(path: Path, docs: List[Dict[str, Any]]) -> None:
    """Write documents as JSONL (one JSON object per line)."""
    with path.open("w", encoding="utf-8") as f:
        for doc in docs:
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")


def main():
    ap = argparse.ArgumentParser(
        description=(
            "Split the full ClaimPT dataset (JSON/JSONL) into train/test by document, "
            "avoiding leakage and optionally preserving the global Non-Claim:Claim ratio."
        )
    )
    ap.add_argument(
        "--input",
        required=True,
        help="Full dataset file (JSON or JSONL), same schema as claimpt_dataset.*",
    )
    ap.add_argument(
        "--out-train-json",
        default="train.json",
        help="Output train JSON (list of documents).",
    )
    ap.add_argument(
        "--out-test-json",
        default="test.json",
        help="Output test JSON (list of documents).",
    )
    ap.add_argument(
        "--out-train-jsonl",
        default="train.jsonl",
        help="Output train JSONL (one document per line).",
    )
    ap.add_argument(
        "--out-test-jsonl",
        default="test.jsonl",
        help="Output test JSONL (one document per line).",
    )
    ap.add_argument(
        "--test-size",
        type=float,
        default=0.20,
        help=(
            "Target proportion of TOTAL CLAIMS to place in the test split "
            "(default: 0.20 = 20%%). Splitting is done at document level."
        ),
    )
    ap.add_argument(
        "--keep-ratio",
        action="store_true",
        help=(
            "Aim to preserve the global Non-Claim:Claim ratio in each split by "
            "routing non-claim-only documents accordingly."
        ),
    )
    ap.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible document selection (default: 42).",
    )

    args = ap.parse_args()
    rng = random.Random(args.seed)

    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    docs = load_dataset(input_path)

    # Attach meta info for each document
    doc_infos = []
    total_claims = 0
    total_nonclaims = 0

    for idx, doc in enumerate(docs):
        doc_id = doc.get("document")
        if doc_id is None:
            raise ValueError(
                f"Document at index {idx} has no 'document' field. "
                f"Every entry must have a unique document id."
            )
        n_c, n_nc = count_claims_nonclaims(doc)
        total_claims += n_c
        total_nonclaims += n_nc
        doc_infos.append(
            {
                "idx": idx,
                "id": doc_id,
                "doc": doc,
                "n_claims": n_c,
                "n_nonclaims": n_nc,
            }
        )

    if total_claims == 0:
        raise ValueError(
            "Dataset appears to contain zero claims (claim == true). "
            "Cannot create a claim-based test split."
        )

    global_ratio = total_nonclaims / total_claims if total_claims else 0.0

    # Separate documents into those with claims vs non-claim-only
    docs_with_claims = [d for d in doc_infos if d["n_claims"] > 0]
    docs_nc_only = [d for d in doc_infos if d["n_claims"] == 0]

    # --- Step 1: choose test docs among docs_with_claims (document-level) ---
    target_claims_test = max(1, int(round(args.test_size * total_claims)))
    rng.shuffle(docs_with_claims)

    test_docs_claim = []
    train_docs_claim = []

    cumulative_test_claims = 0
    for di in docs_with_claims:
        if cumulative_test_claims < target_claims_test:
            test_docs_claim.append(di)
            cumulative_test_claims += di["n_claims"]
        else:
            train_docs_claim.append(di)

    # If, for some reason, we didn't put any docs in test, force at least one
    if not test_docs_claim and docs_with_claims:
        test_docs_claim.append(docs_with_claims[0])
        train_docs_claim = [d for d in docs_with_claims[1:]]

    # Current counts from docs that contain claims
    test_claims = sum(d["n_claims"] for d in test_docs_claim)
    train_claims = total_claims - test_claims

    test_nonclaims_from_claim_docs = sum(d["n_nonclaims"] for d in test_docs_claim)
    train_nonclaims_from_claim_docs = sum(d["n_nonclaims"] for d in train_docs_claim)

    # --- Step 2: assign non-claim-only docs (docs_nc_only) ---
    rng.shuffle(docs_nc_only)

    test_docs_nc_only = []
    train_docs_nc_only = []

    if args.keep_ratio and total_claims > 0:
        # We aim to match the global NC:C ratio in TEST (TRAIN follows by complement).
        desired_test_nc = int(round(test_claims * global_ratio))
        current_test_nc = test_nonclaims_from_claim_docs

        # If we're already above the desired NC in test, send all nc-only docs to train.
        if current_test_nc >= desired_test_nc or not docs_nc_only:
            train_docs_nc_only = docs_nc_only[:]
        else:
            needed_extra_nc = desired_test_nc - current_test_nc
            extra_nc_so_far = 0

            for di in docs_nc_only:
                if extra_nc_so_far < needed_extra_nc:
                    test_docs_nc_only.append(di)
                    extra_nc_so_far += di["n_nonclaims"]
                else:
                    train_docs_nc_only.append(di)

            # Any remaining docs (if loop ended early) go to train
            # (but in the current logic, we already placed all).
    else:
        # No ratio-keeping: send ~test_size of nc-only docs (by count of docs) to test
        n_nc_docs = len(docs_nc_only)
        n_nc_docs_test = int(round(args.test_size * n_nc_docs))
        n_nc_docs_test = min(n_nc_docs_test, n_nc_docs)
        test_docs_nc_only = docs_nc_only[:n_nc_docs_test]
        train_docs_nc_only = docs_nc_only[n_nc_docs_test:]

    # --- Step 3: final train/test document sets ---
    train_doc_infos = train_docs_claim + train_docs_nc_only
    test_doc_infos = test_docs_claim + test_docs_nc_only

    # Sanity: every doc must be assigned exactly once
    train_ids = {d["id"] for d in train_doc_infos}
    test_ids = {d["id"] for d in test_doc_infos}
    all_ids = {d["id"] for d in doc_infos}

    if train_ids & test_ids:
        overlap = train_ids & test_ids
        raise AssertionError(f"Document leakage: documents in both splits: {sorted(overlap)[:10]}")

    if (train_ids | test_ids) != all_ids:
        missing = all_ids - (train_ids | test_ids)
        extra = (train_ids | test_ids) - all_ids
        raise AssertionError(
            f"Mismatch in assigned documents. Missing: {sorted(missing)}, Extra: {sorted(extra)}"
        )

    # Sort docs in each split by original index to preserve original order as much as possible
    train_doc_infos_sorted = sorted(train_doc_infos, key=lambda d: d["idx"])
    test_doc_infos_sorted = sorted(test_doc_infos, key=lambda d: d["idx"])

    train_docs = [d["doc"] for d in train_doc_infos_sorted]
    test_docs = [d["doc"] for d in test_doc_infos_sorted]

    # --- Step 4: compute final stats for reporting ---
    def count_split(docs_list: List[Dict[str, Any]]) -> Tuple[int, int, int]:
        docs_count = len(docs_list)
        c = 0
        nc = 0
        for doc in docs_list:
            n_c, n_nc = count_claims_nonclaims(doc)
            c += n_c
            nc += n_nc
        return docs_count, c, nc

    train_docs_count, train_claims_final, train_nonclaims_final = count_split(train_docs)
    test_docs_count, test_claims_final, test_nonclaims_final = count_split(test_docs)

    ratio_train = (
        train_nonclaims_final / train_claims_final if train_claims_final else float("inf")
    )
    ratio_test = (
        test_nonclaims_final / test_claims_final if test_claims_final else float("inf")
    )
    ratio_global = total_nonclaims / total_claims if total_claims else float("inf")

    # --- Step 5: write outputs ---
    out_train_json = Path(args.out_train_json)
    out_test_json = Path(args.out_test_json)
    out_train_jsonl = Path(args.out_train_jsonl)
    out_test_jsonl = Path(args.out_test_jsonl)

    write_json(out_train_json, train_docs)
    write_json(out_test_json, test_docs)
    write_jsonl(out_train_jsonl, train_docs)
    write_jsonl(out_test_jsonl, test_docs)

    # --- Step 6: report ---
    print("=== Split summary ===")
    print(f"Total documents:      {len(docs)}")
    print(f"  Train documents:    {train_docs_count}")
    print(f"  Test documents:     {test_docs_count}")
    print()
    print(f"Total claims:         {total_claims}")
    print(f"  Train claims:       {train_claims_final}")
    print(f"  Test claims:        {test_claims_final}")
    print()
    print(f"Total non-claims:     {total_nonclaims}")
    print(f"  Train non-claims:   {train_nonclaims_final}")
    print(f"  Test non-claims:    {test_nonclaims_final}")
    print()
    print(f"NC:C ratio (global):  {ratio_global:.3f}")
    print(f"NC:C ratio (train):   {ratio_train:.3f}")
    print(f"NC:C ratio (test):    {ratio_test:.3f}")
    print()
    print(f"Target test-size (claims): ~{args.test_size:.2%} of {total_claims}")
    print(f"Achieved test claims:       {test_claims_final} (~{test_claims_final/total_claims:.2%})")
    print()
    print(f"Wrote:")
    print(f"  Train JSON:   {out_train_json}")
    print(f"  Test JSON:    {out_test_json}")
    print(f"  Train JSONL:  {out_train_jsonl}")
    print(f"  Test JSONL:   {out_test_jsonl}")


if __name__ == "__main__":
    main()
