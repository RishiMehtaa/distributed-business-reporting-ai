from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Any
from collections import defaultdict
app = FastAPI(title="Distributed Analytics Service")
class Dataset(BaseModel):
    rows: List[Dict[str, Any]]
@app.get('/health')
def health(): return {'service':'analytics','status':'ok'}
@app.post('/profile')
def profile(data: Dataset):
    required={'month','region','category','sales','target'}; issues=[]; seen=set()
    if not data.rows: issues.append('Dataset is empty')
    if data.rows and not required.issubset(data.rows[0]):
        issues.append('Missing columns: '+', '.join(sorted(required-set(data.rows[0]))))
        return {'valid':False,'issues':issues,'row_count':len(data.rows)}
    for i,row in enumerate(data.rows,1):
        if any(row.get(k) in (None,'') for k in required): issues.append(f'Row {i}: missing value')
        try:
            if float(row['sales'])<0 or float(row['target'])<0: issues.append(f'Row {i}: negative sales/target')
        except (ValueError,TypeError,KeyError): issues.append(f'Row {i}: sales/target must be numeric')
        key=(row.get('month'),row.get('region'),row.get('category'))
        if key in seen: issues.append(f'Row {i}: duplicate month/region/category')
        seen.add(key)
    return {'valid':not issues,'issues':issues[:30],'row_count':len(data.rows)}
@app.post('/kpis')
def kpis(data: Dataset):
    if not data.rows: return {'error':'Dataset is empty'}
    monthly,regional,cats=defaultdict(float),defaultdict(float),defaultdict(float); total=target=0.0
    for row in data.rows:
        s=float(row['sales']); total+=s; target+=float(row['target']); monthly[str(row['month'])]+=s; regional[str(row['region'])]+=s; cats[str(row['category'])]+=s
    ordered=sorted(monthly.items()); growth=None
    if len(ordered)>1 and ordered[-2][1]: growth=round((ordered[-1][1]/ordered[-2][1]-1)*100,2)
    strongest=max(regional.items(),key=lambda x:x[1])
    return {'total_sales':round(total,2),'total_target':round(target,2),'target_attainment_pct':round(total/target*100,2) if target else None,'monthly_sales':[{'month':k,'sales':round(v,2)} for k,v in ordered],'regional_sales':[{'region':k,'sales':round(v,2)} for k,v in sorted(regional.items())],'category_sales':[{'category':k,'sales':round(v,2)} for k,v in sorted(cats.items())],'latest_mom_growth_pct':growth,'strongest_region':strongest[0],'strongest_region_sales':round(strongest[1],2),'material_decline_flag':growth is not None and growth<=-10,'row_count':len(data.rows)}
