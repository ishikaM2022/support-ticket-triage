"""Reproduce list-price estimates from retained experiment token summaries.
These are NOT Portkey invoices or a total cost-of-ownership measurement.
"""
import argparse
import csv
from pathlib import Path


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--input-per-million',type=float,default=1.0)
    p.add_argument('--output-per-million',type=float,default=5.0)
    p.add_argument('--output',type=Path,default=Path('analysis/cost_comparison.csv'))
    a=p.parse_args()
    if a.input_per_million<0 or a.output_per_million<0: raise ValueError('Rates must be nonnegative')
    experiments=[('Category pilot 1 v1',30,6043,146),('Category pilot 2 v1',30,6046,144),('Category pilot 2 v2',30,12346,145),('Urgency round 2 v1',12,3781,1061),('Urgency round 2 v2',12,6229,1028)]
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f); w.writerow(['experiment','requests','input_tokens','output_tokens','input_usd_per_million','output_usd_per_million','estimated_batch_usd','projected_usd_per_1000_similar_requests'])
        for name,n,inp,out in experiments:
            cost=(inp*a.input_per_million+out*a.output_per_million)/1_000_000
            w.writerow([name,n,inp,out,a.input_per_million,a.output_per_million,cost,cost/n*1000])
            print(f'{name}: estimated batch ${cost:.6f}; projected per 1,000 ${cost/n*1000:.4f}')


if __name__=='__main__':
    main()
