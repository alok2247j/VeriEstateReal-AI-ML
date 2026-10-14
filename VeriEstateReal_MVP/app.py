import csv, io, json, os, sqlite3, uuid
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, abort
from werkzeug.utils import secure_filename
from joblib import load
from document_processor import allowed_file, extract_text, extract_fields
from ml_utils import score_pair
BASE=Path(__file__).resolve().parent; INSTANCE=BASE/'instance'; UPLOADS=BASE/'uploads'; MODEL_PATH=BASE/'models'/'duplicate_model.joblib'; DB=INSTANCE/'veriestate.db'
INSTANCE.mkdir(exist_ok=True); UPLOADS.mkdir(exist_ok=True)
app=Flask(__name__); app.config['SECRET_KEY']=os.environ.get('VERIESTATE_SECRET','local-demo-key-change-before-deployment'); app.config['MAX_CONTENT_LENGTH']=8*1024*1024
@app.template_filter('from_json')
def from_json(value):
 try: return json.loads(value or '{}')
 except (TypeError,json.JSONDecodeError): return {}
def db():
 con=sqlite3.connect(DB); con.row_factory=sqlite3.Row; con.execute('PRAGMA foreign_keys = ON'); return con
def init_db():
 con=db(); con.executescript("""CREATE TABLE IF NOT EXISTS listings(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,address TEXT NOT NULL,locality TEXT NOT NULL,city TEXT NOT NULL,state TEXT DEFAULT '',property_type TEXT NOT NULL,area_sqft REAL,property_id TEXT DEFAULT '',description TEXT DEFAULT '',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
 CREATE TABLE IF NOT EXISTS documents(id INTEGER PRIMARY KEY AUTOINCREMENT,listing_id INTEGER NOT NULL,original_filename TEXT NOT NULL,stored_filename TEXT NOT NULL,extracted_text TEXT DEFAULT '',extraction_status TEXT DEFAULT '',extracted_fields_json TEXT DEFAULT '{}',created_at TEXT DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(listing_id) REFERENCES listings(id) ON DELETE CASCADE);
 CREATE TABLE IF NOT EXISTS comparisons(id INTEGER PRIMARY KEY AUTOINCREMENT,listing_a_id INTEGER NOT NULL,listing_b_id INTEGER NOT NULL,score REAL NOT NULL,candidate INTEGER NOT NULL,warnings_json TEXT DEFAULT '[]',review_status TEXT DEFAULT 'Needs Review',reviewer_note TEXT DEFAULT '',created_at TEXT DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(listing_a_id) REFERENCES listings(id) ON DELETE CASCADE,FOREIGN KEY(listing_b_id) REFERENCES listings(id) ON DELETE CASCADE);"""); con.commit(); con.close()
init_db()
try: MODEL=load(MODEL_PATH) if MODEL_PATH.exists() else None
except Exception: MODEL=None
def one_listing(i):
 con=db(); row=con.execute('SELECT * FROM listings WHERE id=?',(i,)).fetchone(); con.close(); return row
def all_listings():
 con=db(); rows=con.execute('SELECT * FROM listings ORDER BY id DESC').fetchall(); con.close(); return rows
@app.errorhandler(413)
def too_large(_): flash('File exceeds the 8 MB demo limit. Please use a smaller file.','error'); return redirect(request.referrer or url_for('index'))
@app.route('/')
def index():
 con=db(); counts=[con.execute('SELECT COUNT(*) FROM listings').fetchone()[0],con.execute('SELECT COUNT(*) FROM documents').fetchone()[0],con.execute('SELECT COUNT(*) FROM comparisons').fetchone()[0],con.execute("SELECT COUNT(*) FROM comparisons WHERE review_status='Needs Review'").fetchone()[0]]; recent=con.execute('SELECT * FROM listings ORDER BY id DESC LIMIT 5').fetchall(); con.close()
 metrics=None; mp=BASE/'models'/'model_metrics.json'
 if mp.exists():
  try: metrics=json.loads(mp.read_text(encoding='utf-8'))
  except Exception: pass
 return render_template('index.html',listing_count=counts[0],doc_count=counts[1],comparison_count=counts[2],review_count=counts[3],recent=recent,model_ready=MODEL is not None,metrics=metrics)
@app.route('/listings')
def listings(): return render_template('listings.html',listings=all_listings())
@app.route('/listings/new',methods=['GET','POST'])
def new_listing():
 values={}
 if request.method=='POST':
  keys=['title','address','locality','city','state','property_type','area_sqft','property_id','description']; values={k:request.form.get(k,'').strip() for k in keys}
  missing=[k for k in ['title','address','locality','city','property_type'] if not values[k]]
  if missing: flash('Please complete required fields: '+', '.join(missing),'error'); return render_template('new_listing.html',values=values)
  try:
   area=float(values['area_sqft'].replace(',','')) if values['area_sqft'] else None
   if area is not None and area<=0: raise ValueError
  except ValueError: flash('Area must be a positive number or left blank.','error'); return render_template('new_listing.html',values=values)
  con=db(); cur=con.execute('INSERT INTO listings(title,address,locality,city,state,property_type,area_sqft,property_id,description) VALUES (?,?,?,?,?,?,?,?,?)',(values['title'],values['address'],values['locality'],values['city'],values['state'],values['property_type'],area,values['property_id'],values['description'])); ident=cur.lastrowid; con.commit(); con.close(); flash('Listing saved. Submitted information is not proof of legal ownership.','success'); return redirect(url_for('listing_detail',listing_id=ident))
 return render_template('new_listing.html',values=values)
@app.route('/listings/<int:listing_id>')
def listing_detail(listing_id):
 listing=one_listing(listing_id)
 if listing is None: abort(404)
 con=db(); docs=con.execute('SELECT * FROM documents WHERE listing_id=? ORDER BY id DESC',(listing_id,)).fetchall(); con.close(); return render_template('listing_detail.html',listing=listing,documents=docs)
@app.route('/listings/<int:listing_id>/upload',methods=['GET','POST'])
def upload_document(listing_id):
 listing=one_listing(listing_id)
 if listing is None: abort(404)
 if request.method=='POST':
  file=request.files.get('document')
  if not file or not file.filename: flash('Choose a document first.','error'); return redirect(request.url)
  if not allowed_file(file.filename): flash('Supported formats: PDF, TXT, PNG, JPG, JPEG.','error'); return redirect(request.url)
  name=secure_filename(file.filename) or 'document'; ext=name.rsplit('.',1)[1].lower(); stored=uuid.uuid4().hex+'.'+ext; path=UPLOADS/stored; file.save(path); text,status=extract_text(path,ext); fields=extract_fields(text)
  con=db(); con.execute('INSERT INTO documents(listing_id,original_filename,stored_filename,extracted_text,extraction_status,extracted_fields_json) VALUES (?,?,?,?,?,?)',(listing_id,name,stored,text[:20000],status,json.dumps(fields))); con.commit(); con.close()
  flash((status+'. Extracted fields are suggestions requiring review.') if text else status,'success' if text else 'error'); return redirect(url_for('listing_detail',listing_id=listing_id))
 return render_template('upload_document.html',listing=listing)
@app.route('/compare')
def compare():
 listings=all_listings()
 if len(listings)<2: flash('Add at least two listings, or run python seed_demo.py to load fictional examples.','error')
 return render_template('compare.html',listings=listings)
@app.route('/compare/result',methods=['POST'])
def compare_result():
 if MODEL is None: flash('The ML model is not trained. Run python train_model.py, then restart the app.','error'); return redirect(url_for('compare'))
 try: aid,bid=int(request.form.get('listing_a_id','')),int(request.form.get('listing_b_id',''))
 except ValueError: flash('Choose two listings.','error'); return redirect(url_for('compare'))
 if aid==bid: flash('Choose two different listings.','error'); return redirect(url_for('compare'))
 a,b=one_listing(aid),one_listing(bid)
 if a is None or b is None: abort(404)
 result=score_pair(MODEL,dict(a),dict(b)); status='Needs Review' if result['candidate'] or result['warnings'] else 'No candidate flagged — not a verification'
 con=db(); cur=con.execute('INSERT INTO comparisons(listing_a_id,listing_b_id,score,candidate,warnings_json,review_status) VALUES (?,?,?,?,?,?)',(aid,bid,result['probability'],int(result['candidate']),json.dumps(result['warnings']),status)); cid=cur.lastrowid; con.commit(); con.close()
 return render_template('compare_result.html',a=a,b=b,result=result,comparison_id=cid,status=status)
@app.route('/review')
def review_queue():
 con=db(); rows=con.execute("SELECT c.*,a.title AS title_a,b.title AS title_b FROM comparisons c JOIN listings a ON a.id=c.listing_a_id JOIN listings b ON b.id=c.listing_b_id WHERE c.review_status='Needs Review' ORDER BY c.id DESC").fetchall(); con.close(); return render_template('review_queue.html',rows=rows)
@app.route('/review/<int:comparison_id>',methods=['POST'])
def save_review(comparison_id):
 note=request.form.get('reviewer_note','').strip(); con=db(); row=con.execute('SELECT id FROM comparisons WHERE id=?',(comparison_id,)).fetchone()
 if row is None: con.close(); abort(404)
 con.execute("UPDATE comparisons SET review_status='Reviewed by human',reviewer_note=? WHERE id=?",(note,comparison_id)); con.commit(); con.close(); flash('Manual review note saved; this is not a legal determination.','success'); return redirect(url_for('review_queue'))
@app.route('/export/listings.csv')
def export_listings():
 rows=all_listings(); out=io.StringIO(); fields=['id','title','address','locality','city','state','property_type','area_sqft','property_id','description','created_at']; writer=csv.DictWriter(out,fieldnames=fields); writer.writeheader()
 for r in rows: writer.writerow({k:r[k] for k in fields})
 data=io.BytesIO(out.getvalue().encode('utf-8-sig')); data.seek(0); return send_file(data,mimetype='text/csv',as_attachment=True,download_name='veriestatereal_listings.csv')
@app.route('/about')
def about(): return render_template('about.html')
if __name__=='__main__':
 print('\nVeriEstateReal local prototype'); print('No government portal integration or legal ownership certification.'); print('Open http://127.0.0.1:5000\n'); app.run(debug=True,host='127.0.0.1',port=5000)

