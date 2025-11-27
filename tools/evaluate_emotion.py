#!/usr/bin/env python3
"""
도구: 감정 평가 실행기

사용법:
    python tools/evaluate_emotion.py

동작:
 - `tests/data/emotion_cases.jsonl`을 로드합니다.
 - 가능하면 `services.api_emotion.main.generate_emotion`을 사용해서 라벨을 얻고,
   없으면 `routers.chatbot_router.detect_emotion`으로 폴백합니다.
 - 정답(label) 대비 예측(pred)으로 정확도, 클래스별 정확도, 혼동행렬을 계산하고
   `reports/emotion_eval_results.md`에 결과를 씁니다.
"""

import os
import sys
import json
import asyncio
from collections import defaultdict
from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.dirname(__file__))
# Ensure repository root is on sys.path so imports like `services` work
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
# Load .env from repository root explicitly to ensure environment variables
env_path = os.path.join(ROOT, '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    # fallback to default loader (will search CWD)
    load_dotenv()
DATA_PATH = os.path.join(ROOT, 'tests', 'data', 'emotion_cases.jsonl')
REPORT_PATH = os.path.join(ROOT, 'reports', 'emotion_eval_results.md')


def load_cases(path):
    cases = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            cases.append(json.loads(line))
    return cases


async def call_api_emotion(text):
    # Try to import the service and call generate_emotion
    try:
        import services.api_emotion.main as api_emotion
    except Exception:
        return None

    # build payload
    payload = None
    if hasattr(api_emotion, 'EmotionRequest'):
        payload = api_emotion.EmotionRequest(user_text=text, conversation_history=None)
    else:
        payload = {'user_text': text, 'conversation_history': None}

    gen = getattr(api_emotion, 'generate_emotion', None)
    if gen is None:
        return None

    try:
        if asyncio.iscoroutinefunction(gen):
            resp = await gen(payload)
        else:
            loop = asyncio.get_running_loop()
            resp = await loop.run_in_executor(None, lambda: gen(payload))
    except Exception as e:
        return {'pred': None, 'raw': {'error': str(e)}}

    # normalize response
    if hasattr(resp, 'dict'):
        resp = resp.dict()
    if not isinstance(resp, dict):
        return None
    # If the API explicitly returned a canonical_label, prefer that immediately
    canonical = resp.get('canonical_label') or resp.get('canonical')
    if isinstance(canonical, str) and canonical:
        canon = to_canonical(canonical)
        return {'pred': canon, 'raw': resp}
    # Prefer tone_tags/emojis (they often contain more specific tokens).
    tokens = resp.get('tone_tags') or resp.get('emojis') or resp.get('tags')
    if tokens:
        # normalize list/str to list
        if isinstance(tokens, str):
            tokens = [tokens]
        if isinstance(tokens, list):
            for t in tokens:
                canon = to_canonical(t)
                if canon and canon != 'neutral':
                    return {'pred': canon, 'raw': resp}

    # Try scanning description/summary for strong lexical cues (Korean stems added in SYNONYMS)
    desc = resp.get('description') or resp.get('summary') or ''
    if isinstance(desc, str) and desc:
        canon = to_canonical(desc)
        if canon and canon != 'neutral':
            return {'pred': canon, 'raw': resp}

    # Fallback to primary fields
    for key in ('primary_tone', 'primary', 'label', 'emotion'):
        v = resp.get(key)
        if isinstance(v, str) and v:
            canon = to_canonical(v)
            return {'pred': canon, 'raw': resp}

    # last resort: return raw response with no pred
    return {'pred': None, 'raw': resp}


def call_local_detector(text):
    try:
        import routers.chatbot_router as cr
    except Exception:
        return {'pred': None, 'raw': None}
    try:
        return {'pred': cr.detect_emotion(text), 'raw': None}
    except Exception:
        return {'pred': None, 'raw': None}


def to_canonical(label):
    # Prefer backend util if available
    try:
        from utils.emotion_lottie import to_canonical as tc
        return tc(label)
    except Exception:
        if not label or not isinstance(label, str):
            return 'neutral'
        return label.strip().lower()


def compute_metrics(cases, preds):
    labels = ['happy', 'sad', 'angry', 'love', 'fearful', 'neutral']
    totals = defaultdict(int)
    correct = defaultdict(int)
    conf = {a: {b: 0 for b in labels} for a in labels}
    total = 0
    correct_total = 0
    for case, pred in zip(cases, preds):
        gold = to_canonical(case.get('label'))
        if gold not in labels:
            gold = 'neutral'
        p = to_canonical(pred or 'neutral')
        if p not in labels:
            p = 'neutral'
        totals[gold] += 1
        conf[gold][p] += 1
        total += 1
        if gold == p:
            correct[gold] += 1
            correct_total += 1

    per_label_acc = {l: (correct[l], totals[l], (correct[l] / totals[l]) if totals[l] else None) for l in labels}
    overall = (correct_total, total, correct_total / total if total else None)
    return {'per_label': per_label_acc, 'confusion': conf, 'overall': overall}


async def run_evaluation():
    cases = load_cases(DATA_PATH)
    preds = []
    debug_entries = []

    # choose method preference: try api_emotion first (if available), else local
    api_available = False
    try:
        import services.api_emotion.main as _
        api_available = True
    except Exception as e:
        api_available = False
        # write a small debug hint so user can inspect import failure
        print(f'[evaluate_emotion] services.api_emotion import failed: {e}')

    for c in cases:
        text = c['text']
        pred_entry = None
        method = 'local'
        if api_available:
            r = await call_api_emotion(text)
            if isinstance(r, dict) and r.get('pred'):
                pred_entry = r
                method = 'api'
            else:
                # keep raw even if pred is None
                pred_entry = r
        if not pred_entry or not pred_entry.get('pred'):
            r2 = call_local_detector(text)
            # if api provided raw but no pred, retain raw in debug
            if not pred_entry:
                pred_entry = r2
            else:
                # prefer api raw if available
                if not pred_entry.get('raw'):
                    pred_entry['raw'] = r2.get('raw')
                # if api produced no pred, use local pred
                if not pred_entry.get('pred') and r2.get('pred'):
                    pred_entry['pred'] = r2.get('pred')
                    method = 'local'
        # If still no prediction (no API and local failed), use a simple keyword baseline
        if not pred_entry or not pred_entry.get('pred'):
            text_low = (text or '').lower()
            baseline = None
            if any(w in text_low for w in ['기쁘', '행복', '고맙', '즐거', '감사']):
                baseline = 'happy'
            elif any(w in text_low for w in ['슬프', '우울', '눈물', '상처']):
                baseline = 'sad'
            elif any(w in text_low for w in ['화나', '열받', '분노', '불쾌', '짜증', '성냄']):
                baseline = 'angry'
            elif any(w in text_low for w in ['사랑', '보고 싶', '좋아해', '사랑해']):
                baseline = 'love'
            elif any(w in text_low for w in ['무서', '두렵', '겁', '공포', '불안', '막막']):
                baseline = 'fearful'
            else:
                baseline = 'neutral'
            if not pred_entry:
                pred_entry = {'pred': baseline, 'raw': None}
            else:
                pred_entry['pred'] = baseline
            method = 'baseline'
        preds.append(pred_entry.get('pred') if pred_entry else None)
        debug_entries.append({
            'text': text,
            'gold': c.get('label'),
            'pred': pred_entry.get('pred') if pred_entry else None,
            'method': method,
            'raw': pred_entry.get('raw') if pred_entry else None,
        })

    metrics = compute_metrics(cases, preds)

    # collect misclassified entries for reporting
    misclassified = []
    for e in debug_entries:
        g = to_canonical(e.get('gold'))
        p = to_canonical(e.get('pred'))
        if g != p:
            misclassified.append(e)

    # write detailed debug file
    debug_path = os.path.join(os.path.dirname(REPORT_PATH), 'emotion_debug.jsonl')
    with open(debug_path, 'w', encoding='utf-8') as df:
        for e in debug_entries:
            df.write(json.dumps(e, ensure_ascii=False) + "\n")

    # write report
    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write('# Emotion Evaluation Results\n\n')
        f.write(f'API available: {api_available}\n\n')
        overall = metrics['overall']
        f.write(f'- Overall correct/total: {overall[0]}/{overall[1]}\n')
        f.write(f'- Overall accuracy: {overall[2]:.3f}\n\n')

        f.write('## Per-label accuracy\n')
        for label, (corr, tot, acc) in metrics['per_label'].items():
            f.write(f'- {label}: {corr}/{tot} ')
            if acc is None:
                f.write('(n/a)\n')
            else:
                f.write(f'accuracy={acc:.3f}\n')

        f.write('\n## Confusion matrix (gold -> pred)\n')
        labels = ['happy', 'sad', 'angry', 'love', 'fearful', 'neutral']
        f.write('|gold/pred|' + '|'.join(labels) + '|\n')
        f.write('|' + '---|' * (len(labels)+1) + '\n')
        for g in labels:
            row = [str(metrics['confusion'][g][p]) for p in labels]
            f.write('|' + g + '|' + '|'.join(row) + '|\n')
        # Misclassified examples (simplified table: id | text | gold | pred)
        f.write('\n## Misclassified examples\n')
        if not misclassified:
            f.write('\n- None (모든 케이스가 정답 처리됨)\n')
        else:
            f.write('\n| id | text | gold | pred |\n')
            f.write('|---:|------|:----:|:----:|\n')
            for i, m in enumerate(misclassified, start=1):
                gold = to_canonical(m.get('gold'))
                pred = to_canonical(m.get('pred'))
                text = (m.get('text') or '').replace('|', '\\|').replace('\n', ' ')
                f.write(f'| {i} | {text} | {gold} | {pred} |\n')

    print('Evaluation complete. Report written to', REPORT_PATH)


if __name__ == '__main__':
    asyncio.run(run_evaluation())
