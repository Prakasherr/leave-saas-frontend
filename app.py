from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import pandas as pd
from io import BytesIO
from flask import send_file


app = Flask(__name__)
CORS(app)  # Allow frontend access
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)

# User table
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(120))
    role = db.Column(db.String(20))  # 'admin' or 'employee'

# Leave table
class Leave(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    start_date = db.Column(db.String(20))
    end_date = db.Column(db.String(20))
    leave_type = db.Column(db.String(20))
    reason = db.Column(db.String(255))
    status = db.Column(db.String(20))  # pending, approved, rejected

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    user = User(name=data['name'], email=data['email'], password=data['password'], role='employee')
    db.session.add(user)
    db.session.commit()
    return jsonify({"message": "User registered"}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(email=data['email'], password=data['password']).first()
    if user:
        return jsonify({"message": "Login successful", "user": {"id": user.id, "role": user.role}})
    else:
        return jsonify({"message": "Invalid credentials"}), 401

@app.route('/leave/apply', methods=['POST'])
def apply_leave():
    data = request.json
    leave = Leave(
        user_id=data['user_id'],
        start_date=data['start_date'],
        end_date=data['end_date'],
        leave_type=data['leave_type'],
        reason=data['reason'],
        status='pending'
    )
    db.session.add(leave)
    db.session.commit()
    return jsonify({"message": "Leave request submitted"}), 201

@app.route('/admin/requests', methods=['GET'])
def view_requests():
    leaves = Leave.query.all()
    result = []
    for l in leaves:
        user = User.query.get(l.user_id)
        result.append({
            "id": l.id,
            "name": user.name if user else "Unknown",
            "start_date": l.start_date,
            "end_date": l.end_date,
            "leave_type": l.leave_type,
            "status": l.status
        })
    return jsonify(result)

@app.route('/leave/status')
def leave_status():
    email = request.args.get("email")
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify([])

    leaves = Leave.query.filter_by(user_id=user.id).all()
    return jsonify([
        {
            "start_date": l.start_date,
            "end_date": l.end_date,
            "leave_type": l.leave_type,
            "status": l.status
        } for l in leaves
    ])

@app.route("/admin/export/excel")
def export_excel():
    leaves = Leave.query.all()
    data = [{
        "Name": User.query.get(l.user_id).name,
        "Start Date": l.start_date,
        "End Date": l.end_date,
        "Type": l.leave_type,
        "Status": l.status
    } for l in leaves]

    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Leaves')
    output.seek(0)

    return send_file(output, as_attachment=True,
                     download_name="leave_report.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@app.route('/admin/requests/<int:id>', methods=['PUT'])
def update_status(id):
    data = request.json
    leave = Leave.query.get(id)
    leave.status = data['status']  # approved/rejected
    db.session.commit()
    return jsonify({"message": "Status updated"})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create tables
    app.run(debug=True)
