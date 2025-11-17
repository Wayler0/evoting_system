
# ----- LIVE RESULTS JSON ENDPOINT ----- #
from flask import jsonify
from flask import Flask, render_template, request, redirect, session, url_for
import os
import time
from sqlalchemy import create_engine, Column, String, Integer, DateTime, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import psycopg2

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'a-default-secret-key-for-development')

# ---------------- DATABASE ---------------- #
DATABASE_URL = os.environ.get('POSTGRES_URL')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Registry(Base):
    __tablename__ = 'registry'
    voter_id = Column(String, primary_key=True)
    full_name = Column(String, nullable=False)

class Candidates(Base):
    __tablename__ = 'candidates'
    voter_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)

class Votes(Base):
    __tablename__ = 'votes'
    id = Column(Integer, primary_key=True, autoincrement=True)
    voter_id = Column(String, nullable=False)
    candidate_id = Column(String, nullable=False)
    timestamp = Column(DateTime, default=func.now())

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------- ROUTES ---------------- #

@app.route('/')
def index():
    return render_template('index.html')  # Role selector

# ----- ADMIN ----- #
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == os.environ.get('ADMIN_PASSWORD', 'adminiebc123'):
            session['admin'] = True
            return redirect('/admin/choose_action')
        else:
            return render_template('admin.html', error="Access Denied")
    return render_template('admin.html')

@app.route('/admin/choose_action')
def choose_action():
    if not session.get('admin'):
        return redirect(url_for('admin'))
    return render_template('admin_choose_action.html')

@app.route('/admin/add', methods=['GET', 'POST'])
def add_candidate():
    if not session.get('admin'):
        return redirect(url_for('admin'))

    db = next(get_db())
    error = None
    success = None
    if request.method == "POST":
        voter_id = request.form["voter_id"].strip()
        full_name = request.form["full_name"].strip()

        match = db.query(Registry).filter_by(voter_id=voter_id, full_name=full_name).first()

        if match:
            existing = db.query(Candidates).filter_by(voter_id=voter_id).first()
            if existing:
                error = "Already a candidate!"
            else:
                new_candidate = Candidates(voter_id=voter_id, name=full_name)
                db.add(new_candidate)
                db.commit()
                success = f"Candidate {full_name} added successfully!"
        else:
            error = "Invalid ID or Name"

    candidates = db.query(Candidates).all()
    voters = db.query(Registry).all()
    return render_template("add_candidate.html", candidates=candidates, voters=voters, error=error, success=success)

@app.route('/admin/add_voter', methods=['GET', 'POST'])
def add_voter():
    if not session.get('admin'):
        return redirect(url_for('admin'))

    db = next(get_db())
    error = None
    success = None
    if request.method == 'POST':
        import re
        voter_id = request.form.get('voter_id', '').strip()
        full_name = request.form.get('full_name', '').strip()
        if not voter_id or not full_name:
            error = "Both Voter ID and Full Name are required."
        elif not re.match(r'^KEV\d{4,}$', voter_id):
            error = "Voter ID must start with 'KEV' followed by at least 4 digits (e.g. KEV0001)."
        else:
            exists = db.query(Registry).filter_by(voter_id=voter_id).first()
            if exists:
                error = "Voter ID already exists."
            else:
                new_voter = Registry(voter_id=voter_id, full_name=full_name)
                db.add(new_voter)
                db.commit()
                success = f"Voter {full_name} added successfully!"
    return render_template('add_voter.html', error=error, success=success)

@app.route('/admin/remove_candidate', methods=['POST'])
def remove_candidate():
    if not session.get('admin'):
        return redirect(url_for('admin'))
    voter_id = request.form.get('voter_id', '').strip()
    db = next(get_db())
    if voter_id:
        candidate = db.query(Candidates).filter_by(voter_id=voter_id).first()
        if candidate:
            db.delete(candidate)
            db.commit()
    return redirect(url_for('add_candidate'))

@app.route('/admin/remove_voter', methods=['POST'])
def remove_voter():
    if not session.get('admin'):
        return redirect(url_for('admin'))
    voter_id = request.form.get('voter_id', '').strip()
    db = next(get_db())
    if voter_id:
        voter = db.query(Registry).filter_by(voter_id=voter_id).first()
        if voter:
            db.delete(voter)
            db.commit()
    return redirect(url_for('add_voter'))

@app.route('/admin/voter_list')
def voter_list():
    if not session.get('admin'):
        return redirect(url_for('admin'))
    db = next(get_db())
    voters = db.query(Registry).all()
    return render_template('voter_list.html', voters=voters)

@app.route('/admin/results')
def results():
    if not session.get('admin'):
        return redirect(url_for('admin'))

    db = next(get_db())
    results = db.query(Candidates.name, func.count(Votes.candidate_id).label('vote_count')).outerjoin(Votes, Candidates.voter_id == Votes.candidate_id).group_by(Candidates.voter_id).all()
    return render_template('results.html', results=results)

@app.route('/voter', methods=['GET', 'POST'])
def voter_auth():
    if request.method == 'POST':
        voter_id = request.form.get('voter_id', '').strip()
        full_name = request.form.get('full_name', '').strip()
        if not voter_id or not full_name:
            return render_template('voter_auth.html', error="Please enter both your Voter ID and Full Name.")
        
        db = next(get_db())
        valid = db.query(Registry).filter_by(voter_id=voter_id, full_name=full_name).first()
        voted = db.query(Votes).filter_by(voter_id=voter_id).first()

        if not valid:
            return render_template('voter_auth.html', error="Voter ID and Name not recognized or do not match.")
        elif voted:
            return render_template('voter_auth.html', error="This voter has already voted.")
        else:
            session['voter_id'] = voter_id
            return redirect(url_for('vote'))
    return render_template('voter_auth.html')

@app.route('/vote', methods=['GET', 'POST'])
def vote():
    voter_id = session.get('voter_id')
    if not voter_id:
        return redirect(url_for('voter_auth'))

    db = next(get_db())
    voted = db.query(Votes).filter_by(voter_id=voter_id).first()
    if voted:
        return redirect(url_for('thankyou'))

    if request.method == 'POST':
        candidate_id = request.form.get('candidate_id', '').strip()
        if not candidate_id:
            candidates = db.query(Candidates).all()
            return render_template('vote.html', voter_id=voter_id, candidates=candidates, error="Please select a candidate.")
        
        new_vote = Votes(voter_id=voter_id, candidate_id=candidate_id)
        db.add(new_vote)
        db.commit()
        return redirect(url_for('thankyou'))

    candidates = db.query(Candidates).all()
    return render_template('vote.html', voter_id=voter_id, candidates=candidates)

@app.route('/thankyou')
def thankyou():
    session.pop('voter_id', None)
    return render_template('thankyou.html')

@app.route('/results_json')
def results_json():
    db = next(get_db())
    results = db.query(Candidates.name, func.count(Votes.candidate_id).label('vote_count')).outerjoin(Votes, Candidates.voter_id == Votes.candidate_id).group_by(Candidates.voter_id).all()
    data = [{'name': row.name, 'vote_count': row.vote_count} for row in results]
    return jsonify(data)


# ---------------- RUN ---------------- #
if __name__ == '__main__':
    init_db()
    app.run(debug=True)