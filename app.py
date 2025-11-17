
# ----- LIVE RESULTS JSON ENDPOINT ----- #
from flask import jsonify
from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
import time

app = Flask(__name__)
# TODO: Use a secure, randomly generated secret key in production
app.secret_key = 'change-this-in-production'

# ---------------- DATABASE ---------------- #
def get_db():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# ---------------- ROUTES ---------------- #

@app.route('/')
def index():
    return render_template('index.html')  # Role selector

# ----- ADMIN ----- #
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        password = request.form.get('password', '')
        # Store admin password securely, not hardcoded
        if password == 'adminiebc123':
            session['admin'] = True
            return redirect('/admin/choose_action')
        else:
            return render_template('admin.html', error="Access Denied")
    return render_template('admin.html')
# ----- ADMIN CHOOSE ACTION ----- #
@app.route('/admin/choose_action')
def choose_action():
    if not session.get('admin'):
        return redirect(url_for('admin'))
    return render_template('admin_choose_action.html')

@app.route('/admin/add', methods=['GET', 'POST'])
def add_candidate():
    if not session.get('admin'):
        return redirect(url_for('admin'))

    conn = get_db()
    error = None
    success = None
    if request.method == "POST":
        voter_id = request.form["voter_id"].strip()
        full_name = request.form["full_name"].strip()

        # 1. Verify both voter_id and full_name exist in registry
        match = conn.execute("SELECT * FROM registry WHERE voter_id = ? AND full_name = ?", (voter_id, full_name)).fetchone()

        if match:
            # 2. Check if already a candidate
            existing = conn.execute("SELECT * FROM candidates WHERE voter_id = ?", (voter_id,)).fetchone()
            if existing:
                error = "Already a candidate!"
            else:
                # 3. Insert candidate
                conn.execute("INSERT INTO candidates (voter_id, name) VALUES (?, ?)", (voter_id, full_name))
                conn.commit()
                success = f"Candidate {full_name} added successfully!"
        else:
            error = "Invalid ID or Name"

    # Fetch candidate list for display
    candidates = conn.execute("SELECT voter_id, name FROM candidates").fetchall()
    voters = conn.execute("SELECT voter_id, full_name FROM registry").fetchall()
    return render_template("add_candidate.html", candidates=candidates, voters=voters, error=error, success=success)
 # ----- ADMIN ADD VOTER ----- #
@app.route('/admin/add_voter', methods=['GET', 'POST'])
def add_voter():
    if not session.get('admin'):
        return redirect(url_for('admin'))

    error = None
    success = None
    if request.method == 'POST':
        import re
        voter_id = request.form.get('voter_id', '').strip()
        full_name = request.form.get('full_name', '').strip()
        # Voter ID must match KEV followed by 4+ digits
        if not voter_id or not full_name:
            error = "Both Voter ID and Full Name are required."
        elif not re.match(r'^KEV\d{4,}$', voter_id):
            error = "Voter ID must start with 'KEV' followed by at least 4 digits (e.g. KEV0001)."
        else:
            conn = get_db()
            exists = conn.execute('SELECT * FROM registry WHERE voter_id = ?', (voter_id,)).fetchone()
            if exists:
                error = "Voter ID already exists."
            else:
                conn.execute('INSERT INTO registry (voter_id, full_name) VALUES (?, ?)', (voter_id, full_name))
                conn.commit()
                success = f"Voter {full_name} added successfully!"
    return render_template('add_voter.html', error=error, success=success)   

# ----- ADMIN REMOVE CANDIDATE ----- #
@app.route('/admin/remove_candidate', methods=['POST'])
def remove_candidate():
    if not session.get('admin'):
        return redirect(url_for('admin'))
    voter_id = request.form.get('voter_id', '').strip()
    full_name = request.form.get('full_name', '').strip()
    conn = get_db()
    if voter_id:
        conn.execute('DELETE FROM candidates WHERE voter_id = ?', (voter_id,))
    elif full_name:
        conn.execute('DELETE FROM candidates WHERE name = ?', (full_name,))
    conn.commit()
    return redirect(url_for('add_candidate'))

# ----- ADMIN REMOVE VOTER ----- #
@app.route('/admin/remove_voter', methods=['POST'])
def remove_voter():
    if not session.get('admin'):
        return redirect(url_for('admin'))
    voter_id = request.form.get('voter_id', '').strip()
    full_name = request.form.get('full_name', '').strip()
    conn = get_db()
    if voter_id:
        conn.execute('DELETE FROM registry WHERE voter_id = ?', (voter_id,))
    elif full_name:
        conn.execute('DELETE FROM registry WHERE full_name = ?', (full_name,))
    conn.commit()
    return redirect(url_for('add_voter'))
# ----- ADMIN VIEW VOTER LIST ----- #
@app.route('/admin/voter_list')
def voter_list():
    if not session.get('admin'):
        return redirect(url_for('admin'))
    conn = get_db()
    voters = conn.execute('SELECT voter_id, full_name FROM registry').fetchall()
    return render_template('voter_list.html', voters=voters)

#  admin view results                                                                             
@app.route('/admin/results')
def results():
    if not session.get('admin'):
        return redirect(url_for('admin'))

    conn = get_db()
    results = conn.execute('''
        SELECT c.name, COUNT(v.candidate_id) as vote_count
        FROM candidates c
        LEFT JOIN votes v ON c.voter_id = v.candidate_id
        GROUP BY c.voter_id
    ''').fetchall()
    return render_template('results.html', results=results)

# ----- VOTER ----- #
@app.route('/voter', methods=['GET', 'POST'])
def voter_auth():
    if request.method == 'POST':
        voter_id = request.form.get('voter_id', '').strip()
        full_name = request.form.get('full_name', '').strip()
        if not voter_id or not full_name:
            return render_template('voter_auth.html', error="Please enter both your Voter ID and Full Name.")
        conn = get_db()
        valid = conn.execute('SELECT * FROM registry WHERE voter_id = ? AND full_name = ?', (voter_id, full_name)).fetchone()
        voted = conn.execute('SELECT * FROM votes WHERE voter_id = ?', (voter_id,)).fetchone()

        if not valid:
            return render_template('voter_auth.html', error="Voter ID and Name not recognized or do not match.")
        elif voted:
            return render_template('voter_auth.html', error="This voter has already voted.")
        else:
            return redirect(url_for('vote', voter_id=voter_id))
    return render_template('voter_auth.html')

@app.route('/vote/<voter_id>', methods=['GET', 'POST'])
def vote(voter_id):
    conn = get_db()
    # Prevent access if already voted
    voted = conn.execute('SELECT * FROM votes WHERE voter_id = ?', (voter_id,)).fetchone()
    if voted:
        return redirect(url_for('thankyou'))

    if request.method == 'POST':
        candidate_id = request.form.get('candidate_id', '').strip()
        if not candidate_id:
            candidates = conn.execute('SELECT * FROM candidates').fetchall()
            return render_template('vote.html', voter_id=voter_id, candidates=candidates, error="Please select a candidate.")
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        try:
            conn.execute('INSERT INTO votes (voter_id, candidate_id, timestamp) VALUES (?, ?, ?)',
                         (voter_id, candidate_id, timestamp))
            conn.commit()
        except sqlite3.IntegrityError:
            return render_template('vote.html', voter_id=voter_id, candidates=[], error="Vote could not be recorded.")
        return redirect(url_for('thankyou'))

    candidates = conn.execute('SELECT * FROM candidates').fetchall()
    return render_template('vote.html', voter_id=voter_id, candidates=candidates)

@app.route('/thankyou')
def thankyou():
    return render_template('thankyou.html')
@app.route('/results_json')
def results_json():
    conn = get_db()
    results = conn.execute('''
        SELECT c.name, COUNT(v.candidate_id) as vote_count
        FROM candidates c
        LEFT JOIN votes v ON c.voter_id = v.candidate_id
        GROUP BY c.voter_id
    ''').fetchall()
    data = [{'name': row['name'], 'vote_count': row['vote_count']} for row in results]
    return jsonify(data)

# ---------------- RUN ---------------- #
if __name__ == '__main__':
    app.run(debug=True)