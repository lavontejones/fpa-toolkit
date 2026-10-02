"""Budget variance and driver-based forecast with decimal currency arithmetic."""
import argparse
import csv
import html
import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

CENT = Decimal('0.01')
ZERO = Decimal('0')

def money(value):
    value = Decimal(str(value))
    if not value.is_finite():
        raise ValueError('Amounts must be finite')
    return value.quantize(CENT, rounding=ROUND_HALF_UP)

def variance(actual, budget, kind):
    if kind not in ('revenue', 'expense'):
        raise ValueError('kind must be revenue or expense')
    actual, budget = money(actual), money(budget)
    delta = actual - budget
    favorable = delta if kind == 'revenue' else -delta
    return {'variance': delta, 'variance_pct': delta / abs(budget) if budget else None,
            'favorable_variance': favorable}

def forecast(opening_cash, revenue, variable_rate, fixed_cost, growth, months):
    cash, revenue, fixed_cost = map(money, (opening_cash, revenue, fixed_cost))
    rate, growth = Decimal(str(variable_rate)), Decimal(str(growth))
    if not rate.is_finite() or not growth.is_finite() or not ZERO <= rate <= 1 or growth <= -1:
        raise ValueError('Invalid rate or growth')
    if months < 1 or months > 60 or revenue < 0 or fixed_cost < 0:
        raise ValueError('Use 1–60 months and nonnegative revenue/costs')
    rows = []
    for month in range(1, months + 1):
        variable = money(revenue * rate)
        operating = revenue - variable - fixed_cost
        cash += operating
        rows.append({'month':month, 'revenue':revenue, 'variable_cost':variable,
                     'fixed_cost':fixed_cost, 'operating_cash':operating, 'closing_cash':cash})
        revenue = money(revenue * (1 + growth))
    return rows

def load_actuals(path):
    rows, seen = [], set()
    with Path(path).open(newline='') as file:
        reader = csv.DictReader(file)
        if reader.fieldnames != ['month','account','kind','budget','actual']:
            raise ValueError('Expected month,account,kind,budget,actual headers')
        for row in reader:
            import datetime
            datetime.datetime.strptime(row['month'], '%Y-%m')
            key = row['month'], row['account']
            if key in seen or not row['account'].strip():
                raise ValueError('Duplicate or empty account')
            seen.add(key)
            budget, actual = money(row['budget']), money(row['actual'])
            rows.append({**row, 'budget':budget, 'actual':actual,
                         **variance(actual,budget,row['kind'])})
    if not rows:
        raise ValueError('No actuals rows')
    return rows

def build_report(input_path, output_dir, assumptions_path):
    actuals = load_actuals(input_path)
    assumptions = json.loads(Path(assumptions_path).read_text())
    scenarios = {}
    for name, growth in assumptions['monthly_growth'].items():
        scenarios[name] = forecast(assumptions['opening_cash'], assumptions['monthly_revenue'],
                                  assumptions['variable_cost_rate'], assumptions['monthly_fixed_cost'],
                                  growth, assumptions['months'])
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    with (out/'variance.csv').open('w',newline='') as file:
        writer=csv.DictWriter(file,fieldnames=list(actuals[0]))
        writer.writeheader();writer.writerows(actuals)
    with (out/'forecast.csv').open('w',newline='') as file:
        writer=csv.DictWriter(file,fieldnames=['scenario',*scenarios[next(iter(scenarios))][0]])
        writer.writeheader()
        for name, rows in scenarios.items():
            writer.writerows({'scenario':name,**row} for row in rows)
    def table(rows, keys):
        head=''.join('<th>'+html.escape(k.replace('_',' ').title())+'</th>' for k in keys)
        body=''.join('<tr>'+''.join('<td>'+html.escape(str(row[k]))+'</td>' for k in keys)+'</tr>' for row in rows)
        return '<table><thead><tr>'+head+'</tr></thead><tbody>'+body+'</tbody></table>'
    report='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>FP&amp;A demonstration</title><style>body{font:16px system-ui;max-width:1100px;margin:40px auto;padding:20px;background:#f7fafc;color:#172c42}table{border-collapse:collapse;background:white;width:100%;margin:20px 0}td,th{padding:10px;text-align:right;border-bottom:1px solid #dde4ed}th:first-child,td:first-child{text-align:left}h1,h2{color:#155e75}.note{padding:18px;background:#e0f2fe}</style><h1>Budget performance &amp; cash outlook</h1><p class="note">Synthetic consulting demonstration by Lavonte Jones. No client data. USD; illustrative operating cash model.</p><h2>Budget versus actual</h2>'''
    report+=table(actuals,['month','account','kind','budget','actual','favorable_variance'])
    for name,rows in scenarios.items():
        report+='<h2>'+html.escape(name.title())+' forecast</h2>'+table(rows,list(rows[0]))
    report+='<h2>Assumptions and limits</h2><p>Monthly revenue grows from the second forecast month. Variable costs scale with revenue; fixed costs stay constant. Revenue is collected and costs are paid in the same month. No working capital, taxes, debt, capital expenditure, or balance-sheet reconciliation. Negative cash is retained to expose funding gaps. Positive favorable variance means better than budget; zero budgets have no percentage variance.</p></html>'
    (out/'report.html').write_text(report)
    return actuals,scenarios

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--actuals',default='samples/actuals.csv')
    parser.add_argument('--assumptions',default='samples/assumptions.json')
    parser.add_argument('--output',default='outputs')
    args=parser.parse_args()
    try:
        build_report(args.actuals,args.output,args.assumptions)
    except (ValueError, KeyError, ArithmeticError) as error:
        parser.error(str(error))
    print(f'Report written to {args.output}/report.html')
