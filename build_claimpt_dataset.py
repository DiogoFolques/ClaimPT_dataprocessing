#!/usr/bin/env python3
import os
import json
import argparse
from typing import Dict, Any, List, Optional


def convert_single_election_cas(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert one eleições CAS JSON (INCEpTION-style) into a ClaimPT-like doc record.
    """

    # --- Get full document text from Sofa ---
    sofas = [fs for fs in data.get('%FEATURE_STRUCTURES', []) if fs.get('%TYPE') == 'uima.cas.Sofa']
    if not sofas:
        raise ValueError("No uima.cas.Sofa found in document")
    text = sofas[0].get('sofaString', '')

    # --- Document metadata (for document title) ---
    metas = [
        fs for fs in data.get('%FEATURE_STRUCTURES', [])
        if fs.get('%TYPE') == 'de.tudarmstadt.ukp.dkpro.core.api.metadata.type.DocumentMetaData'
    ]
    if not metas:
        raise ValueError("No DocumentMetaData found")
    doc_meta = metas[0]
    document_title = doc_meta.get('documentTitle', '')  # e.g. "news_0001.txt"

    # --- Custom spans (all annotation spans live here) ---
    custom_spans = [fs for fs in data.get('%FEATURE_STRUCTURES', []) if fs.get('%TYPE') == 'custom.Span']

    # --- Meta spans: topic and publication time ---
    topic_span: Optional[Dict[str, Any]] = None
    pubtime_span: Optional[Dict[str, Any]] = None
    for fs in custom_spans:
        meta = fs.get('Metadata')
        if meta == 'News Article Topic' and topic_span is None:
            topic_span = fs
        elif meta == 'Publication Time' and pubtime_span is None:
            pubtime_span = fs

    # News article topic (e.g. "politics", "economy", ...)
    news_article_topic = topic_span.get('categoria') if topic_span else ''

    # Publication time: slice from the text using begin/end offsets
    if pubtime_span is not None:
        b, e = pubtime_span.get('begin', 0), pubtime_span.get('end', 0)
        publication_time = text[b:e].strip()
    else:
        publication_time = ''

    # --- Group annotation spans by label ---
    # Labels we care about: "Claim", "Non-claim", "Claim span", "Claim object", "Claimer", "Time"
    label_groups: Dict[str, List[Dict[str, Any]]] = {}
    for fs in custom_spans:
        label = fs.get('label')
        if not label:
            continue
        label_groups.setdefault(label, []).append(fs)

    claim_spans = label_groups.get('Claim', [])
    nonclaim_spans = label_groups.get('Non-claim', [])
    claim_span_spans = label_groups.get('Claim span', [])
    claim_object_spans = label_groups.get('Claim object', [])
    claimer_spans = label_groups.get('Claimer', [])
    time_spans = label_groups.get('Time', [])

    def spans_to_value(spans: List[Dict[str, Any]]):
        """
        Convert a list of span FS into the JSON schema used in your dataset:

        - 0 spans  -> None
        - 1 span   -> a single dict {"text", "begin", "end"}
        - >1 spans -> list of such dicts
        """
        if not spans:
            return None
        res = []
        for s in spans:
            b, e = s.get('begin', 0), s.get('end', 0)
            res.append({
                "text": text[b:e],
                "begin": b,
                "end": e,
            })
        if len(res) == 1:
            return res[0]
        return res

    def spans_overlapping(spans: List[Dict[str, Any]], start: int, end: int) -> List[Dict[str, Any]]:
        """Return spans whose [begin, end) intervals overlap [start, end)."""
        out: List[Dict[str, Any]] = []
        for s in spans:
            b, e = s.get('begin', 0), s.get('end', 0)
            if not (e <= start or b >= end):
                out.append(s)
        return out

    # Document-level claimer/time (same for all claims in this doc)
    doc_claimer_val = spans_to_value(claimer_spans)  # -> dict or list or None
    doc_time_val = spans_to_value(time_spans)        # -> dict or list or None

    items: List[Dict[str, Any]] = []

    # --- Claims ---
    for c in claim_spans:
        cb, ce = c.get('begin', 0), c.get('end', 0)
        claim_topic = c.get('Topic', news_article_topic)

        item: Dict[str, Any] = {
            "claim": True,
            "begin_character": cb,
            "end_character": ce,
            "text_segment": text[cb:ce],
            "claim_topic": claim_topic,
        }

        # Claim span(s): overlap with this claim span
        cspans = spans_overlapping(claim_span_spans, cb, ce)
        if cspans:
            item["claim_span"] = spans_to_value(cspans)

        # Claim object(s): overlap with this claim span
        o_spans = spans_overlapping(claim_object_spans, cb, ce)
        if o_spans:
            item["claim_object"] = spans_to_value(o_spans)

        # Claimer / time: document-level
        if doc_claimer_val is not None:
            item["claimer"] = doc_claimer_val
        else:
            item["claimer"] = []  # no claimer annotated

        if doc_time_val is not None:
            item["time"] = doc_time_val
        else:
            item["time"] = ""     # match existing dataset style

        items.append(item)

    # --- Non-claims ---
    for n in nonclaim_spans:
        nb, ne = n.get('begin', 0), n.get('end', 0)
        item = {
            "claim": False,
            "begin_character": nb,
            "end_character": ne,
            "text_segment": text[nb:ne],
        }
        items.append(item)

    # Sort everything by position and THEN assign per-document IDs
    items.sort(key=lambda it: it["begin_character"])

    # Use the document title (e.g. "news_0001.txt") to build IDs like "news_0001_c1"
    doc_basename = os.path.splitext(document_title)[0]
    for local_idx, it in enumerate(items, start=1):
        it["id"] = f"{doc_basename}_c{local_idx}"

    return {
        "document": document_title,          # e.g. "news_0001.txt"
        "news_article_topic": news_article_topic,
        "publication_time": publication_time,
        "items": items,
    }


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Convert a folder of INCEpTION-style eleições_XXX.json files "
            "into a ClaimPT-style dataset (JSON + JSONL)."
        )
    )
    parser.add_argument(
        "--input_dir",
        required=True,
        help="Directory containing the eleições_XXX.json files (after you bundled them).",
    )
    parser.add_argument(
        "--output_json",
        default="eleicoes_dataset.pretty.json",
        help="Output pretty JSON file (default: eleicoes_dataset.pretty.json).",
    )
    parser.add_argument(
        "--output_jsonl",
        default="eleicoes_dataset.jsonl",
        help="Output JSONL file (default: eleicoes_dataset.jsonl).",
    )
    args = parser.parse_args()

    input_dir = args.input_dir

    # Collect all .json files in the folder (your 228 elections jsons)
    filenames = [
        f for f in os.listdir(input_dir)
        if f.lower().endswith(".json")
    ]
    filenames.sort()

    if not filenames:
        raise SystemExit(f"No .json files found in directory: {input_dir}")

    dataset: List[Dict[str, Any]] = []

    for fname in filenames:
        path = os.path.join(input_dir, fname)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        doc_record = convert_single_election_cas(data)
        dataset.append(doc_record)
        print(f"[OK] {fname} -> {doc_record['document']} ({len(doc_record['items'])} items)")

    # Write pretty JSON (full list of docs)
    with open(args.output_json, "w", encoding="utf-8") as f_out:
        json.dump(dataset, f_out, ensure_ascii=False, indent=2)

    # Write JSONL (one doc per line)
    with open(args.output_jsonl, "w", encoding="utf-8") as f_out:
        for doc in dataset:
            f_out.write(json.dumps(doc, ensure_ascii=False) + "\n")

    print(f"[DONE] Wrote {len(dataset)} documents to:")
    print(f"  - {args.output_json}")
    print(f"  - {args.output_jsonl}")


if __name__ == "__main__":
    main()
