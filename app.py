from flask import Flask, render_template, request, session, redirect, url_for
import random
import datetime
import json
import os

app = Flask(__name__)
app.secret_key = "your_secret_key"
user_data = {}

def log_action(action, user_id, message):
    # 获取当前时间
    current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 日志内容
    log_entry = f"[{current_time}] [{action}] User ID: {user_id} - {message}\n"
    
    # 将日志写入本地文件
    with open("app_log.txt", "a") as log_file:
        log_file.write(log_entry)
    
    # 同时在控制台打印日志（可选）
    print(log_entry.strip())

@app.route('/')
def main_page():
    return render_template('main.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    return render_template('register.html', message="")

@app.route('/register_result', methods=['POST'])
def register_result():
    username = request.form.get('user_name').strip()
    meter_id = request.form.get('meter_id').strip()
    dwelling_type = request.form.get('dwelling_type').strip()
    region = request.form.get('region').strip()
    area = request.form.get('area').strip()

    if not all([username, meter_id, dwelling_type, region, area]):
        return render_template('register.html', message="All fields are required!")

    unique_user_id = str(random.randint(100000, 999999))
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    start_time_str = f"{today} 01:00:00"

    user_data[unique_user_id] = {
        "user_id": unique_user_id,
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

    return render_template(
        'register_result.html',
        message=f"Successfully registered!",
        user_id=unique_user_id,
        username=username,
        meter_id=meter_id,
        dwelling_type=dwelling_type,
        region=region,
        area=area
    )

@app.route('/reading', methods=['GET'])
def reading():
    return render_template('reading.html', message="")

@app.route('/upload_reading', methods=['GET', 'POST'])
def upload_reading():
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        meter_id = request.form.get('meter_id')
        date = request.form.get('date')

        if user_id not in user_data or user_data[user_id]['meter_id'] != meter_id:
            return render_template('reading.html', message="Invalid User ID or Meter ID")

        session['user_id'] = user_id
        session['meter_id'] = meter_id
        session['date'] = date

        return render_template(
            'upload_reading.html',
            user_id=user_id,
            meter_id=meter_id,
            date=date,
            latest_reading=user_data[user_id]['meter_readings'][-1] if user_data[user_id]['meter_readings'] else None
        )

    return redirect(url_for('main_page'))

@app.route('/submit_reading', methods=['POST'])
def submit_reading():
    user_id = session.get('user_id')
    meter_id = session.get('meter_id')
    date = session.get('date')

    if not user_id or not meter_id or not date:
        return "Session expired or invalid request", 400

    reading = float(request.form.get('reading'))

    if not user_data[user_id]['meter_readings']:
        # 如果是第一次上传，使用用户选择的日期的 01:00:00
        current_time = f"{date} 01:00:00"
    else:
        # 否则，基于上一次读数的时间增加 30 分钟
        last_reading_time = user_data[user_id]['meter_readings'][-1]['meter_update_time']
        current_time = (datetime.datetime.strptime(last_reading_time, '%Y-%m-%d %H:%M:%S') +
                       datetime.timedelta(minutes=30)).strftime('%Y-%m-%d %H:%M:%S')

    user_data[user_id]['meter_readings'].append({
        "meter_update_time": current_time,
        "reading": reading
    })

    # 更新下一次读数时间
    user_data[user_id]['next_meter_update_time'] = current_time

    log_action("UPLOAD_READING", user_id, f"Uploaded reading {reading} at {current_time}")

    # 检查是否是最后一次读数（23:30:00）
    if current_time.endswith("23:30:00"):
        return redirect(url_for('stop_server'))

    latest_reading = user_data[user_id]['meter_readings'][-1] if user_data[user_id]['meter_readings'] else None

    return render_template(
        'upload_reading.html',
        user_id=user_id,
        meter_id=meter_id,
        date=date,
        latest_reading=latest_reading
    )

@app.route('/stop_server', methods=['GET'])
def stop_server():
    user_id = session.get('user_id')
    meter_id = session.get('meter_id')
    date = session.get('date')

    if not user_id or not meter_id or not date:
        return "Session expired or invalid request", 400
    
    if os.path.exists('electricity_record.json'):
        with open('electricity_record.json', 'r') as file:
            existing_data = json.load(file)
    else:
        existing_data = {}

    # 更新或添加当前用户的数据
    if user_id in existing_data:
        # 如果 user_id 已存在，追加新的读数
        existing_data[user_id]['meter_readings'].extend(user_data[user_id]['meter_readings'])
    else:
        # 如果 user_id 不存在，创建新的条目
        existing_data[user_id] = {
            "user_info": {
                "user_id": user_id,  # 添加 user_id
                "username": user_data[user_id]['username'],
                "meter_id": user_data[user_id]['meter_id'],
                "dwelling_type": user_data[user_id]['dwelling_type'],
                "region": user_data[user_id]['region'],
                "area": user_data[user_id]['area'],
                "register_account_time": user_data[user_id]['register_account_time']
            },
            "meter_readings": user_data[user_id]['meter_readings']
        }

    # 写入更新后的数据到 JSON 文件
    with open('electricity_record.json', 'w') as file:
        json.dump(existing_data, file, indent=4)

    # 清空当前日期的数据
    user_data[user_id]['meter_readings'] = []

    # 更新日期为下一天的 01:00:00
    next_date = (datetime.datetime.strptime(date, '%Y-%m-%d') + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    user_data[user_id]['next_meter_update_time'] = f"{next_date} 01:00:00"

    return render_template('stop_server.html')

@app.route('/next_day', methods=['GET'])
def next_day():
    user_id = session.get('user_id')
    meter_id = session.get('meter_id')

    if not user_id or not meter_id:
        return "Session expired or invalid request", 400

    next_date = (datetime.datetime.strptime(user_data[user_id]['next_meter_update_time'], '%Y-%m-%d %H:%M:%S') +
                datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    user_data[user_id]['next_meter_update_time'] = f"{next_date} 01:00:00"

    return redirect(url_for('upload_reading'))

def recover_system():
    """ Recover system by checking and resetting necessary files if corrupted or missing. """
    
    global user_data  # Ensure we update the global variable

    # Check and recover the electricity record file
    electricity_file = "electricity_record.json"
    if not os.path.exists(electricity_file):
        print("⚠️ electricity_record.json not found. Creating a new one.")
        with open(electricity_file, "w") as f:
            json.dump({}, f)  # Create an empty JSON file
    else:
        try:
            with open(electricity_file, "r") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("Invalid JSON format")
        except (json.JSONDecodeError, ValueError):
            print("⚠️ electricity_record.json is corrupted. Resetting to empty structure.")
            with open(electricity_file, "w") as f:
                json.dump({}, f)

    # Load user data from electricity_record.json if available
    try:
        with open(electricity_file, "r") as f:
            user_data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        user_data = {}

    # Check and recover the application log file
    log_file = "app_log.txt"
    if not os.path.exists(log_file):
        print("⚠️ app_log.txt not found. Creating a new one.")
        with open(log_file, "w") as f:
            f.write("System Log Initialized\n")

    # Ensure all users in user_data have a valid structure
    for user_id, user_info in user_data.items():
        if "meter_readings" not in user_info:
            user_info["meter_readings"] = []
        if "next_meter_update_time" not in user_info:
            user_info["next_meter_update_time"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    print("✅ System Recovery Complete. Ready to Run.")


def load_json_data():
    """ 加载 JSON 数据，若损坏则重置为空 JSON，并从日志恢复 """
    json_path = 'electricity_record.json'
    log_path = 'app_log.txt'
    
    try:
        # 🚀 先检查 JSON 文件是否存在
        if not os.path.exists(json_path):
            print("⚠️ electricity_record.json 不存在，创建新文件...")
            with open(json_path, 'w') as f:
                json.dump({}, f)
            return {}

        # 🚀 读取 JSON 数据
        with open(json_path, 'r') as file:
            return json.load(file)  # ✅ JSON 格式正确，正常返回数据

    except (FileNotFoundError, json.JSONDecodeError):
        print("❌ JSON 文件损坏，尝试从日志恢复数据...")

        # 🚀 第一步：删除损坏的 JSON 并重置为空 `{}` 文件
        if os.path.exists(json_path):
            os.remove(json_path)
        
        with open(json_path, 'w') as f:
            json.dump({}, f)

        # 🚀 第二步：尝试从 `app_log.txt` 读取历史数据
        recovered_data = recover_data_from_logs(log_path)

        # 🚀 第三步：将恢复的数据写入 JSON 文件
        with open(json_path, 'w') as f:
            json.dump(recovered_data, f, indent=4)

        return recovered_data
        
def recover_data_from_logs(log_path):
    """ 从日志文件中恢复数据 """
    recovered_data = {}

    if not os.path.exists(log_path):
        print("⚠️ 没有找到日志文件，无法恢复数据")
        return recovered_data

    with open(log_path, 'r') as file:
        logs = file.readlines()

    for log in logs:
        try:
            parts = log.strip().split(" | ")
            if len(parts) < 3:
                continue  # 无效日志跳过

            timestamp, action, details = parts[0], parts[1], " | ".join(parts[2:])

            if action == "REGISTER":
                # 解析注册信息
                details_parts = details.split("Registered user ")[1].split(" with meter ")
                username = details_parts[0]
                meter_id = details_parts[1].split(" ")[0]

                # 生成 user_id（日志里没有存 user_id，所以这里随机生成）
                user_id = str(random.randint(100000, 999999))

                recovered_data[user_id] = {
                    "user_id": user_id,
                    "username": username,
                    "meter_id": meter_id,
                    "dwelling_type": "Unknown",
                    "region": "Unknown",
                    "area": "Unknown",
                    "register_account_time": timestamp,
                    "meter_readings": [],
                    "next_meter_update_time": timestamp
                }

            elif action == "UPLOAD_READING":
                # 解析电表读数日志
                details_parts = details.split("Uploaded reading ")[1].split(" at ")
                reading = float(details_parts[0])
                reading_time = details_parts[1]

                # 通过 user_id 查找用户（日志里没有 user_id 直接关联，所以使用 meter_id 匹配）
                matching_user = None
                for user in recovered_data.values():
                    if user["meter_id"] in log:
                        matching_user = user
                        break
                
                if matching_user:
                    matching_user["meter_readings"].append({
                        "meter_update_time": reading_time,
                        "reading": reading
                    })

                    # 更新 `next_meter_update_time`
                    matching_user["next_meter_update_time"] = reading_time

        except Exception as e:
            print(f"⚠️ 解析日志时发生错误: {e}")

    return recovered_data


@app.route('/daily_query', methods=['GET', 'POST'])
def daily_query():
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        meter_id = request.form.get('meter_id')

        if not user_id or not meter_id:
            return render_template('daily_query.html', message="User ID and Meter ID are required!")

        if user_id not in user_data or user_data[user_id]['meter_id'] != meter_id:
            return render_template('daily_query.html', message="Invalid User ID or Meter ID")

        # 获取 meter_readings 中的日期
        if user_data[user_id]['meter_readings']:
            # 从第一条读数中提取日期
            first_reading_time = user_data[user_id]['meter_readings'][0]['meter_update_time']
            date = first_reading_time.split(' ')[0]  # 提取日期部分（YYYY-MM-DD）
        else:
            return render_template('daily_query.html', message="No readings available for the selected user and meter")

        # 过滤出当天的读数数据
        daily_readings = [
            reading for reading in user_data[user_id]['meter_readings']
            if reading['meter_update_time'].startswith(date)
        ]

        return render_template(
            'daily_query.html',
            user_id=user_id,
            meter_id=meter_id,
            daily_readings=daily_readings,
            message=""
        )

    return render_template('daily_query.html', message="")

# 让 `/history_query` 也使用新的 `load_json_data()`
@app.route('/history_query', methods=['GET', 'POST'])
def history_query():
    json_data = load_json_data()  # ✅ 在查询前加载 JSON，并确保它没有损坏

    if request.method == 'POST':
        user_id = request.form.get('user_id')
        meter_id = request.form.get('meter_id')
        query_date = request.form.get('date')

        if not user_id or not meter_id or not query_date:
            return render_template('history_query.html', message="User ID, Meter ID, and Date are required!")

        if user_id not in json_data:
            return render_template('history_query.html', message="Invalid User ID")

        if json_data[user_id]['user_info']['meter_id'] != meter_id:
            return render_template('history_query.html', message="Invalid Meter ID")

        # 过滤出查询日期的读数数据
        daily_readings = [
            reading for reading in json_data[user_id]['meter_readings']
            if reading['meter_update_time'].startswith(query_date)
        ]

        if not daily_readings:
            return render_template('history_query.html', message=f"No data available for the date: {query_date}")

        # 获取 01:00:00 和 23:30:00 的读数
        reading_0100 = next(
            (reading['reading'] for reading in daily_readings if reading['meter_update_time'].endswith('01:00:00')),
            None
        )
        reading_2330 = next(
            (reading['reading'] for reading in daily_readings if reading['meter_update_time'].endswith('23:30:00')),
            None
        )

        if not reading_0100 or not reading_2330:
            return render_template('history_query.html', message=f"Incomplete data for the date: {query_date}")

        total_usage = reading_2330 - reading_0100

        query_result = {
            "date": query_date,
            "reading_0100": reading_0100,
            "reading_2330": reading_2330,
            "total_usage": total_usage
        }

        return render_template(
            'history_query.html',
            user_id=user_id,
            meter_id=meter_id,
            query_result=query_result,
            message=""
        )

    return render_template('history_query.html', message="")



if __name__ == '__main__':
    recover_system()
    app.run(debug=True)
