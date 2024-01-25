from flask import Flask, render_template, flash, request, redirect, url_for, session, send_file
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_
from datetime import datetime
from utils import *
from io import BytesIO
from werkzeug.utils import secure_filename
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx'}
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///DataBase.db'
app.config['SECRET_KEY'] = 'uiht79M*(E$MY776&%V87034hulo#%&!@##)$*@%^dfhv":}{:?"4y8btuf7'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['admin'] = "admin"
app.config['admin_password'] = "admin123"

db = SQLAlchemy(app)


plagiarism_service = PlagiarismDetectionService()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    userid = db.Column(db.Integer, nullable=False)
    Fname = db.Column(db.String(50), nullable=False)
    Lname = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(100), nullable=False)
    PhoneNo = db.Column(db.String(12), nullable=False)
    Course = db.Column(db.String(5), nullable=False)
    role = db.Column(db.String(10), nullable=False)
    password = db.Column(db.String(100), nullable=False)


class AssignmentQuestionFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    file_data = db.Column(db.LargeBinary, nullable=False)
    course = db.Column(db.String(5), nullable=False)


class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    file_data = db.Column(db.LargeBinary, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship(
        'User', backref=db.backref('assignments', lazy=True))

    course = db.Column(db.String(5), nullable=False)
    timeuploaded = db.Column(db.DateTime, default=datetime.now())
    status = db.Column(db.String(15), default="Not Checked")
    comment = db.Column(db.String(500), nullable=True)
    totalmarks = db.Column(db.Integer, nullable=True)
    obtmarks = db.Column(db.Integer, nullable=True)
    plagiarism_report = db.Column(db.PickleType, nullable=True)


class AssignmentDueDate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    due_date = db.Column(db.DateTime, nullable=True)
    course = db.Column(db.String(5), nullable=True)


@app.route('/')
def home():
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    return render_template('index.html', user=user)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        role_local = request.form.get('role')
        username_local = request.form.get('username')
        userid_local = request.form.get('user_id')
        Fname_local = request.form.get('Fname')
        Lname_local = request.form.get('Lname')
        email_local = request.form.get('email')
        phoneno_local = request.form.get('phoneno')
        Course_local = request.form.get('Course')
        password_local = request.form.get('password')

        user = User(username=username_local, userid=userid_local, Fname=Fname_local,
                    Lname=Lname_local, email=email_local, PhoneNo=phoneno_local, Course=Course_local, role=role_local, password=password_local)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == app.config['admin'] and password == app.config['admin_password']:
            return redirect(url_for('admin'))
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            # Store the user's information in the session
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role

            if (user.role == "Student"):
                return redirect(url_for('dashboard'))
            else:
                return redirect(url_for('teacherdashboard'))

        else:
            # Login failed, show an error message
            error_message = "Invalid username or password."
            return render_template('login.html', error_message=error_message)
    return render_template('login.html')


@app.route('/download_assignment_question/<int:id>')
def download_assignment_question(id):
    # Get the assignment from the database
    assignmentquestionfile = AssignmentQuestionFile.query.filter_by(
        id=id).first()

    if assignmentquestionfile:
        # Set up the response headers for file download
        response = send_file(
            BytesIO(assignmentquestionfile.file_data),
            as_attachment=True,
            download_name=f'Download-{assignmentquestionfile.filename}'
        )
        return response
    else:
        # Assignment not found
        flash('Assignment not found.')
        username = session.get('username')
        user = User.query.filter_by(username=username).first()
        if user.role == "Student":
            return redirect(url_for('dashboard'))
        else:
            return redirect(url_for('teacherdashboard'))


@app.route('/admin')
def admin():
    allstudents = User.query.filter_by(role='Student').all()
    allteachers = User.query.filter_by(role='Teacher').all()
    return render_template('admin.html', allstudents=allstudents, allteachers=allteachers)


@app.route('/delete_user/<int:id>')
def deleteuser(id):
    user = User.query.filter_by(id=id).first()
    instance = user
    assignment = Assignment.query.filter_by(
        user=user).first()
    if instance:
        db.session.delete(instance)
        db.session.delete(assignment)
        db.session.commit()
    return redirect(url_for('admin'))


@app.route('/update_user/<int:id>', methods=['GET', 'POST'])
def updateuser(id):
    user = User.query.filter_by(id=id).first()
    if request.method == 'POST':
        user.role = request.form.get('role')
        user.username = request.form.get('username')
        user.userid = request.form.get('user_id')
        user.Fname = request.form.get('Fname')
        user.Lname = request.form.get('Lname')
        user.email = request.form.get('email')
        user.phoneno = request.form.get('phoneno')
        user.Course = request.form.get('Course')
        user.password = request.form.get('password')
        db.session.commit()
        return redirect(url_for('admin'))
    return render_template('Update_user.html', user_for_update=user)


@app.route('/download_assignment/<int:id>')
def download_assignment(id):
    # Get the assignment from the database
    assignment = Assignment.query.filter_by(id=id).first()

    if assignment:
        # Set up the response headers for file download
        response = send_file(
            BytesIO(assignment.file_data),
            as_attachment=True,
            download_name=f'Download-{assignment.filename}'
        )
        return response
    else:
        # Assignment not found
        flash('Assignment not found.')
        username = session.get('username')
        user = User.query.filter_by(username=username).first()
        if user.role == "Student":
            return redirect(url_for('dashboard'))
        else:
            return redirect(url_for('teacherdashboard'))


@app.route('/dashboard')
def dashboard():
    # Retrieve user information from the session
    username = session.get('username')
    if (username):
        user = User.query.filter_by(username=username).first()
        try:
            assignment = Assignment.query.filter_by(user_id=user.id).first()
        except:
            assignment = None
        try:
            assignmentquestionfile = AssignmentQuestionFile.query.filter_by(
                course=user.Course).first()
        except:
            assignmentquestionfile = None
        assignmentduedate = AssignmentDueDate.query.filter_by(
            course=user.Course).first()

        if (assignment):
            assignment.timeuploaded = assignment.timeuploaded.strftime(
                "%d-%m-%Y %I:%M:%S %p")
        timepassed = False
        if (assignmentduedate):
            timenow = datetime.now()
            if assignmentduedate and timenow > assignmentduedate.due_date:
                timepassed = True
            assignmentduedate.due_date = assignmentduedate.due_date.strftime(
                "%d-%m-%Y %I:%M:%S %p")
            return render_template('dashboard.html', user=user, assignment=assignment, assignmentquestionfile=assignmentquestionfile,  assignmentduedate=assignmentduedate, timepassed=timepassed)

    return render_template('dashboard.html', user=user, assignment=assignment)


@app.route('/teacherdashboard')
def teacherdashboard():
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    assignmentduedate = AssignmentDueDate.query.filter_by(
        course=user.Course).first()
    allassignment = Assignment.query.filter_by(course=user.Course).all()
    formatted_due_date = ""
    try:
        assignmentquestionfile = AssignmentQuestionFile.query.filter_by(
            course=user.Course).first()
    except:
        assignmentquestionfile = None
    if (assignmentduedate):
        # Store the formatted due_date in a separate variable
        formatted_due_date = assignmentduedate.due_date.strftime(
            "%d-%m-%Y %I:%M:%S %p")
    all_checked = all(assignment.status ==
                      'Checked' for assignment in allassignment)
    timepassed = False
    if (assignmentduedate):
        timenow = datetime.now()
        if assignmentduedate and timenow > assignmentduedate.due_date:
            timepassed = True

    return render_template('teacher_dashboard.html', user=user, timepassed=timepassed, all_checked=all_checked, allassignment=allassignment, assignmentquestionfile=assignmentquestionfile, assignmentduedate=assignmentduedate, formatted_due_date=formatted_due_date)


@app.route('/Markassignment/<int:id>', methods=['GET', 'POST'])
def Markassignment(id):
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    assignment = Assignment.query.filter_by(id=id).first()
    if request.method == 'POST':
        totalmark = request.form.get('totalmark')
        obtmark = request.form.get('obtmark')
        comment = request.form.get('comment')

        # Update the existing assignment
        assignment.totalmarks = totalmark
        assignment.obtmarks = obtmark
        assignment.comment = comment
        assignment.status = "Checked"

        db.session.commit()
        return redirect(url_for('teacherdashboard'))
    return render_template('markassignment.html', user=user, assignment=assignment)


@app.route('/UpdateDueDate', methods=['GET', 'POST'])
def updateduedate():
    if request.method == 'POST':
        username = session.get('username')
        duedate = request.form.get('duedate')
        duedate = datetime.strptime(duedate, "%Y-%m-%dT%H:%M")
        user = User.query.filter_by(username=username).first()

        # Try to get the existing AssignmentDueDate
        assignment_due_date = AssignmentDueDate.query.filter_by(
            course=user.Course).first()

        if assignment_due_date:
            # If it exists, update the due_date
            assignment_due_date.due_date = duedate
        else:
            # If it doesn't exist, create a new AssignmentDueDate
            assignment_due_date = AssignmentDueDate(
                due_date=duedate, course=user.Course)
            db.session.add(assignment_due_date)

        db.session.commit()

    return redirect(url_for('teacherdashboard'))


@app.route('/CheckPlagiarism/<int:id>', methods=['GET', 'POST'])
def CheckPlagiarism(id):
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    assignment1 = Assignment.query.filter_by(id=id).first()
    plagiarism_results = []
    if request.method == 'POST':
        exclude_references = request.form.get('exclude_references')
        exclude_quotes = request.form.get('exclude_quotes')

        if exclude_references == "Yes":
            exclude_references = True
        else:
            exclude_references = False

        if exclude_quotes == "Yes":
            exclude_quotes = True
        else:
            exclude_quotes = False

        all_assignments = Assignment.query.filter_by(course=user.Course).all()

        # Perform plagiarism checks

        for i, assignment2 in enumerate(all_assignments):
            if assignment1.id == assignment2.id:
                continue  # Skip comparing the same assignments

            # Check plagiarism using the plagiarism detection service
            plagiarism_percentage, plagiarism_sources = plagiarism_service.check_plagiarism(
                assignment1.file_data, assignment2.file_data, assignment1.filename, assignment2.filename, exclude_references, exclude_quotes)

            plagiarism_results.append({
                'assignment1_name': assignment1.user.Fname,
                'assignment2_name': assignment2.user.Fname,
                'percentage': plagiarism_percentage,
                'exclude_references': exclude_references,
                'exclude_quotes': exclude_quotes,
                'plagiarism_sources': plagiarism_sources
            })
        assignment1.plagiarism_report = plagiarism_results
        db.session.commit()

        # Render the plagiarism report template with results
        return render_template('PlagiarismCheck.html', id=id, user=user, plagiarism_results=plagiarism_results)
    if (not (assignment1.plagiarism_report == None)):
        plagiarism_results = assignment1.plagiarism_report
    # Render the plagiarism report template for GET requests
    return render_template('PlagiarismCheck.html', id=id, plagiarism_results=plagiarism_results, user=user)


@app.route('/plagiarism_report/<int:id>', methods=['GET', 'POST'])
def PlagiarismReport(id):
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    assignment = Assignment.query.filter_by(id=id).first()
    plagiarism_results = assignment.plagiarism_report
    return render_template('PlagiarismReport.html',  plagiarism_results=plagiarism_results, user=user)


@app.route('/profile')
def profile():
    username = session.get('username')
    user = User.query.filter_by(username=username).first()
    return render_template('profile.html', user=user)


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    # Clear session variables
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('role', None)
    return redirect(url_for('home'))


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/uploadquestionassignment', methods=['POST'])
def upload_Question_assignment():
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            username = session.get('username')
            filename = secure_filename(file.filename)
            file_data = file.read()
            # Check if the file size is greater than 16 MB
            if len(file_data) > app.config['MAX_CONTENT_LENGTH']:
                flash('File size must be 16 MB or less')
                return redirect(request.url)
            # Get the user from the session
            user = User.query.filter_by(username=username).first()
            # Create a new Assignment object and save it to the database
            assignmentQuestion = AssignmentQuestionFile(
                filename=filename, file_data=file_data, course=user.Course)

            db.session.add(assignmentQuestion)
            db.session.commit()
            return redirect(url_for('teacherdashboard'))
        else:
            flash('You can only upload .txt,.pdf and .docx file')
            return redirect(request.url)
    # If not a POST request, or if there was an issue with the upload, redirect to the dashboard
    return redirect(url_for('teacherdashboard'))


@app.route('/upload_assignment', methods=['POST'])
def upload_assignment():
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            username = session.get('username')
            filename = secure_filename(file.filename)
            file_data = file.read()
            # Check if the file size is greater than 16 MB
            if len(file_data) > app.config['MAX_CONTENT_LENGTH']:
                flash('File size must be 16 MB or less')
                return redirect(request.url)
            # Get the user from the session
            user = User.query.filter_by(username=username).first()
            # Create a new Assignment object and save it to the database
            assignment = Assignment(
                filename=filename, file_data=file_data, user=user, course=user.Course)

            db.session.add(assignment)
            db.session.commit()
            return redirect(url_for('dashboard'))
        else:
            flash('You can only upload .txt,.pdf and .docx file')
            return redirect(request.url)
    return redirect(url_for('dashboard'))


@app.route('/deleteall', methods=['POST', 'GET'])
def deleteall():
    # Check if it's a POST request
    if request.method == 'POST':
        # Get the current username from the session
        username = session.get('username')
        user = User.query.filter_by(username=username).first()

        # Check if the user is a teacher
        if user.role == 'Teacher':
            try:
                # Delete assignments
                Assignment.query.filter_by(course=user.Course).delete(
                    synchronize_session='fetch')

                # Delete assignment question files
                AssignmentQuestionFile.query.filter_by(
                    course=user.Course).delete(synchronize_session='fetch')

                # Delete due dates
                AssignmentDueDate.query.filter_by(
                    course=user.Course).delete(synchronize_session='fetch')

                # Commit the changes to the database
                db.session.commit()

                return redirect(request.url)
            except Exception as e:
                return "Error"

    # If not a POST request or an issue with the deletion, return an error
    return "Wrong Request"


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=False)
