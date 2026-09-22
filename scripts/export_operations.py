"""Read-only operational aggregates from the app's SQLite database.
Usage: python scripts/export_operations.py --db data/triage.db
No model imports, network requests, writes to the database, or customer-text exports.
"""
import argparse
import csv
import html
import json
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from statistics import mean, median


def parse_time(value):
    if not value:
        return None
    dt=datetime.fromisoformat(value)
    if dt.tzinfo is None:
        raise ValueError('Timezone required')
    return dt.astimezone(timezone.utc)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--db', type=Path, required=True)
    p.add_argument('--output', type=Path, default=Path('analysis/operations'))
    args=p.parse_args()
    db=args.db.resolve()
    conn=sqlite3.connect(db.as_uri()+'?mode=ro',uri=True)
    try:
        raw=conn.execute('SELECT record_json FROM tickets').fetchall()
    finally:
        conn.close()
    daily=Counter(); categories=Counter(); resolved=defaultdict(list); open_by_urgency=Counter()
    issues=Counter(); now=datetime.now(timezone.utc); loaded=0
    for (value,) in raw:
        try:
            r=json.loads(value)
            if not isinstance(r,dict): raise ValueError('Not an object')
        except (ValueError,TypeError):
            issues['invalid_record_json']+=1
            continue
        loaded+=1
        category=r.get('final_category') or r.get('predicted_category') or 'Unclassified'
        categories[category]+=1
        try:
            created=parse_time(r.get('created_at'))
            if created is None or created>now: raise ValueError('Missing or future creation')
            daily[created.date().isoformat()]+=1
        except (ValueError,TypeError):
            issues['missing_invalid_or_future_created_at']+=1
            created=None
        if r.get('resolved_at'):
            try:
                end=parse_time(r['resolved_at'])
                if created is None or end<created or end>now: raise ValueError('Invalid interval')
                # Use the saved historical urgency; never backfill today's urgency.
                tier=r.get('urgency_at_resolution') or 'Unassigned at resolution'
                resolved[tier].append((end-created).total_seconds()/3600)
            except (ValueError,TypeError):
                issues['invalid_resolution_interval']+=1
        else:
            open_by_urgency[r.get('urgency') or 'Needs assessment']+=1
    args.output.mkdir(parents=True,exist_ok=True)
    def write(name,header,rows):
        with (args.output/name).open('w',newline='',encoding='utf-8') as f:
            w=csv.writer(f); w.writerow(header); w.writerows(rows)
    # Fill zero-count dates only inside observed coverage, not before collection.
    if daily:
        day=datetime.fromisoformat(min(daily)).date(); last=datetime.fromisoformat(max(daily)).date()
        while day<=last:
            daily.setdefault(day.isoformat(),0); day+=timedelta(days=1)
    daily_rows=sorted(daily.items())
    category_rows=categories.most_common()
    duration_rows=[(tier,len(values),mean(values),median(values)) for tier,values in sorted(resolved.items())]
    write('volume_by_day_utc.csv',['date_utc','tickets'],daily_rows)
    write('category_breakdown.csv',['category_final_else_predicted','tickets'],category_rows)
    write('resolution_by_urgency.csv',['urgency_at_resolution','resolved_tickets','mean_calendar_hours','median_calendar_hours'],duration_rows)
    write('open_by_urgency.csv',['confirmed_urgency','open_tickets'],open_by_urgency.most_common())
    summary={'generated_at_utc':now.isoformat(),'loaded_records':loaded,'source_rows':len(raw),'valid_resolution_durations':sum(map(len,resolved.values())), 'data_quality_exclusions':dict(issues),'interpretation':'Observed app activity only, including demo/test tickets. Durations are descriptive, not forecasts. Resolved-only averages exclude still-open tickets and are subject to selection bias.'}
    (args.output/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    def table(headers, rows):
        return '<table><thead><tr>'+''.join('<th>'+html.escape(str(x))+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+html.escape(f'{x:.2f}' if isinstance(x,float) else str(x))+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table>'
    def bars(rows):
        peak=max((v for _,v in rows),default=1) or 1
        return ''.join('<div class="row"><span>'+html.escape(str(k))+'</span><div class="track"><div class="bar" style="width:'+str(v/peak*100)+'%"></div></div><b>'+str(v)+'</b></div>' for k,v in rows)
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Observed support operations</title><style>body{font:16px system-ui;background:#f3f6fa;color:#14283d;margin:0}main{max-width:1100px;margin:auto;padding:32px}section{background:white;border:1px solid #dbe3ed;border-radius:12px;padding:24px;margin:20px 0}p{line-height:1.6}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:12px;border-bottom:1px solid #dbe3ed}.row{display:grid;grid-template-columns:160px 1fr 50px;gap:12px;margin:12px 0}.track{background:#edf2f7}.bar{height:20px;background:#137b88}small{color:#536579}</style><main><h1>Observed support operations</h1><p>Demo/test activity is included. These are measured event durations, not customer-service forecasts or evidence of business improvement. Days use UTC.</p>'''
    page+='<section><h2>Ticket arrivals by day</h2>'+bars(daily_rows)+'</section>'
    page+='<section><h2>Category breakdown</h2><p>Final category where available; otherwise the model prediction.</p>'+bars(category_rows)+'</section>'
    page+='<section><h2>Resolution time by urgency</h2><p>Creation to resolution, in calendar hours; grouped by the saved urgency at resolution. Open tickets are excluded. Small groups are descriptive only.</p>'+table(['Urgency','Resolved n','Mean hours','Median hours'],duration_rows)+'</section>'
    page+='<section><h2>Open workload by confirmed urgency</h2>'+bars(open_by_urgency.most_common())+'</section>'
    page+='<section><h2>Data-quality exclusions</h2>'+table(['Check','Excluded records'],issues.items())+'<p>Missing groups or empty charts mean no eligible observations; they do not mean zero elapsed time.</p></section><small>Generated '+now.isoformat()+'</small></main></html>'
    (args.output/'report.html').write_text(page,encoding='utf-8')
    print(json.dumps(summary,indent=2)); print('Report:',args.output/'report.html')


if __name__=='__main__':
    main()
