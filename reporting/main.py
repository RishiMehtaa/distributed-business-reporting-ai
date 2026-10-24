from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict,Any
from pathlib import Path
import os,re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
app=FastAPI(title='Business Reporting Service')
OUT=Path(os.getenv('OUTPUT_DIR','./output')); OUT.mkdir(parents=True,exist_ok=True)
class Report(BaseModel):
    run_id:str; kpis:Dict[str,Any]; analysis:str; chart_advice:str; investigation:str=''; critique:str=''; qa_passed:bool=False
@app.get('/health')
def health(): return {'service':'reporting','status':'ok'}
@app.post('/generate')
def generate(d:Report):
    sid=re.sub(r'[^A-Za-z0-9_-]','_',d.run_id); paths=[]; monthly=d.kpis.get('monthly_sales',[]); regional=d.kpis.get('regional_sales',[])
    if monthly:
        plt.figure(figsize=(9,4)); plt.plot([x['month'] for x in monthly],[x['sales'] for x in monthly],marker='o'); plt.title('Monthly Sales Trend'); plt.xticks(rotation=45); plt.tight_layout(); p=OUT/f'{sid}_monthly.png'; plt.savefig(p,dpi=130); plt.close(); paths.append(p.name)
    if regional:
        plt.figure(figsize=(7,4)); plt.bar([x['region'] for x in regional],[x['sales'] for x in regional]); plt.title('Sales by Region'); plt.tight_layout(); p=OUT/f'{sid}_regional.png'; plt.savefig(p,dpi=130); plt.close(); paths.append(p.name)
    content=f'''# Executive Business Report\n\nRun: {d.run_id} | QA: {"PASS" if d.qa_passed else "REVIEW REQUIRED"}\n\n## KPIs\n- Total sales: {d.kpis.get('total_sales')}\n- Target: {d.kpis.get('total_target')}\n- Target attainment: {d.kpis.get('target_attainment_pct')}%\n- Latest MoM growth: {d.kpis.get('latest_mom_growth_pct')}%\n- Strongest region: {d.kpis.get('strongest_region')}\n\n## AI Business Analysis\n{d.analysis}\n\n## Conditional Anomaly Investigation\n{d.investigation or 'Not triggered: no material decline detected.'}\n\n## Chart Advice\n{d.chart_advice}\n\n## Independent Critic\n{d.critique}\n\n## Generated charts\n{chr(10).join(paths)}\n\n## Limitation\nMetrics are calculated deterministically. AI commentary is not proof of causation; review before business decisions.\n'''
    path=OUT/f'{sid}_report.md'; path.write_text(content,encoding='utf-8')
    return {'run_id':d.run_id,'report_path':str(path),'chart_paths':[str(OUT/x) for x in paths],'qa_passed':d.qa_passed}
