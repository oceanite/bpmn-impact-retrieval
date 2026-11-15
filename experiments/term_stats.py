"""Audit term frequencies and document frequencies in the codebase and BPMN scenarios.

Used by Orang 2 (Query & Preprocessing) to:
1. Identify the top 50 terms with the highest document frequency (DF) in the corpus.
2. Detect generic code boilerplate terms that should be added to `code_stopwords`.
3. Audit query terms from BPMN scenarios (S01–S10 and real pair), detecting zero-DF terms (out-of-vocabulary).
4. Analyze Indonesian terms in BPMN models (data/bpmn/real/) to propose Indonesian stopwords.

Usage (from repository root):
    python experiments/term_stats.py
    python experiments/term_stats.py --top 50
    python experiments/term_stats.py --min-df-pct 15.0
    python experiments/term_stats.py --field body --top 30
    python experiments/term_stats.py --output-csv experiments/results/term_stats.csv

Outputs:
    - Console summary tables (Markdown formatted)
    - experiments/results/term_stats.csv (Corpus term frequencies)
    - experiments/results/query_stats.csv (BPMN query term frequencies in corpus)
    - experiments/results/term_stats_report.md (Comprehensive markdown report)
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

# Regex matching words and camelCase/snake_case pieces (same as preprocessing/text.py)
_WORD = re.compile(r"[A-Za-z][A-Za-z0-9]*")
_CAMEL = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|\d+")

# Standard English stopwords fallback if sklearn is not installed
FALLBACK_ENGLISH_STOPWORDS = frozenset({
    "a", "about", "above", "across", "after", "afterwards", "again", "against", "all", "almost",
    "alone", "along", "already", "also", "although", "always", "am", "among", "amongst", "amoungst",
    "amount", "an", "and", "another", "any", "anyhow", "anyone", "anything", "anyway", "anywhere",
    "are", "around", "as", "at", "back", "be", "became", "because", "become", "becomes", "becoming",
    "been", "before", "beforehand", "behind", "being", "below", "beside", "besides", "between",
    "beyond", "bill", "both", "bottom", "but", "by", "call", "can", "cannot", "cant", "co", "con",
    "could", "couldnt", "cry", "de", "describe", "detail", "do", "done", "down", "due", "during",
    "each", "eg", "eight", "either", "eleven", "else", "elsewhere", "empty", "enough", "etc", "even",
    "ever", "every", "everyone", "everything", "everywhere", "except", "few", "fifteen", "fifty",
    "fill", "find", "fire", "first", "five", "for", "former", "formerly", "forty", "found", "four",
    "from", "front", "full", "further", "get", "give", "go", "had", "has", "hasnt", "have", "he",
    "hence", "her", "here", "hereafter", "hereby", "herein", "hereupon", "hers", "herself", "him",
    "himself", "his", "how", "however", "hundred", "i", "ie", "if", "in", "inc", "indeed",
    "interest", "into", "is", "it", "its", "itself", "keep", "last", "latter", "latterly", "least",
    "less", "ltd", "made", "many", "may", "me", "meanwhile", "might", "mill", "mine", "more",
    "moreover", "most", "mostly", "move", "much", "must", "my", "myself", "name", "namely", "neither",
    "never", "nevertheless", "next", "nine", "no", "nobody", "none", "noone", "nor", "not", "nothing",
    "now", "nowhere", "of", "off", "often", "on", "once", "one", "only", "onto", "or", "other",
    "others", "otherwise", "our", "ours", "ourselves", "out", "over", "own", "part", "per", "perhaps",
    "please", "put", "rather", "re", "same", "see", "seem", "seemed", "seeming", "seems", "serious",
    "several", "she", "should", "show", "side", "since", "sincere", "six", "sixty", "so", "some",
    "somehow", "someone", "something", "sometime", "sometimes", "somewhere", "still", "such",
    "system", "take", "ten", "than", "that", "the", "their", "them", "themselves", "then", "thence",
    "there", "thereafter", "thereby", "therefore", "therein", "thereupon", "these", "they", "thick",
    "thin", "third", "this", "those", "though", "three", "through", "throughout", "thru", "thus",
    "to", "together", "too", "top", "toward", "towards", "twelve", "twenty", "two", "un", "under",
    "until", "up", "upon", "us", "very", "via", "was", "we", "well", "were", "what", "whatever",
    "when", "whence", "whenever", "where", "whereafter", "whereas", "whereby", "wherein", "whereupon",
    "wherever", "whether", "which", "while", "whither", "who", "whoever", "whole", "whom", "whose",
    "why", "will", "with", "within", "without", "would", "yet", "you", "your", "yours", "yourself",
    "yourselves"
})


def split_identifier(token: str) -> list[str]:
    """Split identifier into subwords: `getHTTPResponse_code2` -> `['get', 'http', 'response', 'code', '2']`."""
    parts: list[str] = []
    for chunk in re.split(r"[_\-\s.$/]+", token):
        parts.extend(p.lower() for p in _CAMEL.findall(chunk))
    return parts


def tokenize_raw(text: str | None, min_len: int = 2) -> list[str]:
    """Tokenize text into lowercase subwords without removing stopwords or stemming."""
    if not text:
        return []
    tokens = []
    for word in _WORD.findall(text):
        for piece in split_identifier(word):
            piece = piece.lower()
            if len(piece) >= min_len and not piece.isdigit():
                tokens.append(piece)
    return tokens


def load_corpus_documents(repo_path: Path, cfg: Mapping) -> list[Any]:
    """Load documents via ImpactPipeline, or fall back to scanning directory if tree-sitter is missing."""
    try:
        from impact_retrieval.pipeline import ImpactPipeline
        pipe = ImpactPipeline(cfg=cfg)
        return pipe.documents
    except Exception as e:
        print(f"[Notice] Loading via standard extract_corpus encountered: {e}")
        print("[Notice] Using fallback direct text scanner for target repo.")

    # Lightweight fallback scanner
    from dataclasses import dataclass

    @dataclass
    class SimpleDoc:
        doc_id: str
        path: str
        function: str
        fields: dict[str, str]

    docs = []
    exts = tuple(cfg.get("code_extraction", {}).get("include_extensions", [".go", ".ts", ".tsx", ".sql", ".yaml"]))
    exclude_dirs = set(cfg.get("code_extraction", {}).get("exclude_dirs", [".git", "node_modules", ".next"]))

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for f in files:
            if f.endswith(exts):
                full = Path(root) / f
                rel = full.relative_to(repo_path).as_posix()
                try:
                    content = full.read_text(encoding="utf-8", errors="ignore")
                    docs.append(SimpleDoc(doc_id=rel, path=rel, function="", fields={"body": content, "path": rel}))
                except Exception:
                    pass
    return docs


def load_configured_stopwords(cfg: Mapping) -> tuple[set[str], set[str], set[str]]:
    """Return (english_stopwords, code_stopwords, bpmn_stopwords)."""
    try:
        from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
        en_stops = set(ENGLISH_STOP_WORDS)
    except ImportError:
        en_stops = set(FALLBACK_ENGLISH_STOPWORDS)

    prep = cfg.get("preprocessing", {})
    code_stops = {str(w).lower() for w in prep.get("code_stopwords") or () if w is not None}
    bpmn_stops = {str(w).lower() for w in prep.get("bpmn_stopwords") or () if w is not None}
    return en_stops, code_stops, bpmn_stops


def compute_corpus_stats(documents: Sequence[Any], target_field: str | None = None, min_len: int = 2):
    """Compute DF (document frequency) and TF (term frequency) across the documents."""
    doc_freq = Counter()
    term_freq = Counter()
    total_docs = len(documents)

    for doc in documents:
        seen_in_doc = set()
        fields_to_check = [target_field] if target_field and target_field in doc.fields else doc.fields.keys()
        for f in fields_to_check:
            text = doc.fields.get(f, "")
            tokens = tokenize_raw(text, min_len=min_len)
            for t in tokens:
                term_freq[t] += 1
                seen_in_doc.add(t)
        for t in seen_in_doc:
            doc_freq[t] += 1

    return doc_freq, term_freq, total_docs


def extract_scenario_queries(scenarios_dir: Path, real_bpmn_dir: Path, cfg: Mapping) -> dict[str, list[str]]:
    """Extract query terms for each scenario S01-S10 and the real BPMN pair."""
    scenario_terms = defaultdict(list)
    use_fallback = False

    try:
        from impact_retrieval.bpmn import diff_models, parse_bpmn
        from impact_retrieval.query import build_query

        # S01 - S10
        for s_dir in sorted(scenarios_dir.glob("S*")):
            if s_dir.is_dir() and (s_dir / "old.bpmn").exists() and (s_dir / "new.bpmn").exists():
                old_m = parse_bpmn(s_dir / "old.bpmn")
                new_m = parse_bpmn(s_dir / "new.bpmn")
                diff = diff_models(old_m, new_m)
                query = build_query(diff, old_m, new_m, cfg.get("query"))
                terms = []
                for part in query.parts:
                    terms.extend(tokenize_raw(part.text))
                scenario_terms[s_dir.name] = terms

        # Real pair
        if real_bpmn_dir.exists():
            old_p = real_bpmn_dir / "l0-simple-erp_old.bpmn"
            new_p = real_bpmn_dir / "l0-simple-erp_new.bpmn"
            if old_p.exists() and new_p.exists():
                old_m = parse_bpmn(old_p)
                new_m = parse_bpmn(new_p)
                diff = diff_models(old_m, new_m)
                query = build_query(diff, old_m, new_m, cfg.get("query"))
                terms = []
                for part in query.parts:
                    terms.extend(tokenize_raw(part.text))
                scenario_terms["REAL_BPMN_HAQI"] = terms
    except Exception as err:
        use_fallback = True

    if use_fallback:
        import xml.etree.ElementTree as ET

        def extract_xml_bpmn_terms(path: Path) -> list[str]:
            terms = []
            try:
                tree = ET.parse(path)
                for elem in tree.iter():
                    name = elem.get("name")
                    if name:
                        terms.extend(tokenize_raw(name))
                    tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                    if tag == "documentation" and elem.text:
                        terms.extend(tokenize_raw(elem.text))
            except Exception:
                pass
            return terms

        for s_dir in sorted(scenarios_dir.glob("S*")):
            if s_dir.is_dir():
                combined = []
                if (s_dir / "old.bpmn").exists():
                    combined.extend(extract_xml_bpmn_terms(s_dir / "old.bpmn"))
                if (s_dir / "new.bpmn").exists():
                    combined.extend(extract_xml_bpmn_terms(s_dir / "new.bpmn"))
                scenario_terms[s_dir.name] = combined

        if real_bpmn_dir.exists():
            combined = []
            old_p = real_bpmn_dir / "l0-simple-erp_old.bpmn"
            new_p = real_bpmn_dir / "l0-simple-erp_new.bpmn"
            if old_p.exists():
                combined.extend(extract_xml_bpmn_terms(old_p))
            if new_p.exists():
                combined.extend(extract_xml_bpmn_terms(new_p))
            scenario_terms["REAL_BPMN_HAQI"] = combined

    return dict(scenario_terms)


def classify_term(term: str, df: int, total_docs: int, en_stops: set[str], code_stops: set[str],
                  bpmn_stops: set[str], min_df_pct: float = 20.0) -> str:
    """Classify term into stopword status or candidate."""
    pct = (df / total_docs) * 100 if total_docs else 0.0
    if term in code_stops:
        return "IN_CODE_STOPWORDS"
    if term in en_stops:
        return "IN_ENGLISH_STOPWORDS"
    if term in bpmn_stops:
        return "IN_BPMN_STOPWORDS"
    if pct >= min_df_pct:
        # High frequency boilerplate heuristic
        return "CANDIDATE_STOPWORD"
    return "DOMAIN_TERM"


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit term and document frequencies in codebase and queries.")
    parser.add_argument("--top", type=int, default=50, help="Number of top DF terms to display (default: 50)")
    parser.add_argument("--min-len", type=int, default=2, help="Minimum token length (default: 2)")
    parser.add_argument("--min-df-pct", type=float, default=20.0,
                        help="DF percentage threshold to flag candidate stopwords (default: 20.0)")
    parser.add_argument("--field", type=str, default=None,
                        help="Audit specific field only (e.g. body, name, comment, route)")
    parser.add_argument("--output-csv", type=str, default="experiments/results/term_stats.csv",
                        help="Output CSV for corpus term statistics")
    parser.add_argument("--output-query-csv", type=str, default="experiments/results/query_stats.csv",
                        help="Output CSV for BPMN query terms analysis")
    parser.add_argument("--output-report", type=str, default="experiments/results/term_stats_report.md",
                        help="Output markdown report file")
    args = parser.parse_args()

    # Load config
    from impact_retrieval.config import load_config, resolve_path
    cfg = load_config()
    target_repo = resolve_path(cfg, "target_repo")
    scenarios_dir = resolve_path(cfg, "scenarios")
    real_bpmn_dir = ROOT / "data" / "bpmn" / "real"

    en_stops, code_stops, bpmn_stops = load_configured_stopwords(cfg)

    print("=" * 80)
    print("BPMN Change Impact Retrieval - Term Frequency Audit (Orang 2)")
    print(f"Target repository: {target_repo}")
    print(f"Loaded stopwords: English={len(en_stops)}, Code={len(code_stops)}, BPMN={len(bpmn_stops)}")
    print("=" * 80)

    # 1. Load documents and compute corpus frequencies
    documents = load_corpus_documents(target_repo, cfg)
    total_docs = len(documents)
    print(f"Total documents extracted in corpus: {total_docs}")

    doc_freq, term_freq, total_docs = compute_corpus_stats(documents, target_field=args.field, min_len=args.min_len)
    total_unique_terms = len(doc_freq)
    print(f"Total unique raw terms found: {total_unique_terms}\n")

    # Sort terms by Document Frequency descending, then Term Frequency
    sorted_terms = sorted(doc_freq.items(), key=lambda x: (x[1], term_freq[x[0]]), reverse=True)

    # Prepare top-N terms
    top_terms = sorted_terms[:args.top]

    # Console display for top DF terms
    field_title = f" (Field: {args.field})" if args.field else ""
    print(f"## Top {args.top} Terms by Document Frequency (DF){field_title}\n")
    print("| Rank | Term | DF | DF % | Total TF | Status |")
    print("|---|---|:---:|:---:|:---:|---|")
    for idx, (term, df) in enumerate(top_terms, 1):
        tf = term_freq[term]
        pct = (df / total_docs) * 100
        status = classify_term(term, df, total_docs, en_stops, code_stops, bpmn_stops, args.min_df_pct)
        print(f"| {idx:2d} | `{term}` | {df:4d} | {pct:5.1f}% | {tf:5d} | {status} |")

    # 2. Extract Candidate Stopwords (DF >= min_df_pct and not currently a stopword)
    candidates = []
    for term, df in sorted_terms:
        pct = (df / total_docs) * 100
        status = classify_term(term, df, total_docs, en_stops, code_stops, bpmn_stops, args.min_df_pct)
        if status == "CANDIDATE_STOPWORD":
            candidates.append((term, df, pct, term_freq[term]))

    print(f"\n## Candidate Stopwords (DF >= {args.min_df_pct}% of corpus, not in existing stopwords)\n")
    if candidates:
        print("| Term | DF | DF % | Total TF | Suggested Action |")
        print("|---|:---:|:---:|:---:|---|")
        for term, df, pct, tf in candidates[:30]:
            action = "Add to `code_stopwords`" if pct >= 30.0 else "Consider for `code_stopwords` or synonym"
            print(f"| `{term}` | {df} | {pct:.1f}% | {tf} | {action} |")
    else:
        print("None found above threshold.")

    # 3. Analyze BPMN Query Terms & Zero-DF (Out-of-Vocabulary)
    print("\n## BPMN Query Terms Audit\n")
    scenario_queries = extract_scenario_queries(scenarios_dir, real_bpmn_dir, cfg)

    query_stats_rows = []
    zero_df_terms = defaultdict(list)
    id_terms = []

    for sc_name, terms in scenario_queries.items():
        unique_q_terms = sorted(set(terms))
        for qt in unique_q_terms:
            df = doc_freq.get(qt, 0)
            tf = term_freq.get(qt, 0)
            pct = (df / total_docs) * 100 if total_docs else 0.0
            query_stats_rows.append({"scenario": sc_name, "term": qt, "df": df, "df_pct": pct, "tf": tf})
            if df == 0:
                zero_df_terms[sc_name].append(qt)
                if sc_name == "REAL_BPMN_HAQI":
                    id_terms.append(qt)

    print(f"Audited {len(scenario_queries)} BPMN scenarios/sources.")
    for sc_name, z_terms in sorted(zero_df_terms.items()):
        if z_terms:
            print(f"- **{sc_name}**: {len(z_terms)} Zero-DF terms -> {', '.join(f'`{t}`' for t in z_terms[:12])}"
                  + ("..." if len(z_terms) > 12 else ""))

    # 4. Indonesian Real BPMN Audit
    if "REAL_BPMN_HAQI" in scenario_queries:
        real_terms = set(scenario_queries["REAL_BPMN_HAQI"])
        matched_real = {t: doc_freq[t] for t in real_terms if doc_freq[t] > 0}
        print("\n## Terms in Real Indonesian BPMN (data/bpmn/real/) matching Simple-ERP Code:")
        for t, df in sorted(matched_real.items(), key=lambda x: x[1], reverse=True):
            print(f"- `{t}`: DF = {df} ({df/total_docs*100:.1f}% of docs)")

    # 5. Save Outputs
    out_dir = ROOT / "experiments" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_path = ROOT / args.output_csv
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["rank", "term", "df", "df_pct", "tf", "status"])
        for idx, (term, df) in enumerate(sorted_terms, 1):
            tf = term_freq[term]
            pct = (df / total_docs) * 100
            status = classify_term(term, df, total_docs, en_stops, code_stops, bpmn_stops, args.min_df_pct)
            writer.writerow([idx, term, df, f"{pct:.2f}", tf, status])
    print(f"\nCorpus term frequency table written to: {csv_path}")

    q_csv_path = ROOT / args.output_query_csv
    with open(q_csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["scenario", "term", "df", "df_pct", "tf"])
        for row in query_stats_rows:
            writer.writerow([row["scenario"], row["term"], row["df"], f"{row['df_pct']:.2f}", row["tf"]])
    print(f"Query terms frequency table written to: {q_csv_path}")

    # Generate Markdown Report
    report_path = ROOT / args.output_report
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write(f"# Laporan Audit Frekuensi Kata (Term Frequency Audit)\n\n")
        fh.write(f"- **Target Repositori:** `{target_repo}`\n")
        fh.write(f"- **Jumlah Dokumen Korpus:** {total_docs}\n")
        fh.write(f"- **Jumlah Unique Terms:** {total_unique_terms}\n")
        fh.write(f"- **Threshold Kandidat Stopwords:** DF >= {args.min_df_pct}%\n\n")

        fh.write("## 1. Top 50 Terms Berdasarkan Document Frequency (DF)\n\n")
        fh.write("| Rank | Term | DF | DF % | Total TF | Status |\n")
        fh.write("|---|---|:---:|:---:|:---:|---|\n")
        for idx, (term, df) in enumerate(top_terms, 1):
            tf = term_freq[term]
            pct = (df / total_docs) * 100
            status = classify_term(term, df, total_docs, en_stops, code_stops, bpmn_stops, args.min_df_pct)
            fh.write(f"| {idx} | `{term}` | {df} | {pct:.1f}% | {tf} | {status} |\n")

        fh.write("\n## 2. Kandidat Stopwords Baru untuk `code_stopwords`\n\n")
        fh.write("Term teknis/boilerplate dengan DF tinggi yang belum tersaring oleh stopword eksisting:\n\n")
        fh.write("| Term | DF | DF % | Total TF |\n")
        fh.write("|---|:---:|:---:|:---:|\n")
        for term, df, pct, tf in candidates:
            fh.write(f"| `{term}` | {df} | {pct:.1f}% | {tf} |\n")

        fh.write("\n## 3. Istilah BPMN Query yang Zero-DF (Out-of-Vocabulary)\n\n")
        for sc_name, z_terms in sorted(zero_df_terms.items()):
            if z_terms:
                fh.write(f"- **{sc_name}:** {', '.join(f'`{t}`' for t in z_terms)}\n")

    print(f"Comprehensive markdown report written to: {report_path}")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
