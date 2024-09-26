from flask import Flask, render_template, request, redirect, url_for
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
import random
import webview
import threading

app = Flask(__name__)

client = MongoClient('localhost', 27017 )
db = client['patient_data']
collection = db['patients']

def generate_index_code():
    return str(random.randint(1000000, 9999999))

@app.route('/')
def index():
    return render_template('form.html')

@app.route('/submit', methods=['POST'])
def submit():
    index_code = generate_index_code()
    patient_name = request.form.get('patient_name')
    patient_dob = request.form.get('patient_dob')
    patient_sex = request.form.get('patient_sex')
    contact = request.form.get('contact')
    attending = request.form.get('attending')
    blood_group = request.form.get('blood_group')
    height = request.form.get('height')
    weight = request.form.get('weight')
    consultation = request.form.get('consultation')
    vaccine = request.form.get('vaccine')
    applied_doses = request.form.getlist('applied_doses') or 'NA'
    notes = request.form.get('notes') or 'NA'  # Fill with 'NA' if empty
    
    now = datetime.now()
    date = now.strftime('%Y-%m-%d')
    time = now.strftime('%H:%M:%S')

    patient_data = {
        'index_code': index_code,
        'patient_name': patient_name,
        'patient_dob': patient_dob,
        'patient_sex': patient_sex,
        'contact': contact,
        'attending': attending,
        'blood_group': blood_group,
        'height': height,
        'weight': weight,
        'consultation': consultation,
        'vaccine': vaccine,
        'applied_doses': applied_doses,
        'notes': notes,
        'date': date,
        'time': time
    }

    collection.insert_one(patient_data)
    return redirect(url_for('report', patient_id=str(patient_data['_id'])))

def calculate_age(dob, ref_date):
    dob = datetime.strptime(dob, "%Y-%m-%d")
    ref_date = datetime.strptime(ref_date, "%Y-%m-%d")
    age = ref_date.year - dob.year - ((ref_date.month, ref_date.day) < (dob.month, dob.day))
    return age

@app.route('/show_data', methods=['GET', 'POST'])
def show_data():
    query = {}
    if request.method == 'POST':
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        blood_group = request.form.get('blood_group')
        
        if start_date and end_date:
            query['date'] = {'$gte': start_date, '$lte': end_date}
        
        if blood_group:
            query['blood_group'] = blood_group
        
        if not start_date and not end_date and not blood_group:
            search_term = request.form.get('search')
            if search_term:
                query = {
                    '$or': [
                        {'index_code': {'$regex': search_term, '$options': 'i'}},
                        {'patient_name': {'$regex': search_term, '$options': 'i'}},
                        {'contact': {'$regex': search_term, '$options': 'i'}}
                    ]
                }

    patients = list(collection.find(query))

    for patient in patients:
        patient['age'] = calculate_age(patient['patient_dob'], patient['date'])

    # Calculate the number of unique index codes
    unique_index_codes = len(set(patient['index_code'] for patient in patients))

    total_entries = len(patients)
    attending_present = sum(1 for patient in patients if patient.get('attending'))
    patients_male = sum(1 for patient in patients if patient.get('patient_sex') == 'male')
    patients_female = sum(1 for patient in patients if patient.get('patient_sex') == 'female')
    patients_other = sum(1 for patient in patients if patient.get('patient_sex') == 'other')

    summary_data = {
        'total_entries': total_entries,
        'attending_present': attending_present,
        'patients_male': patients_male,
        'patients_female': patients_female,
        'patients_other': patients_other,
        'unique_index_codes': unique_index_codes  # Add unique index codes to summary data
    }

    return render_template('table.html', patients=patients, summary=summary_data)



@app.route('/delete/<string:patient_id>', methods=['POST'])
def delete_patient(patient_id):
    collection.delete_one({'_id': ObjectId(patient_id)})
    return redirect(url_for('show_data'))

@app.route('/update_patient/<patient_id>', methods=['GET', 'POST'])
def update_patient(patient_id):
    if request.method == 'POST':
        updated_data = {
            'index_code': request.form['index_code'],  # Keep index code unchanged
            'patient_name': request.form['patient_name'],
            'patient_dob': request.form['patient_dob'],
            'patient_sex': request.form['patient_sex'],
            'contact': request.form['contact'],
            'attending': request.form['attending'],
            'blood_group': request.form['blood_group'],
            'height': request.form['height'],
            'weight': request.form['weight'],
            'consultation': request.form['consultation'],
            'vaccine': request.form['vaccine'],
            'applied_doses': request.form.getlist('applied_doses'),
            'notes': request.form.get('notes'),
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': datetime.now().strftime('%H:%M:%S')
        }

        collection.update_one({'_id': ObjectId(patient_id)}, {'$set': updated_data})
        return redirect(url_for('show_data'))
    else:
        patient = collection.find_one({'_id': ObjectId(patient_id)})
        return render_template('update.html', patient=patient)

@app.route('/report/<string:patient_id>')
def report(patient_id):
    patient = collection.find_one({'_id': ObjectId(patient_id)})
    patient['age'] = calculate_age(patient['patient_dob'], patient['date'])
    return render_template('report.html', patient=patient)

@app.route('/view/<string:patient_id>')
def view_patient(patient_id):
    patient = collection.find_one({'_id': ObjectId(patient_id)})
    patient['age'] = calculate_age(patient['patient_dob'], patient['date'])
    return render_template('report.html', patient=patient)

@app.route('/copy_patient/<string:patient_id>', methods=['POST'])
def copy_patient(patient_id):
    patient = collection.find_one({'_id': ObjectId(patient_id)})
    patient_data = {
        'index_code': patient['index_code'],
        'patient_name': patient['patient_name'],
        'patient_dob': patient['patient_dob'],
        'patient_sex': patient['patient_sex'],
        'contact': patient['contact'],
        'attending': patient['attending'],
        'blood_group': patient['blood_group'],
        'height': patient['height'],
        'weight': patient['weight'],
        'consultation': patient['consultation'],
        'vaccine': patient['vaccine'],
        'applied_doses': patient['applied_doses'],
        'notes': patient['notes'],
        'date': patient['date'],  # Keep the same date
        'time': patient['time']    # Keep the same time
    }
    collection.insert_one(patient_data)
    return redirect(url_for('show_data'))

def start_flask():
    app.run()

if __name__ == '__main__':
    threading.Thread(target=start_flask).start()
    
    webview.create_window('Patient Data Collection', 'http://127.0.0.1:5000')
    webview.start() 




