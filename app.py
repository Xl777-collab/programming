from flask import Flask, render_template, request, jsonify
import random
import datetime

app = Flask(__name__)
user_data = {}

def log_action(action, user_id, message):
    print(f"[{action}] User ID: {user_id} - {message}")

@app.route('/')
def main_page():
    return render_template('main.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    return render_template('register.html', message="")

@app.route('/register_result', methods=['POST'])
def register_result():
    username = request.form.get('user_name')
    meter_id = request.form.get('meter_id')
    dwelling_type = request.form.get('dwelling_type')
    region = request.form.get('region')
    area = request.form.get('area')

    if not all([username, meter_id, dwelling_type, region, area]):
        return render_template('register.html', message="All fields are required!")
    
    unique_user_id = str(random.randint(100000, 999999))
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    start_time_str = f"{today} 01:00:00"

    user_data[unique_user_id] = {
        "username": username,
        "meter_id": meter_id,
        "dwelling_type": dwelling_type,
        "region": region,
        "area": area,
        "register_account_time": start_time_str,
        "meter_readings": [],
        "next_meter_update_time": start_time_str
    }

    log_action("REGISTER", unique_user_id, f"Registered user {username} with meter {meter_id}")

    return render_template('register_result.html', message=f"Successfully registered! Unique User ID: {unique_user_id}", user_id=unique_user_id, username=username, meter_id=meter_id, dwelling_type=dwelling_type, region=region, area=area)


if __name__ == '__main__':
    app.run(debug=True)