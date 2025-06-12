from flask import Flask, render_template, request, redirect, flash, url_for, session
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = '1234567890w'  # Add this line
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///evoting.db'
db = SQLAlchemy(app)

# === Models ===
class Voter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    has_voted = db.Column(db.Boolean, default=False)

class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    candidate = db.Column(db.String(100))

# === Routes ===
@app.route('/')
def home():
    return render_template('home.html')  # Make sure index.html exists

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        vid = request.form.get('id')
        if not name or not vid:
            flash("Please provide both name and ID.", "error")
            return redirect(url_for('register'))
        try:
            vid = int(vid)
        except ValueError:
            flash("ID must be a number.", "error")
            return redirect(url_for('register'))
        existing = Voter.query.get(vid)
        if existing:
            flash("Already registered!", "error")
            return redirect(url_for('register'))
        db.session.add(Voter(id=vid, name=name))
        db.session.commit()
        flash("Registration successful!", "success")
        return redirect(url_for('register'))
    return render_template('register.html')

@app.route('/vote', methods=['GET', 'POST'])
def vote():
    if request.method == 'POST':
        vid = request.form.get('id')
        candidate = request.form.get('candidate')
        if not vid or not candidate:
            flash("Please provide your ID and select a candidate.", "error")
            return redirect(url_for('vote'))
        try:
            vid = int(vid)
        except ValueError:
            flash("ID must be a number.", "error")
            return redirect(url_for('vote'))
        voter = Voter.query.get(vid)
        if not voter:
            flash("Not registered.", "error")
            return redirect(url_for('vote'))
        if voter.has_voted:
            flash("You already voted.", "error")
            return redirect(url_for('vote'))
        db.session.add(Vote(candidate=candidate))
        voter.has_voted = True
        db.session.commit()
        flash("Vote cast successfully!", "success")
        return redirect(url_for('vote'))
    return render_template('vote.html')

@app.route('/results')
def results():
    from sqlalchemy import func
    results = db.session.query(Vote.candidate, func.count(Vote.id)).group_by(Vote.candidate).all()
    return render_template('results.html', results=results)

@app.route('/admin/voters', methods=['GET', 'POST'])
def admin_voters():
    if not session.get('is_admin'):
        if request.method == 'POST':
            password = request.form.get('password')
            if password == 'admin123':  # Change this to your secret password
                session['is_admin'] = True
                return redirect(url_for('admin_voters'))
            else:
                flash('You are not admin.', 'error')
        return render_template('admin_login.html')
    voters = Voter.query.all()
    return render_template('admin_voters.html', voters=voters)

@app.route('/admin/logout')
def admin_logout():
    session.pop('is_admin', None)
    flash('Logged out from admin.', 'success')
    return redirect(url_for('home'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # only runs the first time to set up DB
    app.run(debug=True)