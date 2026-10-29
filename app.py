import os, sqlite3
from functools import wraps
from flask import Flask, request, jsonify, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
app=Flask(__name__,static_folder='static',static_url_path='/static'); app.secret_key=os.environ.get('CAMPUSBRIDGE_SECRET','local-demo-change-this-secret'); DB=os.path.join(os.path.dirname(__file__),'campusbridge.db')
def conn():
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
def init():
 c=conn(); c.executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,name TEXT NOT NULL,email TEXT UNIQUE NOT NULL,pw TEXT NOT NULL,role TEXT NOT NULL,grad INTEGER,skills TEXT DEFAULT '',location TEXT DEFAULT '',alerts INTEGER DEFAULT 1,sharing INTEGER DEFAULT 0); CREATE TABLE IF NOT EXISTS jobs(id INTEGER PRIMARY KEY,title TEXT,company TEXT,location TEXT,kind TEXT,skills TEXT,years TEXT,deadline TEXT,url TEXT,description TEXT,active INTEGER DEFAULT 1); CREATE TABLE IF NOT EXISTS notices(id INTEGER PRIMARY KEY,user_id INTEGER,job_id INTEGER,subject TEXT,body TEXT,status TEXT DEFAULT 'in-app',read INTEGER DEFAULT 0,created TEXT DEFAULT CURRENT_TIMESTAMP,UNIQUE(user_id,job_id,subject)); CREATE TABLE IF NOT EXISTS applications(id INTEGER PRIMARY KEY,user_id INTEGER,job_id INTEGER,status TEXT DEFAULT 'Interested',UNIQUE(user_id,job_id)); CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,actor INTEGER,action TEXT,details TEXT,created TEXT DEFAULT CURRENT_TIMESTAMP);''')
 if not c.execute("SELECT id FROM users WHERE email='admin@campusbridge.demo'").fetchone(): c.execute('INSERT INTO users(name,email,pw,role) VALUES(?,?,?,?)',('CampusBridge Admin','admin@campusbridge.demo',generate_password_hash('CampusAdmin@123'),'admin'))
 if not c.execute('SELECT id FROM jobs LIMIT 1').fetchone():
  c.executemany('INSERT INTO jobs(title,company,location,kind,skills,years,deadline,url,description) VALUES(?,?,?,?,?,?,?,?,?)', [('Graduate Software Engineer','Atlassian','Bengaluru / Hybrid','Full-time','Python, Java, SQL, React','2026,2027','2026-12-15','https://www.atlassian.com/company/careers','Entry-level software engineering opportunity.'),('Data Analyst Intern','Razorpay','Bengaluru','Internship','SQL, Python, Excel, Tableau','2026,2027','2026-12-10','https://razorpay.com/jobs/','Analyze data and create business insights.'),('Frontend Developer','Freshworks','Remote - India','Full-time','React, JavaScript, CSS','2027','2026-12-20','https://www.freshworks.com/company/careers/','Build web experiences.'),('Backend Engineering Intern','Postman','Bengaluru / Hybrid','Internship','Python, REST APIs, SQL','2027','2026-12-05','https://www.postman.com/company/careers/','Work on APIs and developer tooling.')])
 c.commit(); c.close()
def me():
 if not session.get('uid'): return None
 c=conn(); r=c.execute('SELECT id,name,email,role,grad,skills,location,alerts,sharing FROM users WHERE id=?',(session['uid'],)).fetchone(); c.close(); return dict(r) if r else None
def need(role=None):
 def dec(fn):
  @wraps(fn)
  def w(*a,**kw):
   u=me()
   if not u:return jsonify(error='Please sign in.'),401
   if role and u['role']!=role:return jsonify(error='You do not have permission.'),403
   return fn(*a,**kw)
  return w
 return dec
def log(action,details=''):
 c=conn(); c.execute('INSERT INTO audit(actor,action,details) VALUES(?,?,?)',(session.get('uid'),action,details)); c.commit(); c.close()
@app.get('/')
def home(): return send_from_directory('static','index.html')
@app.get('/api/me')
def api_me(): return jsonify(user=me())
@app.post('/api/register')
def register():
 d=request.get_json() or {}; name=(d.get('name') or '').strip(); email=(d.get('email') or '').strip().lower(); pw=d.get('password') or ''
 if not name or '@' not in email or len(pw)<12:return jsonify(error='Enter a name, valid email, and password of at least 12 characters.'),400
 c=conn()
 try: cur=c.execute("INSERT INTO users(name,email,pw,role,grad,skills,location) VALUES(?,?,?,'student',?,?,?)",(name,email,generate_password_hash(pw),d.get('grad'),d.get('skills',''),d.get('location',''))); c.commit(); uid=cur.lastrowid
 except sqlite3.IntegrityError:c.close();return jsonify(error='An account with this email already exists.'),409
 c.close();session['uid']=uid;log('student_registered',email);return jsonify(user=me()),201
@app.post('/api/login')
def login():
 d=request.get_json() or {}; c=conn(); r=c.execute('SELECT * FROM users WHERE email=?',((d.get('email') or '').strip().lower(),)).fetchone();c.close()
 if not r or not check_password_hash(r['pw'],d.get('password') or ''):return jsonify(error='Email or password is incorrect.'),401
 session.clear();session['uid']=r['id'];log('login',r['role']);return jsonify(user=me())
@app.post('/api/logout')
def logout():session.clear();return jsonify(ok=True)
@app.get('/api/jobs')
def jobs():
 u=me();c=conn();rs=c.execute('SELECT * FROM jobs '+('' if u and u['role']=='admin' else 'WHERE active=1 ' )+'ORDER BY id DESC').fetchall();c.close();out=[]
 for r in rs:
  j=dict(r);req={x.strip().lower() for x in (j['skills'] or '').split(',') if x.strip()};j['required']=sorted(req)
  if u and u['role']=='student':
   own={x.strip().lower() for x in (u['skills'] or '').split(',') if x.strip()};j['score']=round(100*len(req&own)/max(1,len(req)));j['matched']=sorted(req&own);j['missing']=sorted(req-own);j['eligible']=not j['years'] or str(u['grad'] or '') in [x.strip() for x in j['years'].split(',')]
  out.append(j)
 return jsonify(jobs=out)
@app.post('/api/jobs')
@need('admin')
def add_job():
 d=request.get_json() or {}
 if not d.get('title') or not d.get('company'):return jsonify(error='Job title and company are required.'),400
 c=conn();cur=c.execute('INSERT INTO jobs(title,company,location,kind,skills,years,deadline,url,description) VALUES(?,?,?,?,?,?,?,?,?)',(d['title'],d['company'],d.get('location',''),d.get('kind','Full-time'),d.get('skills',''),d.get('years',''),d.get('deadline',''),d.get('url',''),d.get('description','')));jid=cur.lastrowid
 for s in c.execute("SELECT * FROM users WHERE role='student' AND alerts=1").fetchall():
  if d.get('years') and str(s['grad'] or '') not in [x.strip() for x in d['years'].split(',')]:continue
  c.execute('INSERT OR IGNORE INTO notices(user_id,job_id,subject,body) VALUES(?,?,?,?)',(s['id'],jid,'New opportunity: '+d['title'],f"{d['company']} is hiring for {d['title']}. Review the opportunity in CampusBridge."))
 c.commit();c.close();log('job_created',d['title']);return jsonify(ok=True),201
@app.patch('/api/jobs/<int:jid>')
@need('admin')
def patch_job(jid):
 d=request.get_json() or {};allowed={'title','company','location','kind','skills','years','deadline','url','description','active'};f={k:v for k,v in d.items() if k in allowed}
 if not f:return jsonify(error='No fields to update.'),400
 c=conn();c.execute('UPDATE jobs SET '+','.join(k+'=?' for k in f)+' WHERE id=?',(*f.values(),jid));c.commit();c.close();log('job_updated',str(jid));return jsonify(ok=True)
@app.delete('/api/jobs/<int:jid>')
@need('admin')
def archive_job(jid):
 c=conn();c.execute('UPDATE jobs SET active=0 WHERE id=?',(jid,));c.commit();c.close();log('job_archived',str(jid));return jsonify(ok=True)
@app.get('/api/profile')
@need('student')
def profile():return jsonify(profile=me())
@app.patch('/api/profile')
@need('student')
def save_profile():
 d=request.get_json() or {};f={k:d[k] for k in ['name','grad','skills','location','alerts','sharing'] if k in d}
 if not f:return jsonify(error='No changes supplied.'),400
 f={k:(int(bool(v)) if k in ['alerts','sharing'] else v) for k,v in f.items()};c=conn();c.execute('UPDATE users SET '+','.join(k+'=?' for k in f)+' WHERE id=?',(*f.values(),session['uid']));c.commit();c.close();log('profile_updated','student profile');return jsonify(profile=me())
@app.get('/api/notices')
@need('student')
def notices():
 c=conn();rs=c.execute('SELECT n.*,j.title job_title,j.company FROM notices n LEFT JOIN jobs j ON j.id=n.job_id WHERE n.user_id=? ORDER BY n.id DESC',(session['uid'],)).fetchall();c.close();return jsonify(notices=[dict(r) for r in rs])
@app.patch('/api/notices/<int:nid>')
@need('student')
def read_notice(nid):
 c=conn();cur=c.execute('UPDATE notices SET read=1 WHERE id=? AND user_id=?',(nid,session['uid']));c.commit();c.close();return (jsonify(ok=True),200) if cur.rowcount else (jsonify(error='Message not found.'),404)
@app.post('/api/applications/<int:jid>')
@need('student')
def application(jid):
 c=conn();c.execute('INSERT OR IGNORE INTO applications(user_id,job_id) VALUES(?,?)',(session['uid'],jid));c.commit();c.close();return jsonify(ok=True)
@app.get('/api/applications')
@need('student')
def apps():
 c=conn();rs=c.execute('SELECT a.*,j.title,j.company,j.url FROM applications a JOIN jobs j ON j.id=a.job_id WHERE a.user_id=?',(session['uid'],)).fetchall();c.close();return jsonify(applications=[dict(r) for r in rs])
@app.get('/api/admin/data')
@need('admin')
def admin_data():
 c=conn();metrics={k:c.execute(q).fetchone()[0] for k,q in {'students':"SELECT count(*) FROM users WHERE role='student'",'jobs':'SELECT count(*) FROM jobs','active':'SELECT count(*) FROM jobs WHERE active=1','notices':'SELECT count(*) FROM notices'}.items()};students=[dict(r) for r in c.execute("SELECT id,name,email,grad,skills,location,alerts,sharing FROM users WHERE role='student'")];notices=[dict(r) for r in c.execute('SELECT n.*,u.name student,j.title job_title FROM notices n JOIN users u ON u.id=n.user_id LEFT JOIN jobs j ON j.id=n.job_id ORDER BY n.id DESC')];logs=[dict(r) for r in c.execute('SELECT audit.*,users.email FROM audit LEFT JOIN users ON users.id=audit.actor ORDER BY audit.id DESC LIMIT 60')];c.close();return jsonify(metrics=metrics,students=students,notices=notices,logs=logs)
@app.get('/api/health')
def health():return jsonify(ok=True)
if __name__=='__main__':init();print('Admin demo: admin@campusbridge.demo / CampusAdmin@123');app.run(host='127.0.0.1',port=5000,debug=False)
