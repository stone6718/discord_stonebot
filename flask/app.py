from flask import Flask, request, render_template, redirect, session, send_from_directory, jsonify
from discord.ext import commands
from authlib.integrations.flask_client import OAuth
import os, sys
import sqlite3, discord, threading
from oauth import OAuth

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)
import security

app = Flask(__name__, static_folder="static")
app.secret_key = os.urandom(24)

conn = sqlite3.connect("admins.db")
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS admins(
        user_id TEXT PRIMARY KEY
    )
""")
conn.commit()
conn.close()

# 디스코드 봇 설정
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

server_count = 0
server_list = []

@bot.event
async def on_ready():
    global server_count, server_list
    server_count = len(bot.guilds)
    server_list = [guild.name for guild in bot.guilds]
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print(f'Server count: {server_count}')

@app.route("/")
def index():
    return render_template("home.html")

@app.route("/support")
def support():
    return render_template("support.html")

@app.route("/tos")
def tos():
    return render_template("tos.html")

@app.route("/privacy")
def privacy():
    return render_template("privacy_policy.html")

@app.route("/static/<path:filename>")
def image(filename):
    return send_from_directory(app.static_folder, filename)

@app.route("/manage", methods=["GET"])
def manage():
    if not session:
        return redirect("/login")

    access_token = session.get("access_token")
    refresh_token = session.get("refresh_token")
    if not access_token or not refresh_token:
        return redirect("/login")

    oauth = OAuth(access_token, refresh_token)

    if session.get("is_admin"):
        user = oauth.get_user()
        print(user)
        if user is None:
            print("User not found. Requesting new tokens.")
            tokens = oauth.request_tokens()
            if tokens is None:
                return redirect("/login")

            session["access_token"] = tokens[0]
            session["refresh_token"] = tokens[1]

            user = oauth.get_user()
            if user is None:
                print("User still not found after token refresh.")
                return redirect("/login")

        print("User ID:", user.get("id"))

        conn = sqlite3.connect("admins.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM admins WHERE user_id = ?", (user.get("id"),))
        admin = cursor.fetchone()
        conn.close()

        print("Admin check result:", admin)

        if admin:
            print("User is an admin.")
            return render_template("manage.html", guilds=bot.guilds, user_id=session["user_id"], display_name=session["display_name"], avatar=session["avatar"])
        else:
            print("User is not an admin.")
            return render_template("error.html", title="접근할 수 없음", description="어드민 권한이 없습니다.")

    guilds = oauth.get_guilds()
    if guilds is None:
        print("Failed to retrieve guilds. Requesting new tokens.")
        tokens = oauth.request_tokens()
        if tokens is None:
            return redirect("/login")

        session["access_token"] = tokens[0]
        session["refresh_token"] = tokens[1]

        guilds = oauth.get_guilds()
        if guilds is None:
            print("Failed to retrieve guilds after token refresh.")
            return redirect("/login")

    admin_guilds = []
    for guild in guilds:
        ADMINISTRATOR = 0x8

        if (int(guild.get("permissions")) & ADMINISTRATOR) != ADMINISTRATOR:
            continue

        _guild = bot.get_guild(int(guild.get("id")))
        if _guild is None:
            admin_guilds.append({
                "id": guild.get("id"),
                "name": guild.get("name")
            })
            continue

        admin_guilds.append(_guild)

    print("Admin guilds found:", admin_guilds)

    return render_template("manage.html", guilds=admin_guilds, user_id=session["user_id"], display_name=session["display_name"], avatar=session["avatar"])

@app.route("/guild/<id>/users", methods=["GET"])
def guild_users(id: str):
    if not session.get("user_id") or not session.get("access_token") or not session.get("refresh_token"):
        return redirect("/login")

    access_token = session["access_token"]
    refresh_token = session["refresh_token"]
    if not access_token or not refresh_token:
        return redirect("/login")

    oauth = OAuth(access_token, refresh_token)

    admin = False
    if session["is_admin"]:
        user = oauth.get_user()
        if user == None:
            tokens = oauth.request_tokens()
            if tokens == None:
                return redirect("/login")

            session["access_token"] = tokens[0]
            session["refresh_token"] = tokens[1]

            user = oauth.get_user()
            if user == None:
                return redirect("/login")

        conn = sqlite3.connect("admins.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM admins WHERE user_id = ?", (user.get("id"),))
        admin = cursor.fetchone()
        conn.close()

    guild = bot.get_guild(int(id))
    if guild == None:
        return redirect(f"https://discord.com/oauth2/authorize?client_id={security.bot_id}&guild_id={id}&permissions=8&integration_type=0&scope=bot")

    print("guild", guild, guild.name, guild.id)
    if not admin:
        print("not an admin")
        member = guild.get_member(int(session["user_id"]))
        print("member", member, session["user_id"])
        if not member:
            print("member not found", session["user_id"])
            return render_template("error.html", title="접근할 수 없음", description="접근할 수 없는 디스코드 서버입니다. 다른 서버를 선택해주세요.")

        # 어드민 권한이 없는 경우
        if not member.guild_permissions.administrator:
            return render_template("error.html", title="접근할 수 없음", description="관리자 권한이 없습니다. 다른 서버를 선택해주세요.")

    # id는 무조건 숫자로만 이루어져 있으므로(디스코드 길드 존재를 먼저 체크) 인젝션 체크할 필요 X
    file_path = f"../database/{id}.db"
    if not os.path.isfile(file_path):
        print("file does not exist", file_path)
        return render_template("error.html", title="접근할 수 없음", description="등록되지 않은 디스코드 서버입니다. 다른 서버를 선택해주세요.")

    conn = sqlite3.connect(file_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM 경고;")
    warnings = cursor.fetchall()
    conn.close()

    users = []
    for warning in warnings:
        user_id = warning[2]
        warn_count = warning[3]
        user = bot.get_user(user_id)

        users.append({
            "display_name": None if user == None else user.global_name,
            "username": None if user == None else user.name,
            "id": user_id,
            "warn_count": warn_count
        })
        
    return render_template("guild_users.html", guild=guild, users=users, is_admin=True if admin else False, user_id=session["user_id"], display_name=session["display_name"], avatar=session["avatar"])

@app.route("/guild/<id>/commands", methods=["GET", "POST"])
def guild_commands(id: str):
    if not session.get("user_id") or not session.get("access_token") or not session.get("refresh_token"):
        return redirect("/login")

    access_token = session["access_token"]
    refresh_token = session["refresh_token"]
    if not access_token or not refresh_token:
        return redirect("/login")

    guild = bot.get_guild(int(id))
    if guild is None:
        return render_template("error.html", title="접근할 수 없음", description="접근할 수 없는 디스코드 서버입니다. 다른 서버를 선택해주세요.")

    member = guild.get_member(int(session["user_id"]))
    if not member:
        return render_template("error.html", title="접근할 수 없음", description="접근할 수 없는 디스코드 서버입니다. 다른 서버를 선택해주세요.")

    conn = sqlite3.connect("admins.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admins WHERE user_id = ?", (int(session["user_id"]),))
    admin = cursor.fetchone()
    conn.close()
    
    # 어드민 권한이 없는 경우, 개발자일 경우도 허용
    if not member.guild_permissions.administrator and admin is None:
        return render_template("error.html", title="접근할 수 없음", description="관리자 권한이 없습니다. 다른 서버를 선택해주세요.")

    # id는 무조건 숫자로만 이루어져 있으므로(디스코드 길드 존재를 먼저 체크) 인젝션 체크할 필요 X
    file_path = f"../database/{id}.db"
    if not os.path.isfile(file_path):
        print(f"파일 경로: {file_path}")
        return render_template("error.html", title="접근할 수 없음", description="등록되지 않은 디스코드 서버입니다. 다른 서버를 선택해주세요.")

    conn = sqlite3.connect(file_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT 음악기능, 경제기능, 관리기능, 유틸리티기능, 주식명령어, 코인명령어, 게임명령어, 인증, 인증_문자, 인증_이메일, 채팅관리명령어, 유저관리명령어 FROM 설정;")
    except:
        return render_template("error.html", title="접근할 수 없음", description="기능 설정이 등록되지 않은 디스코드 서버입니다. 관리자에게 문의해주세요.")

    functions = cursor.fetchone()
    conn.close()

    if request.method == "GET":
        return render_template("guild_commands.html", guild=guild, is_admin=session["is_admin"], functions=functions, user_id=session["user_id"], display_name=session["display_name"], avatar=session["avatar"])
    elif request.method == "POST":
        body = request.get_json()
        command = body.get("command")
        enabled = body.get("enabled")
        
        conn = sqlite3.connect(f"../database/{id}.db")
        cursor = conn.cursor()
        
        if command == "music":
            cursor.execute("UPDATE 설정 SET 음악기능 = ?", (1 if enabled else 0,))
        elif command == "economy":
            cursor.execute("UPDATE 설정 SET 경제기능 = ?", (1 if enabled else 0,))
        elif command == "manage":
            cursor.execute("UPDATE 설정 SET 관리기능 = ?", (1 if enabled else 0,))
        elif command == "utility":
            cursor.execute("UPDATE 설정 SET 유틸리티기능 = ?", (1 if enabled else 0,))
        elif command == "economy_stock":
            cursor.execute("UPDATE 설정 SET 주식명령어 = ?", (1 if enabled else 0,))
        elif command == "economy_coin":
            cursor.execute("UPDATE 설정 SET 코인명령어 = ?", (1 if enabled else 0,))
        elif command == "economy_game":
            cursor.execute("UPDATE 설정 SET 게임명령어 = ?", (1 if enabled else 0,))
        elif command == "manage_verify":
            cursor.execute("UPDATE 설정 SET 인증 = ?", (1 if enabled else 0,))
        elif command == "manage_verify_sms":
            cursor.execute("UPDATE 설정 SET 인증_문자 = ?", (1 if enabled else 0,))
        elif command == "manage_verify_email":
            cursor.execute("UPDATE 설정 SET 인증_이메일 = ?", (1 if enabled else 0,))
        elif command == "manage_chat":
            cursor.execute("UPDATE 설정 SET 채팅관리명령어 = ?", (1 if enabled else 0,))
        elif command == "manage_user":
            cursor.execute("UPDATE 설정 SET 유저관리명령어 = ?", (1 if enabled else 0,))
        
        conn.commit()
        conn.close()

        return "true"

@app.route("/guild/<id>/panel", methods=["GET", "POST"])
def guild_panel(id: str):
    if not session.get("user_id") or not session.get("access_token") or not session.get("refresh_token"):
        return redirect("/login")

    access_token = session["access_token"]
    refresh_token = session["refresh_token"]
    if not access_token or not refresh_token:
        return redirect("/login")

    oauth = OAuth(access_token, refresh_token)

    admin = False
    if session["is_admin"]:
        user = oauth.get_user()
        if user == None:
            tokens = oauth.request_tokens()
            if tokens == None:
                return redirect("/login")

            session["access_token"] = tokens[0]
            session["refresh_token"] = tokens[1]

            user = oauth.get_user()
            if user == None:
                return redirect("/login")

        conn = sqlite3.connect("admins.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM admins WHERE user_id = ?", (user.get("id"),))
        admin = cursor.fetchone()
        conn.close()

    if not admin:
        return redirect("/login")

    if request.method == "GET":
        conn = sqlite3.connect("../economy.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user")
        economy_users = cursor.fetchall()
        conn.close()

        users = []
        for user in economy_users:
            discord_user = bot.get_user(user[0])
            users.append({
                "id": user[0],
                "money": user[1],
                "display_name": None if discord_user == None else discord_user.global_name,
                "username": None if discord_user == None else discord_user.name,
                "disabled": user[2]
            })

        guild = bot.get_guild(int(id))
        if guild == None:
            return render_template("error.html", title="접근할 수 없음", description="접근할 수 없는 디스코드 서버입니다. 다른 서버를 선택해주세요.")

        return render_template("guild_panel.html", users=users, guild=guild, user_id=session["user_id"], display_name=session["display_name"], avatar=session["avatar"])
    elif request.method == "POST":
        body = request.get_json()
        action_type = body.get("type")
        user_id = body.get("userId")
        if action_type == "add":
            amount = body.get("amount")
            conn = sqlite3.connect("../economy.db")
            cursor = conn.cursor()
            cursor.execute("UPDATE user SET money = money + ? WHERE id = ?", (amount, user_id,))
            conn.commit()
            conn.close()
        elif action_type == "set":
            amount = body.get("amount")
            conn = sqlite3.connect("../economy.db")
            cursor = conn.cursor()
            cursor.execute("UPDATE user SET money = ? WHERE id = ?", (amount, user_id,))
            conn.commit()
            conn.close()
        elif action_type == "disable":
            disabled = body.get("disabled")
            conn = sqlite3.connect("../economy.db")
            cursor = conn.cursor()
            cursor.execute("UPDATE user SET tos = ? WHERE id = ?", (1 if disabled else 0, user_id,))
            conn.commit()
            conn.close()
        elif action_type == "remove":
            conn = sqlite3.connect("../economy.db")
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user WHERE id = ?", (user_id,))
            conn.commit()
            conn.close()
        elif action_type == "remove_guild":
            file_path = f"../database/{id}.db"
            if not os.path.isfile(file_path):
                return "false"

            os.remove(file_path)

        return "true"

@app.route("/login", methods=["GET"])
def login():
    return render_template("login.html", client_id=OAuth.get_client_id(security.token), redirect_uri=security.redirect_uri)

@app.route("/logout", methods=["POST"])
def logout():
    refresh_token = session["refresh_token"]
    if refresh_token:
        oauth = OAuth(None, refresh_token)
        oauth.revoke_tokens()

    del session["access_token"]
    del session["refresh_token"]

    return "true"

# Discord OAuth2
@app.route("/callback", methods=["GET"])
def callback():
    code = request.args.get("code")
    if not code:
        return render_template("error.html")

    oauth = OAuth()

    res = oauth.get_tokens(code)
    status = res[0]
    data = res[1]
    if not status:
        return render_template("error.html", title="로그인 오류", description="디스코드 로그인 세션이 유효하지 않습니다. 다시 로그인해주세요.")

    scope = data.get("scope")
    if "identify" not in scope or "guilds" not in scope:
        print("invalid scopes:", data.get("scope"))
        return render_template("error.html", title="로그인 오류", description="디스코드 OAuth2 스코프가 잘못 지정되어있습니다. 다시 로그인해주세요.")

    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")

    user = oauth.get_user()

    if user == None:
        return render_template("error.html", title="서버 오류", description="고객님의 디스코드 계정을 불러올 수 없습니다. 다시 로그인해주세요.")

    conn = sqlite3.connect("admins.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admins WHERE user_id = ?", (user.get("id"),))
    admin = cursor.fetchone()
    conn.close()

    session["user_id"] = user.get("id")
    session["display_name"] = user.get("global_name")
    session["avatar"] = user.get("avatar")
    session["access_token"] = access_token
    session["refresh_token"] = refresh_token
    session["is_admin"] = True if admin else False

    return redirect("/manage")

def get_db_connection():
    conn = sqlite3.connect('chat.db')
    conn.row_factory = sqlite3.Row  # 행을 딕셔너리 형태로 반환
    return conn

@app.route('/chat', methods=['GET', 'POST'])
def chat():
    if request.method == 'POST':
        username = request.json.get('username')
        message = request.json.get('message')
        
        # 데이터베이스에 저장
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO messages (username, message) VALUES (?, ?)', (username, message))
        conn.commit()
        conn.close()
        
        return jsonify({'status': 'success'}), 201
    
    elif request.method == 'GET':
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT username, message FROM messages')
        messages = cursor.fetchall()
        conn.close()
        
        return jsonify([dict(message) for message in messages])  # JSON 형태로 반환

def run_discord_bot():
    bot.run(security.token)

if __name__ == '__main__':
    # 디스코드 봇을 별도의 스레드에서 실행
    threading.Thread(target=run_discord_bot).start()

    app.run(port=5001)