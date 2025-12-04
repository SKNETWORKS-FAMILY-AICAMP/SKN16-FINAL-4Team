#!/usr/bin/env python3
"""
Preprocess emotion conversation JSONL files into CSV pairs for modeling.

Features:
- Read JSONL files where each line is an object with `messages` array
- Extract (user -> assistant) pairs (for each user message, take the next assistant reply)
- Optional: include system prompt as context
- Text cleaning: URL/email/phone masking, HTML removal, special char normalization
- Minimum length filtering and deduplication
- Outputs CSV with columns: id, system, user, assistant, pair_index, src_file

Usage:
    python scripts/preprocess_emotion.py --input data/enhanced_emotional_chatbot --output data/processed/emotion_pairs_train.csv

"""

import argparse
import json
import os
import re
import csv
import html
from pathlib import Path
from typing import List, Dict, Tuple

# Optional tqdm for progress bar
try:
    from tqdm import tqdm
except Exception:
    tqdm = lambda x: x

# PII regexes
EMAIL_RE = re.compile(r"\b[\w.%-]+@[\w.-]+\.[A-Za-z]{2,6}\b")
PHONE_RE = re.compile(r"\b0\d{1,2}-?\d{3,4}-?\d{4}\b")
URL_RE = re.compile(r"http[s]?://\S+|www\.\S+")
HTML_TAG_RE = re.compile(r'<[^>]+>')

# Characters to keep for Korean/English/numbers and whitespace; remove others
KEEP_CHARS_RE = re.compile(r'[^\uAC00-\uD7A3a-zA-Z0-9\s\.,!?%\-\u3131-\u318E\u1100-\u11FF]')


def mask_pii(text: str) -> str:
    if not text:
        return text
    text = EMAIL_RE.sub('[EMAIL]', text)
    text = PHONE_RE.sub('[PHONE]', text)
    text = URL_RE.sub('[URL]', text)
    return text


def clean_text(text: str, keep_pii_masked: bool = True, preserve_punct: bool = True) -> str:
    if text is None:
        return ''
    # unescape HTML entities
    text = html.unescape(text)
    # remove HTML tags
    text = HTML_TAG_RE.sub(' ', text)
    # mask PII
    if keep_pii_masked:
        text = mask_pii(text)
    # remove URLs again if any
    text = URL_RE.sub(' ', text)
    # normalize whitespace
    text = text.replace('\r', ' ').replace('\n', ' ').strip()
    # remove unwanted special characters but keep basic punctuation
    text = KEEP_CHARS_RE.sub(' ', text)
    # optionally remove basic punctuation (.,!?%-) if preserve_punct is False
    if not preserve_punct:
        text = re.sub(r'[\.,!\?%\-]', ' ', text)
    # collapse spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_pairs_from_messages(messages: List[Dict], include_system: bool = True) -> List[Tuple[str, str, str]]:
    """Return list of tuples (system_prompt, user_text, assistant_text).

    For each user message, find the next assistant message and pair them.
    If include_system=True, concatenate all system messages as system_prompt.
    """
    system_parts = [m.get('content', '') for m in messages if m.get('role') == 'system'] if include_system else []
    system_prompt = ' '.join(system_parts).strip() if system_parts else ''

    pairs = []
    # iterate through messages
    for i, m in enumerate(messages):
        if m.get('role') == 'user':
            user_text = m.get('content', '')
            # find next assistant
            assistant_text = ''
            for j in range(i+1, len(messages)):
                if messages[j].get('role') == 'assistant':
                    assistant_text = messages[j].get('content', '')
                    break
            pairs.append((system_prompt, user_text, assistant_text))
    return pairs


def process_jsonl_file(src_path: Path, out_rows: List[Dict], min_len: int = 2, dedup_set: set = None, include_system: bool = True, strip_punct_user: bool = False, strip_punct_assistant: bool = False):
    with src_path.open('r', encoding='utf-8') as f:
        for idx, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception as e:
                # skip malformed lines but log
                print(f"WARN: failed to parse JSONL line {idx} in {src_path}: {e}")
                continue
            messages = obj.get('messages') or []
            if not isinstance(messages, list) or len(messages) == 0:
                continue
            pairs = extract_pairs_from_messages(messages, include_system=include_system)
            for pair_index, (system_prompt, user_text, assistant_text) in enumerate(pairs):
                user_clean = clean_text(user_text, preserve_punct=(not strip_punct_user))
                assistant_clean = clean_text(assistant_text, preserve_punct=(not strip_punct_assistant))
                # check length
                if len(user_clean) < min_len:
                    continue
                # dedup
                key = (user_clean, assistant_clean)
                if dedup_set is not None:
                    if key in dedup_set:
                        continue
                    dedup_set.add(key)
                out_rows.append({
                    'id': f"{src_path.name}-{idx}-{pair_index}",
                    'system': system_prompt,
                    'user': user_clean,
                    'assistant': assistant_clean,
                    'pair_index': pair_index,
                    'src_file': src_path.name,
                })


def ensure_parent(path: Path):
    if not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)


def write_csv(rows: List[Dict], out_path: Path):
    ensure_parent(out_path)
    fieldnames = ['id', 'system', 'user', 'assistant', 'pair_index', 'src_file']
    with out_path.open('w', encoding='utf-8', newline='') as out:
        writer = csv.DictWriter(out, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def find_jsonl_paths(input_path: Path) -> List[Path]:
    if input_path.is_dir():
        return sorted([p for p in input_path.glob('*.jsonl')])
    if input_path.is_file() and input_path.suffix.lower() in ('.jsonl',):
        return [input_path]
    # maybe pattern
    return sorted(list(input_path.parent.glob(input_path.name)))


def parse_args():
    p = argparse.ArgumentParser(description='Preprocess emotion JSONL into user/assistant CSV pairs')
    p.add_argument('--input', '-i', required=True, help='Input JSONL file or directory containing .jsonl')
    p.add_argument('--output', '-o', required=True, help='Output CSV file path')
    p.add_argument('--min-len', type=int, default=2, help='Minimum character length for user utterance after cleaning')
    p.add_argument('--dedup', action='store_true', help='Remove duplicate (user,assistant) pairs')
    p.add_argument('--include-system', action='store_true', help='Include system prompt content as context field')
    p.add_argument('--strip-punct-user', action='store_true', help='Remove basic punctuation from user field')
    p.add_argument('--strip-punct-assistant', action='store_true', help='Remove basic punctuation from assistant field')
    p.add_argument('--sample', type=int, default=0, help='If >0, only process this many lines per file (for quick tests)')
    return p.parse_args()


def main():
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    jsonl_paths = find_jsonl_paths(input_path)
    if not jsonl_paths:
        print(f"No .jsonl files found at {input_path}")
        return

    rows: List[Dict] = []
    dedup_set = set() if args.dedup else None

    # determine punctuation stripping flags
    strip_punct_user = getattr(args, 'strip_punct_user', False)
    strip_punct_assistant = getattr(args, 'strip_punct_assistant', False)

    for src in jsonl_paths:
        print(f"Processing {src}...")
        if args.sample and args.sample > 0:
            # process only first N lines by creating a temp generator
            cnt = 0
            with src.open('r', encoding='utf-8') as f:
                for idx, line in enumerate(tqdm(f)):
                    if cnt >= args.sample:
                        break
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except Exception as e:
                        continue
                    messages = obj.get('messages') or []
                    pairs = extract_pairs_from_messages(messages, include_system=args.include_system)
                    for pair_index, (system_prompt, user_text, assistant_text) in enumerate(pairs):
                        user_clean = clean_text(user_text, preserve_punct=(not strip_punct_user))
                        assistant_clean = clean_text(assistant_text, preserve_punct=(not strip_punct_assistant))
                        if len(user_clean) < args.min_len:
                            continue
                        key = (user_clean, assistant_clean)
                        if dedup_set is not None:
                            if key in dedup_set:
                                continue
                            dedup_set.add(key)
                        rows.append({
                            'id': f"{src.name}-{idx}-{pair_index}",
                            'system': system_prompt,
                            'user': user_clean,
                            'assistant': assistant_clean,
                            'pair_index': pair_index,
                            'src_file': src.name,
                        })
                        cnt += 1
        else:
            process_jsonl_file(src, rows, min_len=args.min_len, dedup_set=dedup_set, include_system=args.include_system, strip_punct_user=strip_punct_user, strip_punct_assistant=strip_punct_assistant)

    print(f"Total pairs collected: {len(rows)}")
    write_csv(rows, output_path)
    print(f"Wrote CSV to {output_path}")


if __name__ == '__main__':
    main()
