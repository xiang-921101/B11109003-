from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
import os
from datetime import datetime
from app_changelog import CHANGELOG_DATA

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.secret_key = "CloudSecretKey1205"  # 記得改成安全隨機字串
users_db = {}

# app.py (替換 /index 路由)
@app.route("/", methods=["GET", "POST"])
def index():
    today_date = datetime.now().strftime("%Y-%m-%d") # 取得今天的日期
    
    if request.method == "POST":
        choice = request.form.get("choice")
        name = request.form.get("username")
        if name:
            session['temp_username'] = name
            
            # 確保使用者資料存在
            if name not in users_db:
                users_db[name] = {
                    "diary": [], 
                    "photos": [], 
                    "avatar": "default_avatar.png", 
                    "password": "",
                    "nickname": name,
                    "start_date": today_date # ⭐ 第一次進入，記錄開始日期 ⭐
                }
            elif 'nickname' not in users_db[name]:
                 users_db[name]['nickname'] = name
                 
            # 如果是舊資料，但沒有 start_date，則補上今天的日期
            if 'start_date' not in users_db[name]:
                 users_db[name]['start_date'] = today_date
                 
            return redirect(url_for("home"))
        return render_template("index.html", choice=choice)
    return render_template("index.html", choice=None)

@app.route("/register", methods=["POST"])
def register():
    username = request.form.get("username")
    password = request.form.get("password")
    today_date = datetime.now().strftime("%Y-%m-%d") # 取得今天的日期
    
    if not username or not password:
        return "帳號或密碼不能為空"
    
    if username in users_db:
        return "帳號已存在！"

    initial_nickname = session.pop('temp_username', username) 
    
    # 創建新帳號資料
    users_db[username] = {
        "password": password,
        "diary": [],
        "photos": [],
        "avatar": "default_avatar.png",
        "nickname": initial_nickname,
        "start_date": today_date # ⭐ 註冊時，記錄開始日期 ⭐
    }
    
    return "註冊成功"

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        if username in users_db and users_db[username].get("password") == password and users_db[username].get("password") != "":
            session['logged_in'] = True
            session['username'] = username 
            
            # ⭐ 關鍵：登入成功時，清除任何臨時暱稱 ⭐
            session.pop('temp_username', None) 
            
            # 兼容性檢查：確保正式帳號也有 nickname 欄位
            if 'nickname' not in users_db[username]:
                 users_db[username]['nickname'] = username
            
            return redirect(url_for("home"))
        else:
            return "帳號不存在或密碼錯誤"
    return render_template("login.html")

# app.py (替換 /home 路由)
@app.route("/home", methods=["GET","POST"])
def home():
    username = session.get("username") or session.get("temp_username")
    if not username:
        return redirect(url_for("login"))
        
    user_data = users_db.get(username, {"diary": [], "photos": [], "avatar": "default_avatar.png", "password": ""})
    
    # ⭐ 獲取今天的任務ID、完成狀態、diffDays、文字和照片 ⭐
    today_id, is_completed, diff_days, existing_text, existing_photos = get_current_task_info(user_data)
    
    # 傳遞所有關鍵資訊到前端
    return render_template("home.html", 
                           username=username, 
                           is_logged_in=session.get("logged_in", False),
                           task_id=today_id,             
                           is_completed=is_completed,    
                           diff_days=diff_days,
                           existing_text=existing_text,    # ⭐ 傳遞已儲存的文字 ⭐
                           existing_photos=existing_photos) # ⭐ 傳遞已儲存的照片路徑 ⭐

@app.route("/upload", methods=["POST"])
def upload():
    username = session.get("username") or session.get("temp_username")
    if not username:
        return redirect(url_for("login"))

    # 確保使用者資料存在
    if username not in users_db:
        users_db[username] = {"diary": [], "photos": [], "avatar": "default_avatar.png", "password": ""}

    text = request.form.get("text")
    files = request.files.getlist("photos")
    photo_paths = []

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    for file in files:
        if file.filename:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)
            photo_paths.append('uploads/' + file.filename)

    users_db[username]["diary"].append({
        "date": datetime.now().strftime("%Y-%m-%d"),
        "text": text,
        "photos": photo_paths
    })

    return redirect(url_for("profile"))

@app.route("/profile")
def profile():
    # 1. 決定資料庫的鍵 (Account Key)：從正式帳號或臨時名稱中取得
    account_key = session.get("username") or session.get("temp_username") 
    
    # 2. 決定正式帳號名稱 (Formal Account Name)：只有透過 /login 登入的才會有
    formal_account_name = session.get("username") 
    
    # 判斷是否為正式登入使用者 (用於顯示更改密碼/暱稱等功能)
    is_logged_in = bool(session.get("logged_in") and formal_account_name)

    if not account_key or account_key not in users_db:
        # 如果找不到帳號，顯示預設值
        avatar_url = None
        history = []
        display_nickname = "好心人" 
    else:
        user_data = users_db[account_key]
        avatar_url = user_data.get('avatar', 'default_avatar.png')
        history = user_data.get('diary', [])
        
        # 3. 決定顯示的暱稱 (Display Nickname)：優先使用 nickname 欄位，否則使用 account_key
        display_nickname = user_data.get('nickname', account_key)
        
        history.reverse() 

    # 將兩個獨立的變數傳遞給 profile.html
    return render_template("profile.html",
                           display_nickname=display_nickname,  # 暱稱 (index.html輸入的名字會在這裡顯示)
                           formal_account_name=formal_account_name, # 正式帳號名稱 (若為臨時帳號則為 None)
                           avatar_url=avatar_url,
                           history=history,
                           is_logged_in=is_logged_in)

@app.route("/update_avatar", methods=["POST"])
def update_avatar():
    username = session.get("username")
    if not username:
        return redirect(url_for("login"))
    if username not in users_db:
        users_db[username] = {"diary": [], "photos": [], "avatar": "default_avatar.png", "password": ""}

    file = request.files.get("avatar")
    if file:
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)
        users_db[username]['avatar'] = 'uploads/' + file.filename
    return redirect(url_for("profile"))

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route("/change_password", methods=["GET","POST"])
def change_password():
    username = session.get("username")
    if not username:
        return redirect(url_for("login"))
    if username not in users_db:
        # 確保資料存在，雖然這行在實際應用中很少觸發，但保留下來
        users_db[username] = {"diary": [], "photos": [], "avatar": "default_avatar.png", "password": ""}

    if request.method == "POST":
        old1 = request.form.get("old1")
        old2 = request.form.get("old2")
        new1 = request.form.get("new1") # 取得第一次新密碼
        new2 = request.form.get("new2") # 取得第二次新密碼
        
        # 1. 檢查兩次舊密碼是否一致
        if old1 != old2:
            return "舊密碼兩次輸入不一致"
        
        # 2. 檢查舊密碼是否正確
        if users_db[username].get("password") != old1:
            return "舊密碼錯誤"
        
        # ⭐ 3. 檢查兩次新密碼是否一致 (新增邏輯) ⭐
        if new1 != new2:
            return "新密碼兩次輸入不一致"
            
        # 4. 檢查新密碼是否為空
        if not new1:
            return "新密碼不能為空"

        users_db[username]['password'] = new1
        return "密碼更改成功" 
        
    return render_template("change_password.html")

@app.route("/save_task", methods=["POST"])
def save_task():
    username = session.get("username") or session.get("temp_username")
    if not username:
        return redirect(url_for("login"))
    if username not in users_db:
        users_db[username] = {"diary": [], "photos": [], "avatar": "default_avatar.png", "password": ""}

    task = request.form.get("task_title")
    text = request.form.get("text")
    photos = request.files.getlist("photos")
    
    # 獲取今天的日期ID
    today_date_str = datetime.now().strftime("%Y-%m-%d")

    photo_paths = []
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    for file in photos:
        if file.filename:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            # 為了簡單，這裡我們覆蓋同名的檔案
            file.save(filepath) 
            photo_paths.append('uploads/' + file.filename)

    # ⭐ 覆蓋或新增邏輯 ⭐
    is_updated = False
    
    # 1. 檢查是否需要覆蓋現有紀錄 (即今天已完成過)
    for i, entry in enumerate(users_db[username]["diary"]):
        entry_date_str = entry.get("date", "").split(" ")[0]
        if entry_date_str == today_date_str:
            # 覆蓋舊紀錄
            users_db[username]["diary"][i] = {
                "task": task,
                "text": text,
                "photo": photo_paths,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M") # 更新時間戳
            }
            is_updated = True
            break
            
    # 2. 如果沒有覆蓋，則新增紀錄
    if not is_updated:
        users_db[username]["diary"].append({
            "task": task,
            "text": text,
            "photo": photo_paths,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M")
        })
        
    return redirect(url_for("profile"))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory('uploads', filename)

@app.route('/save_post', methods=['POST'])
def save_post():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    text = request.form['text']

    # 讀取 existing uploads
    file = request.files.get('image')
    image_url = None

    if file and file.filename != '':
        filename = file.filename
        file.save(os.path.join('uploads', filename))
        image_url = f"/uploads/{filename}"

    users_db[username]['history'].append({
        'text': text,
        'image': image_url
    })

    return redirect(url_for('profile'))

@app.route("/change_nickname", methods=["POST"])
def change_nickname():
    # 只有正式登入的 session['username'] 才能更改暱稱
    username = session.get("username") 
    if not username or username not in users_db:
        return "請先登入正式帳號"
    
    new_nickname = request.form.get("nickname")
    if new_nickname and new_nickname.strip():
        users_db[username]['nickname'] = new_nickname.strip()
        return "暱稱更改成功"
    return "新暱稱不能為空"

# app.py (替換 get_current_task_info 函式)
def get_current_task_info(user_data):
    today = datetime.now().date()
    today_date_str = today.strftime("%Y-%m-%d")
    
    start_date_str = user_data.get('start_date', today_date_str)
    
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    except ValueError:
        start_date = today

    diffDays = (today - start_date).days
    
    is_completed_today = False
    
    # ⭐ 新增：用於儲存已完成的文字和照片 ⭐
    existing_text = ""
    existing_photos = [] 
    
    for entry in user_data.get("diary", []):
        entry_date_str = entry.get("date", "").split(" ")[0]
        if entry_date_str == today_date_str:
            is_completed_today = True
            existing_text = entry.get("text", "")
            existing_photos = entry.get("photo", [])
            break # 找到今天的紀錄，停止遍歷
            
    # ⭐ 返回新增的兩個欄位 ⭐
    return today_date_str, is_completed_today, diffDays, existing_text, existing_photos

# app.py (新增 /diary 路由)
# 替換您的 /diary 路由
@app.route("/diary")
def diary():
    # 這裡無需檢查登入狀態，因為日誌是給所有人看的
    return render_template("diary.html",
                           changelog=CHANGELOG_DATA)

if __name__ == "__main__":
    app.run(debug=True)