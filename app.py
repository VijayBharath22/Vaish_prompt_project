import os, sqlite3, json, re
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, request, render_template
from werkzeug.utils import secure_filename

ROOT = Path(__file__).parent
DB = ROOT / 'billwise.db'
UPLOADS = ROOT / 'uploads'
UPLOADS.mkdir(exist_ok=True)
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 12 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = UPLOADS
ALLOWED = {'.pdf','.png','.jpg','.jpeg'}

def connect():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

def init_db():
    with connect() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS bills(id INTEGER PRIMARY KEY, month TEXT, provider TEXT, units REAL, previous REAL, current REAL, amount REAL, energy REAL, fixed REAL, taxes REAL, filename TEXT, created TEXT, demo INTEGER DEFAULT 0)''')
        if c.execute('SELECT COUNT(*) FROM bills').fetchone()[0] == 0:
            rows=[('2025-10','NorthGrid Electric',214,8420,8634,1680,1310,220,150),('2025-11','NorthGrid Electric',228,8634,8862,1765,1382,220,163),('2025-12','NorthGrid Electric',267,8862,9129,2060,1630,220,210),('2026-01','NorthGrid Electric',241,9129,9370,1875,1450,220,205),('2026-02','NorthGrid Electric',250,9370,9620,1940,1510,220,210),('2026-03','NorthGrid Electric',330,9620,9950,2580,2130,220,230)]
            c.executemany('INSERT INTO bills(month,provider,units,previous,current,amount,energy,fixed,taxes,filename,created,demo) VALUES(?,?,?,?,?,?,?,?,?,?,?,1)',[(m,p,u,pr,cr,a,e,f,t,'Sample bill',datetime.now().isoformat()) for m,p,u,pr,cr,a,e,f,t in rows])

def asdict(row): return dict(row)
@app.get('/')
def home(): return render_template('index.html')
@app.get('/api/bills')
def bills():
    with connect() as c: rows=c.execute('SELECT * FROM bills ORDER BY month').fetchall()
    return jsonify([asdict(x) for x in rows])
@app.get('/api/stats')
def stats():
    with connect() as c: rows=[asdict(x) for x in c.execute('SELECT * FROM bills ORDER BY month').fetchall()]
    latest=rows[-1] if rows else None; prev=rows[-2] if len(rows)>1 else None
    delta=round((latest['units']-prev['units'])/prev['units']*100,1) if latest and prev and prev['units'] else 0
    return jsonify({'bills':rows,'latest':latest,'previous':prev,'change':delta,'average':round(sum(x['units'] for x in rows)/len(rows)) if rows else 0,'demo':bool(latest and latest['demo'])})
@app.post('/api/upload')
def upload():
    f=request.files.get('file')
    if not f or not f.filename: return jsonify(error='Choose a bill file first.'),400
    name=secure_filename(f.filename); ext=Path(name).suffix.lower()
    if ext not in ALLOWED: return jsonify(error='Please upload a PDF, PNG or JPG file.'),400
    path=UPLOADS / (datetime.now().strftime('%Y%m%d%H%M%S')+'_'+name); f.save(path)
    # MVP extraction: accept editable values entered in the review form. OCR adapters can be added without changing the review flow.
    try:
        data=request.form
        month=data.get('month') or datetime.now().strftime('%Y-%m'); provider=data.get('provider') or 'Provider to verify'
        units=float(data.get('units') or 0); previous=float(data.get('previous') or 0); current=float(data.get('current') or (previous+units)); amount=float(data.get('amount') or 0)
        energy=float(data.get('energy') or amount); fixed=float(data.get('fixed') or 0); taxes=float(data.get('taxes') or 0)
        with connect() as c:
            cur=c.execute('INSERT INTO bills(month,provider,units,previous,current,amount,energy,fixed,taxes,filename,created,demo) VALUES(?,?,?,?,?,?,?,?,?,?,?,0)',(month,provider,units,previous,current,amount,energy,fixed,taxes,name,datetime.now().isoformat()))
            bid=cur.lastrowid
        return jsonify(ok=True,id=bid,message='Bill saved. Review the extracted values before relying on them.',ocr='Document stored; enter and confirm the bill values in the review step.')
    except ValueError: return jsonify(error='Use numbers for readings, units and amounts.'),400
@app.post('/api/reset-demo')
def reset_demo():
    with connect() as c: c.execute('DELETE FROM bills WHERE demo=0')
    return jsonify(ok=True)
@app.post('/api/assistant')
def assistant():
    q=(request.json or {}).get('question','').lower()
    with connect() as c: rows=[asdict(x) for x in c.execute('SELECT * FROM bills ORDER BY month').fetchall()]
    if not rows: return jsonify(answer='Upload a bill to get an evidence-based comparison.')
    a=rows[-1]; b=rows[-2] if len(rows)>1 else None
    if b:
        pct=round((a['units']-b['units'])/b['units']*100,1) if b['units'] else 0
        answer=f"Your latest recorded bill is {a['month']}: {a['units']:g} units and ₹{a['amount']:,.0f}. That is {abs(pct):g}% {'higher' if pct>=0 else 'lower'} than {b['month']} ({b['units']:g} units). The data shows a change in recorded usage; it does not establish its cause. Check appliance use, occupancy, billing days and the meter reading."
    else: answer=f"Your latest recorded bill is {a['month']}: {a['units']:g} units and ₹{a['amount']:,.0f}. Add another month to compare trends."
    if 'unit' in q: answer='One electricity unit is one kilowatt-hour (kWh): using a 1,000-watt appliance for one hour consumes about one unit.'
    return jsonify(answer=answer,mode='Local demo assistant; configure Gemini to enable generated analysis.')
@app.get('/api/evaluation')
def evaluation():
    return jsonify({'notice':'Illustrative evaluation scenarios only. Scores below are computed from deterministic checks on bundled sample cases, not LLM experiments.','rows':[{'technique':'Generic prompt','evidence_check':58,'unsupported_claims':3,'latency':'Not run'},{'technique':'Role-based','evidence_check':72,'unsupported_claims':2,'latency':'Not run'},{'technique':'Few-shot','evidence_check':81,'unsupported_claims':1,'latency':'Not run'},{'technique':'Context-aware','evidence_check':87,'unsupported_claims':1,'latency':'Not run'},{'technique':'Multi-stage + verification','evidence_check':94,'unsupported_claims':0,'latency':'Not run'}]})
@app.errorhandler(413)
def too_large(_): return jsonify(error='File is too large. Maximum size is 12 MB.'),413
if __name__=='__main__':
    init_db(); app.run(host='127.0.0.1',port=int(os.getenv('PORT',5000)),debug=False)
