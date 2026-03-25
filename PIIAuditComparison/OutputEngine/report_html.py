from datetime import datetime
from metrics import get_drift_metrics
from utils import get_logger

logger = get_logger("Generating Drift Detection Report")

def write_html_report(results, html_file):

    if not results:
        print("\nNo changes — HTML report not generated")
        return

    metrics  = get_drift_metrics(results)
    gen_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    high   = metrics.get('HIGH Severity',   0)
    medium = metrics.get('MEDIUM Severity', 0)
    low    = metrics.get('LOW Severity',    0)

    database_total=metrics.get('New Databases', 0)   + metrics.get('Dropped Databases', 0)
    schema_total = metrics.get('New Schemas', 0)   + metrics.get('Dropped Schemas', 0)
    table_total  = metrics.get('New Tables',  0)   + metrics.get('Dropped Tables',  0)
    column_total = (metrics.get('New PII Columns', 0) + metrics.get('New Non PII Columns', 0) +
                    metrics.get('Dropped PII Columns', 0) + metrics.get('Dropped Non PII Columns', 0) +
                    metrics.get('Datatype Changes', 0))

    new_cols    = len([r for r in results if r['ChangeType'] == 'New Column Added'])
    drop_cols   = len([r for r in results if r['ChangeType'] == 'Column Dropped'])
    new_pii     = metrics.get('New PII Columns', 0)
    dropped_pii = metrics.get('Dropped PII Columns', 0)
    dtype_chg   = metrics.get('Datatype Changes', 0)
    new_tables  = metrics.get('New Tables',  0)
    drop_tables = metrics.get('Dropped Tables', 0)
    new_schemas = metrics.get('New Schemas', 0)
    drop_schemas= metrics.get('Dropped Schemas', 0)
    new_databases=metrics.get('New Databases',0)
    dropped_databases = metrics.get('Dropped Databases', 0)

    change_data = [
        ('New PII',          new_pii,     '#e74c3c'),
        ('Dropped PII',      dropped_pii,  '#3498db'),
        ('Datatype Changed', dtype_chg,    '#9b59b6'),
        ('New Table',        new_tables,   '#e67e22'),
        ('Table Dropped',    drop_tables,  '#2980b9'),
        ('New Schema',       new_schemas,  '#f39c12'),
        ('Schema Dropped',   drop_schemas, '#8e44ad'),
        ('New Database',      new_databases,  '#f39c12'),
        ('Database Dropped',  dropped_databases, '#8e44ad'),
    ]
    change_data = [(l, v, c) for l, v, c in change_data if v > 0]
    max_val     = max((v for _, v, _ in change_data), default=1)

    COLOUR_MAP = {
        ('New Column Added',    'Yes')     : '#ffe0e0',
        ('New Column Added',    'No')      : '#fffde0',
        ('New Table Added',     'Yes')     : '#ffe0e0',
        ('New Table Added',     'No')      : '#fffde0',
        ('New Schema Added',    'Yes')     : '#ffe0e0',
        ('New Schema Added',    'No')      : '#fffde0',
        ('New Schema Added',    'Unknown') : '#ffe0e0',
        ('New Database Added',  'Unknown') : '#ffe0e0',
        ('Column Dropped',      'Yes')     : '#fff0e0',
        ('Column Dropped',      'No')      : '#e8f4fb',
        ('Table Dropped',       'Yes')     : '#fff0e0',
        ('Table Dropped',       'No')      : '#e8f4fb',
        ('Schema Dropped',      'Yes')     : '#fff0e0',
        ('Schema Dropped',      'No')      : '#e8f4fb',
        ('Database Dropped',    'Yes')     : '#fff0e0',
        ('Database Dropped',    'No')      : '#e8f4fb',
        ('Datatype Changed',    'Yes')     : '#ffe0e0',
        ('Datatype Changed',    'No')      : '#f5e6ff',
    }

    def sev_badge(sev):
        if sev == 'HIGH':     return '<span class="b-high">HIGH</span>'
        elif sev == 'MEDIUM': return '<span class="b-med">MEDIUM</span>'
        return '<span class="b-low">LOW</span>'

    def pii_tag(is_pii):
        return '<span class="b-pii">PII</span>' if is_pii == 'Yes' else ''

    critical = [r for r in results if r['Severity'] == 'HIGH']

    critical_rows_html = ''
    for r in critical:
        ct     = r['ChangeType']
        is_pii = str(r['IsPII'])
        sev    = str(r['Severity'])
        bg     = COLOUR_MAP.get((ct, is_pii), '#ffffff')
        critical_rows_html += f"""<tr style="background:{bg}">
            <td>{r['Sheet']}</td><td>{r['Database']}</td><td>{r['Schema']}</td>
            <td>{r['Table']}</td><td>{r['Column']}</td>
            <td>{pii_tag(is_pii)} {is_pii}</td>
            <td><span class="ct">{ct}</span></td>
            <td>{sev_badge(sev)}</td>
            <td class="act">{r['Action']}</td>
        </tr>"""

    bar_change = "".join(
        f'<div class="bar-row"><span class="bar-label">{l}</span>'
        f'<div class="bar-track"><div class="bar-fill" style="width:{int(v/max_val*100)}%;background:{c}"></div></div>'
        f'<span class="bar-val">{v}</span></div>'
        for l, v, c in change_data
    )

    max_sev = max(high, medium, low, 1)
    bar_sev = f"""
        <div class="bar-row"><span class="bar-label">HIGH</span><div class="bar-track"><div class="bar-fill" style="width:{int(high/max_sev*100)}%;background:#e74c3c"></div></div><span class="bar-val">{high}</span></div>
        <div class="bar-row"><span class="bar-label">MEDIUM</span><div class="bar-track"><div class="bar-fill" style="width:{int(medium/max_sev*100)}%;background:#e67e22"></div></div><span class="bar-val">{medium}</span></div>
        <div class="bar-row"><span class="bar-label">LOW</span><div class="bar-track"><div class="bar-fill" style="width:{int(low/max_sev*100)}%;background:#27ae60"></div></div><span class="bar-val">{low}</span></div>
    """

    critical_table = f"""
        <table><thead><tr>
            <th>Connection</th><th>Database</th><th>Schema</th><th>Table</th>
            <th>Column</th><th>IsPII</th><th>Change Type</th><th>Severity</th><th>Action</th>
        </tr></thead><tbody>{critical_rows_html}</tbody></table>
    """ if critical else '<p class="no-data">No critical changes detected</p>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>PII Audit Drift Detection Report</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',Arial,sans-serif;background:#f0f2f5;color:#333;font-size:13px}}
.header{{background:linear-gradient(135deg,#1a1a2e,#16213e);color:white;padding:18px 28px}}
.header h1{{font-size:18px;font-weight:600}}
.header p{{font-size:11px;color:#aab;margin-top:3px}}
.container{{padding:20px 28px}}
.sec-title{{font-size:12px;font-weight:600;color:#555;margin:18px 0 10px;text-transform:uppercase;letter-spacing:1px;border-left:3px solid #2980b9;padding-left:8px}}
.summary{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:20px}}
.s-card{{background:white;border-radius:6px;padding:10px 16px;text-align:center;min-width:85px;box-shadow:0 1px 4px rgba(0,0,0,0.08)}}
.s-card b{{display:block;font-size:22px;font-weight:700}}
.s-card span{{font-size:10px;color:#888;text-transform:uppercase}}
.s-red b{{color:#e74c3c}}.s-orange b{{color:#e67e22}}.s-green b{{color:#27ae60}}.s-blue b{{color:#2980b9}}
.divider{{width:1px;background:#ddd;margin:0 4px}}
.charts{{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:20px}}
.chart-box{{background:white;border-radius:8px;padding:16px 20px;box-shadow:0 1px 4px rgba(0,0,0,0.07);flex:1;min-width:260px}}
.chart-box h3{{font-size:11px;font-weight:600;color:#888;margin-bottom:12px;text-transform:uppercase;letter-spacing:0.5px}}
.bar-row{{display:flex;align-items:center;margin-bottom:8px;gap:8px}}
.bar-label{{font-size:11px;color:#555;width:105px;text-align:right;flex-shrink:0}}
.bar-track{{flex:1;background:#f0f0f0;border-radius:3px;height:16px;overflow:hidden}}
.bar-fill{{height:100%;border-radius:3px}}
.bar-val{{font-size:11px;font-weight:600;color:#333;width:22px;text-align:left;flex-shrink:0}}
.legend{{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:12px}}
.li{{display:flex;align-items:center;gap:5px;font-size:11px;color:#555}}
.ld{{width:11px;height:11px;border-radius:2px;flex-shrink:0}}
.table-wrap{{background:white;border-radius:8px;overflow-x:auto;max-height:400px;overflow-y:auto;
              box-shadow:0 1px 4px rgba(0,0,0,0.07)}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
th{{background:#2c3e50;color:white;padding:9px 10px;text-align:left;white-space:nowrap;font-weight:500}}
td{{padding:8px 10px;border-bottom:1px solid #f5f5f5;vertical-align:middle}}
tr:last-child td{{border-bottom:none}}
tr:hover td{{filter:brightness(0.97)}}
.b-high{{background:white;border-radius:8px;overflow-x:auto;max-height:400px;overflow-y:auto;box-shadow:0 1px 4px rgba(0,0,0,0.07)}}
.b-pii{{background:#fde8e8;color:#c0392b;padding:2px 6px;border-radius:3px;font-size:10px;font-weight:600}}
.ct{{background:#eef2ff;color:#3d52d5;padding:2px 7px;border-radius:3px;font-size:10px;white-space:nowrap}}
.act{{font-size:11px;color:#555;max-width:220px}}
.no-data{{padding:20px;text-align:center;color:#bbb;font-size:12px;background:white;border-radius:8px}}
</style>
</head>
<body>
<div class="header">
    <h1>PII Audit Drift Detection Report</h1>
    <p>Generated: {gen_time}</p>
</div>
<div class="container">

<div class="sec-title">Consolidated Drift Summary</div>
<div class="summary">
    <div class="s-card s-red">   <b>{high}</b>         <span>HIGH</span></div>
    <div class="s-card s-orange"><b>{medium}</b>        <span>MEDIUM</span></div>
    <div class="s-card s-green"> <b>{low}</b>           <span>LOW</span></div>
    <div class="divider"></div>
    <div class="s-card s-blue">  <b>{database_total}</b>  <span>Database Changes</span></div>
    <div class="s-card s-blue">  <b>{schema_total}</b>  <span>Schema Changes</span></div>
    <div class="s-card s-blue">  <b>{table_total}</b>   <span>Table Changes</span></div>
</div>

<div class="charts">
    <div class="chart-box"><h3>Changes by Type</h3>{bar_change}</div>
    <div class="chart-box"><h3>Changes by Severity</h3>{bar_sev}</div>
</div>

<div class="sec-title">Consolidated Critical Changes — HIGH Severity Only</div>
<div class="legend">
    <div class="li"><div class="ld" style="background:#ffe0e0"></div>New PII</div>
    <div class="li"><div class="ld" style="background:#fff0e0"></div>Dropped PII</div>
</div>
<div class="table-wrap">{critical_table}</div>

</div>
</body>
</html>"""

    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html)

    logger.info(f"HTML report saved  — {html_file}")
