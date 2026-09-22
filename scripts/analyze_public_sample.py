"""Audit the uploaded sample. Standard library only; never sends data to an API.
Usage: python scripts/analyze_public_sample.py --input customer_support_tickets.csv
"""
import argparse
import csv
import hashlib
import html
import json
from collections import Counter
from datetime import datetime
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--output', type=Path, default=Path('analysis/public_sample'))
    args = p.parse_args()
    raw = args.input.read_bytes()
    with args.input.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        columns = reader.fieldnames or []
    required = {'Ticket ID', 'Ticket Type', 'Ticket Status', 'Ticket Priority', 'First Response Time', 'Time to Resolution'}
    if not required.issubset(columns):
        raise ValueError('Missing columns: ' + ', '.join(sorted(required-set(columns))))
    if not rows:
        raise ValueError('No ticket records')
    closed = [r for r in rows if r['Ticket Status'] == 'Closed']
    invalid_dates = missing_pairs = negative = valid_pairs = 0
    for row in closed:
        if not row['First Response Time'] or not row['Time to Resolution']:
            missing_pairs += 1
            continue
        try:
            start = datetime.fromisoformat(row['First Response Time'])
            end = datetime.fromisoformat(row['Time to Resolution'])
            backwards = end < start
        except (ValueError, TypeError):
            invalid_dates += 1
            continue
        valid_pairs += 1
        negative += backwards
    types = Counter(r['Ticket Type'] for r in rows)
    status = Counter(r['Ticket Status'] for r in rows)
    priority = Counter(r['Ticket Priority'] for r in rows)
    backlog = Counter(r['Ticket Priority'] for r in rows if r['Ticket Status'] != 'Closed')
    summary = {
        'source_filename': args.input.name,
        'source_sha256': hashlib.sha256(raw).hexdigest(),
        'rows': len(rows), 'unique_ticket_ids': len({r['Ticket ID'] for r in rows}),
        'closed': len(closed), 'unresolved': sum(backlog.values()),
        'closed_with_parseable_timestamp_pairs': valid_pairs,
        'closed_with_missing_timestamp_pairs': missing_pairs,
        'closed_with_unparseable_timestamp_pairs': invalid_dates,
        'resolution_before_first_response': negative,
        'negative_interval_share_of_parseable_closed': negative/valid_pairs if valid_pairs else None,
        'creation_timestamp_available': False,
        'interpretation': 'Sample snapshot only. Source priority labels are not validated urgency ground truth. No creation-to-resolution durations can be calculated.'
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output/'audit_summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    for name, counts in [('category_counts', types), ('status_counts', status), ('priority_counts', priority), ('unresolved_by_priority', backlog)]:
        with (args.output/(name+'.csv')).open('w', newline='', encoding='utf-8') as f:
            w=csv.writer(f); w.writerow(['group','tickets','share_within_table'])
            for label,count in counts.most_common(): w.writerow([label,count,count/sum(counts.values())])
    def bars(counts):
        peak=max(counts.values(), default=1)
        return ''.join('<div class="barrow"><span>'+html.escape(label)+'</span><div class="track"><div class="bar" style="width:'+str(100*count/peak)+'%"></div></div><b>'+f'{count:,}'+'</b></div>' for label,count in counts.most_common())
    pct = 100*negative/valid_pairs if valid_pairs else 0
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Support sample audit</title><style>
body{font:16px system-ui,sans-serif;background:#f3f6fa;color:#14283d;margin:0}main{max-width:1100px;margin:auto;padding:40px 24px}h1{font-size:36px;margin-bottom:8px}h2{font-size:22px}p{line-height:1.6}.eyebrow{color:#126c77;font-weight:700;letter-spacing:.12em}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:16px}.card,section{background:white;border:1px solid #dbe3ed;border-radius:12px;padding:24px;margin-top:20px}.card b{display:block;font-size:34px}.muted{color:#536579}.warning{border-left:5px solid #b45819}.barrow{display:grid;grid-template-columns: minmax(110px,190px) 1fr 60px;gap:12px;align-items:center;margin:18px 0}.track{background:#edf2f7;height:20px;border-radius:4px}.bar{background:#137b88;height:20px;border-radius:4px}.barrow b{text-align:right}small{line-height:1.5}footer{margin-top:30px;color:#536579}@media(max-width:500px){.barrow{grid-template-columns:110px 1fr 45px;font-size:13px}h1{font-size:28px}}
</style><main><div class="eyebrow">SUPPORT OPERATIONS / SOURCE AUDIT</div><h1>Check the evidence before the KPI</h1><p class="muted">Uploaded customer-support sample. Descriptive counts, not verified company performance. No customer names, emails or ticket text are included.</p>'''
    page += '<div class="cards">'+''.join('<div class="card"><span>'+label+'</span><b>'+value+'</b><small>'+note+'</small></div>' for label,value,note in [('Sample tickets',f'{len(rows):,}','Snapshot; no arrival date'),('Unresolved',f'{sum(backlog.values()):,}','Open + pending customer response'),('Closed',f'{len(closed):,}','Source status label'),('Reversed timestamps',f'{pct:.1f}%','Of parseable closed-ticket pairs')])+'</div>'
    page += '<section class="warning"><h2>Decision: block resolution-time reporting</h2><p>'+f'{negative:,} of {valid_pairs:,} closed tickets with parseable timestamps show resolution before the first response. There is no ticket-created timestamp. Purchase date cannot stand in for ticket arrival, and “Time to Resolution” contains timestamps, not durations.'+'</p><p>Request an event dictionary and corrected created/responded/resolved timestamps before reporting service speed or staffing trends. Do not repair negative intervals by taking their absolute value or adding a day.</p></section>'
    page += '<section><h2>Ticket category mix</h2>'+bars(types)+'<p class="muted">Source Ticket Type labels; these are separate from the Bitext classifier taxonomy.</p></section>'
    page += '<section><h2>Unresolved tickets by source priority</h2>'+bars(backlog)+'<p class="muted">Snapshot workload only. Source priority is not a model prediction, and no backlog age or SLA breach can be inferred.</p></section>'
    page += '<section><h2>Ticket status</h2>'+bars(status)+'</section><footer>Reproducible with scripts/analyze_public_sample.py. See audit_summary.json for source SHA-256 and denominators.</footer></main></html>'
    (args.output/'report.html').write_text(page, encoding='utf-8')
    print(json.dumps(summary, indent=2))
    print('Report:', args.output/'report.html')


if __name__ == '__main__':
    main()
