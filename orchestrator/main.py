from fastapi import FastAPI,HTTPException
from pydantic import BaseModel
from typing import List,Dict,Any
from concurrent.futures import ThreadPoolExecutor,as_completed
import os,uuid,requests
app=FastAPI(title='CrewAI Distributed Reporting Orchestrator')
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # local demo only; restrict for public deployment
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
A=os.getenv('ANALYTICS_URL','http://localhost:8001'); I=os.getenv('INSIGHTS_URL','http://localhost:8002'); R=os.getenv('REPORTING_URL','http://localhost:8003')
class RunRequest(BaseModel): rows:List[Dict[str,Any]]; question:str='Assess business performance and recommend next actions.'
def call(method,url,**kwargs):
    try:
        r=requests.request(method,url,timeout=300,**kwargs); r.raise_for_status(); return r.json()
    except requests.RequestException as e: raise HTTPException(502,f'Service request failed ({url}): {e}')
def demo_rows(scenario='normal'):
    rows=[]; months=[f'2025-{m:02d}' for m in range(1,13)]; regions=['North','South','East','West']; cats=['Category A','Category B','Category C']; rf={'North':1.12,'South':1.04,'East':.93,'West':1}; cf={'Category A':1,'Category B':.72,'Category C':.48}
    for mi,month in enumerate(months):
        for region in regions:
            for cat in cats:
                sales=round(9000*rf[region]*cf[cat]*(1+mi*.018))
                if scenario=='anomaly' and month in ('2025-11','2025-12'): sales=round(sales*(.78 if month=='2025-11' else .55))
                rows.append({'month':month,'region':region,'category':cat,'sales':sales,'target':round(sales*1.02)})
    if scenario=='bad_data': rows.append(dict(rows[0]))
    return rows
@app.get('/health')
def health(): return {'service':'orchestrator','status':'ok'}
@app.post('/run')
def run(req:RunRequest):
    run_id=str(uuid.uuid4())[:8]; data={'rows':req.rows}
    with ThreadPoolExecutor(max_workers=2) as ex:
        fp=ex.submit(call,'POST',f'{A}/profile',json=data); fk=ex.submit(call,'POST',f'{A}/kpis',json=data); profile=fp.result(); kpis=fk.result()
    if not profile.get('valid'): return {'run_id':run_id,'status':'BLOCKED_DATA_QUALITY','profile':profile,'kpis':kpis,'message':'Invalid data; AI analysis intentionally skipped.'}
    payload={'kpis':kpis,'profile':profile,'question':req.question}; results={}; errors={}
    with ThreadPoolExecutor(max_workers=1) as ex:
        futures={ex.submit(call,'POST',f'{I}/business-analysis',json=payload):'analysis',ex.submit(call,'POST',f'{I}/chart-advice',json=payload):'chart_advice'}
        if kpis.get('material_decline_flag'): futures[ex.submit(call,'POST',f'{I}/investigate',json={**payload,'extra_context':'Material decline threshold triggered.'})]='investigation'
        for f in as_completed(futures):
            key=futures[f]
            try: results[key]=f.result()
            except Exception as e: errors[key]=str(e)
    if errors: return {'run_id':run_id,'status':'PARTIAL_FAILURE','errors':errors,'agent_results':results,'kpis':kpis}
    candidate=results['analysis']['result']+('\n'+results.get('investigation',{}).get('result',''))
    critic=call('POST',f'{I}/critique',json={**payload,'extra_context':candidate})
    expected = round(sum(float(x['sales']) for x in req.rows), 2)
    numeric_ok = abs(expected - float(kpis['total_sales'])) < 0.01
    qa = numeric_ok and critic['passed']
    report=call('POST',f'{R}/generate',json={'run_id':run_id,'kpis':kpis,'analysis':results['analysis']['result'],'chart_advice':results['chart_advice']['result'],'investigation':results.get('investigation',{}).get('result',''),'critique':critic['result'],'qa_passed':qa})
    return {'run_id':run_id,'status':'COMPLETED' if qa else 'COMPLETED_REVIEW_REQUIRED','profile':profile,'kpis':kpis,'agent_results':results,'critic':critic,'numeric_qa':{'passed':numeric_ok,'independent_total':expected,'reported_total':kpis['total_sales']},'report':report,'workflow':{'parallel':['profile','KPI calculation','business analysis','chart advice'],'conditional':['anomaly investigation if latest MoM <= -10%'],'review':'independent critic controls final QA status'}}
@app.post('/run-demo')
def run_demo(body:Dict[str,Any]={}):
    scenario=body.get('scenario','anomaly')
    if scenario not in ('normal','anomaly','bad_data'): raise HTTPException(400,'scenario must be normal, anomaly, or bad_data')
    return run(RunRequest(rows=demo_rows(scenario)))
