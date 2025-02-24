import json, smtplib, os, openai, pytz, random
import aiosqlite, disnake, requests, aiohttp
import security as sec
from datetime import datetime
from googletrans import Translator
from email.utils import formatdate
from email.mime.text import MIMEText
from email.headerregistry import Address
from email.mime.multipart import MIMEMultipart
from discord_webhook.webhook import DiscordWebhook

embedcolor = 0xff00ff
embedwarning = 0xff9900
embedsuccess = 0x00ff00
embederrorcolor = 0xff0000

cooldown_file = "system_database/cooldowns.txt"
smtp_server = sec.smtp_server
smtp_user = sec.smtp_user
smtp_password = sec.smtp_password

nice_api_key = sec.nice_api_key

async def tos(ctx):
    db_path = os.path.join('system_database', 'economy.db')
    async with aiosqlite.connect(db_path) as conn:
        async with conn.execute("SELECT tos FROM user WHERE id = ?", (ctx.author.id,)) as cursor:
            row = await cursor.fetchone()
            if row and row[0] == 1:
                embed = disnake.Embed(color=embederrorcolor)
                embed.add_field(name="❌ 오류", value="명령어 사용이 제한된 사용자입니다.")
                await ctx.send(embed=embed, ephemeral=True)
                return False
            return True
        
async def inspection(ctx):
    embed = disnake.Embed(color=embederrorcolor)
    embed.add_field(name="❌ 오류", value="해당 기능은 점검중입니다.\n개발자에게 문의해주세요.")
    await ctx.send(embed=embed, ephemeral=True)
    return False

async def limit(ctx):
    embed = disnake.Embed(color=embederrorcolor)
    embed.add_field(name="❌ 오류", value="해당 기능은 사용제한된 명령어입니다.\n개발자에게 문의해주세요.")
    await ctx.send(embed=embed, ephemeral=True)
    return False

async def send_webhook_message(content):
    embed = disnake.Embed(title="스톤봇 로그", description=content, color=embedcolor)
    async with aiohttp.ClientSession() as session:
        webhook = disnake.Webhook.from_url(sec.WEBHOOK_URL, session=session)
        await webhook.send(embed=embed)

async def command_use_log(ctx, command, command_value):
    db_path = os.path.join('system_database', 'log.db')
    economy_aiodb = await aiosqlite.connect(db_path)
    # 한국 표준시(KST) 타임존 가져오기
    kst = pytz.timezone('Asia/Seoul')
    # 현재 시간을 KST로 가져오기
    current_time = datetime.now(kst).isoformat()
    
    # 서버 ID와 사용자 ID 가져오기
    guild_id = ctx.guild.id
    user_id = ctx.author.id

    aiocursor = await economy_aiodb.execute("INSERT INTO command (guild_id, id, command, value, time) VALUES (?, ?, ?, ?, ?)", (guild_id, user_id, command, command_value, current_time))
    await economy_aiodb.commit()
    await aiocursor.close()
    await send_webhook_message(f"서버 : {guild_id}\n사용자 : {user_id}\n명령어 : {command}\n value : {command_value}")

async def economy_log(ctx, command, result, money):
    db_path = os.path.join('system_database', 'log.db')
    economy_aiodb = await aiosqlite.connect(db_path)
    # 한국 표준시(KST) 타임존 가져오기
    kst = pytz.timezone('Asia/Seoul')
    # 현재 시간을 KST로 가져오기
    current_time = datetime.now(kst).isoformat()
    
    # 서버 ID와 사용자 ID 가져오기
    guild_id = ctx.guild.id
    user_id = ctx.author.id
    
    aiocursor = await economy_aiodb.execute("INSERT INTO economy (guild_id, id, command, result, money, time) VALUES (?, ?, ?, ?, ?, ?)", (guild_id, user_id, command, result, money, current_time))
    await economy_aiodb.commit()
    await aiocursor.close()
    await send_webhook_message(f"서버 : {guild_id}\n사용자 : {user_id}\n명령어 : {command}\n결과 : {result}\n금액 : {money}")

# 급식 정보를 캐싱하기 위한 딕셔너리
meal_cache = {}        # 급식메뉴
calorie_cache = {}     # 칼로리
school_code_cache = {} # 학교정보
nutrition_cache = {}   # 영양정보
origin_cache = {}      # 원산지정보

# 학교 코드를 찾는 함수
def find_school_code(school_name, edu_office_code):
    # 캐시에서 학교 코드를 확인하고 없으면 API 요청을 보냄
    if (school_name, edu_office_code) in school_code_cache:
        return school_code_cache[(school_name, edu_office_code)]
    
    # 학교 정보 찾기
    url = "https://open.neis.go.kr/hub/schoolInfo"
    params = {
        'KEY': nice_api_key,
        'ATPT_OFCDC_SC_CODE': edu_office_code,
        'SCHUL_NM': school_name,
        'Type': 'json'
    }

    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        if 'schoolInfo' in data:
            schools = data['schoolInfo'][1]['row']
            for school in schools:
                if school['SCHUL_NM'] == school_name:
                    # 학교 코드를 캐시에 저장하고 반환
                    school_code_cache[(school_name, edu_office_code)] = school['SD_SCHUL_CODE']
                    return school['SD_SCHUL_CODE']
            return None
        else:
            raise Exception("학교 정보를 찾을 수 없습니다.")
    else:
        raise Exception(f"API request failed with status code {response.status_code}: {response.text}")

# 급식 정보를 얻는 비동기 함수
async def get_meal_info_async(school_name, edu_office_code, date):
    school_code = find_school_code(school_name, edu_office_code)
    # 학교 코드가 없을 때
    if not school_code:
        raise Exception("학교 코드를 찾을 수 없습니다.")

    # 캐시에서 급식 정보를 확인하고, 없으면 API 요청을 보냄
    if (school_name, edu_office_code, date) in meal_cache:
        return meal_cache[(school_name, edu_office_code, date)]
    
    # 급식 메뉴 찾기
    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    params = {
        'KEY': nice_api_key,
        'ATPT_OFCDC_SC_CODE': edu_office_code,
        'SD_SCHUL_CODE': school_code,
        'MLSV_YMD': date,
        'Type': 'json'
    }
    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        if 'mealServiceDietInfo' in data:
            meals = data['mealServiceDietInfo'][1]['row']
            meal_date = date
            # 급식 정보를 캐시에 저장하고 반환
            # meal_info에 급식 정보가 담겨있음
            meal_info = '\n'.join([meal['DDISH_NM'].replace('<br/>', '\n') for meal in meals])
            meal_cache[(school_name, edu_office_code, date)] = (meal_info, meal_date)
            return meal_info, meal_date
        else:
            # 급식 정보가 없다면
            return "급식 정보가 없습니다.", date
    else:
        raise Exception(f"API request failed with status code {response.status_code}: {response.text}")

# 칼로리 정보를 얻는 비동기 함수
async def get_calorie_info_async(school_name, edu_office_code, date):
    school_code = find_school_code(school_name, edu_office_code)
    if not school_code:
        raise Exception("학교 코드를 찾을 수 없습니다.")

    # 캐시에서 칼로리 정보를 확인하고, 없으면 API 요청을 보냄
    if (school_name, edu_office_code, date) in calorie_cache:
        return calorie_cache[(school_name, edu_office_code, date)]
    
    # 칼로리 찾기
    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    params = {
        'KEY': nice_api_key,
        'ATPT_OFCDC_SC_CODE': edu_office_code,
        'SD_SCHUL_CODE': school_code,
        'MLSV_YMD': date,
        'Type': 'json'
    }
    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        if 'mealServiceDietInfo' in data:
            meals = data['mealServiceDietInfo'][1]['row']
            meal_date = date
            # 칼로리 정보를 캐시에 저장하고 반환
            # calorie_info에 칼로리 값이 있음
            calorie_info = '\n'.join([meal['CAL_INFO'] for meal in meals])
            calorie_cache[(school_name, edu_office_code, date)] = (calorie_info, meal_date)
            return calorie_info, meal_date
        else:
            return "칼로리 정보가 없습니다.", date
    else:
        raise Exception(f"API request failed with status code {response.status_code}: {response.text}")

# 원산지 정보를 얻는 비동기 함수
async def get_origin_info_async(school_name, edu_office_code, date):
    school_code = find_school_code(school_name, edu_office_code)
    if not school_code:
        raise Exception("학교 코드를 찾을 수 없습니다.")

    # 캐시에서 원산지 정보를 확인하고, 없으면 API 요청을 보냄
    if (school_name, edu_office_code, date) in origin_cache:
        return origin_cache[(school_name, edu_office_code, date)]
    
    # 원산지 정보 찾기
    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    params = {
        'KEY': nice_api_key,
        'ATPT_OFCDC_SC_CODE': edu_office_code,
        'SD_SCHUL_CODE': school_code,
        'MLSV_YMD': date,
        'Type': 'json'
    }
    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        if 'mealServiceDietInfo' in data:
            meals = data['mealServiceDietInfo'][1]['row']
            origin_info = '\n'.join([meal.get('ORPLC_INFO', '원산지 정보 없음') for meal in meals])
            # 원산지 정보를 캐시에 저장하고 반환
            origin_cache[(school_name, edu_office_code, date)] = origin_info
            return origin_info
        else:
            return "급식 정보가 없습니다."
    else:
        raise Exception(f"API request failed with status code {response.status_code}: {response.text}")

# 영양 정보를 얻는 비동기 함수
async def get_nutrition_info_async(school_name, edu_office_code, date):
    school_code = find_school_code(school_name, edu_office_code)
    if not school_code:
        raise Exception("학교 코드를 찾을 수 없습니다.")

    # 캐시에서 영양 정보를 확인하고, 없으면 API 요청을 보냄
    if (school_name, edu_office_code, date) in nutrition_cache:
        return nutrition_cache[(school_name, edu_office_code, date)]
    
    # 영양 정보 찾기
    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    params = {
        'KEY': nice_api_key,
        'ATPT_OFCDC_SC_CODE': edu_office_code,
        'SD_SCHUL_CODE': school_code,
        'MLSV_YMD': date,
        'Type': 'json'
    }
    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        if 'mealServiceDietInfo' in data:
            meals = data['mealServiceDietInfo'][1]['row']
            nutrition_info = '\n'.join([meal.get('NTR_INFO', '영양 정보 없음') for meal in meals])
            # 영양 정보를 캐시에 저장하고 반환
            nutrition_cache[(school_name, edu_office_code, date)] = nutrition_info
            return nutrition_info
        else:
            return "급식 정보가 없습니다."
    else:
        raise Exception(f"API request failed with status code {response.status_code}: {response.text}")

async def handle_database(ctx, kind: str, id: int, is_role: bool = False):
    db_path = os.path.join(os.getcwd(), "database", f"{ctx.guild.id}.db")
    if not os.path.exists(db_path):
        await database_create(ctx)
    
    aiodb = await aiosqlite.connect(db_path)
    async with aiodb.execute("SELECT * FROM 설정") as aiocursor:
        dat = await aiocursor.fetchall()

    if not dat:
        query = f"INSERT INTO 설정 ({kind}) VALUES (?)"
    else:
        query = f"UPDATE 설정 SET {kind} = ?"

    async with aiodb.execute(query, (id,)) as aiocursor:
        await aiodb.commit()

    embed = disnake.Embed(color=embedsuccess)
    if is_role:
        embed.add_field(name="역할설정", value=f"<@&{id}>이(가) **{kind}**로 설정되었습니다")
    else:
        embed.add_field(name="채널설정", value=f"{id}이(가) **{kind}**로 설정되었습니다")
    
    return embed

def translate_product(df):
    translator = Translator()
    df['Trans_result'] = df['Before_Trans'].apply(lambda x: translator.translate(x, dest='en').text)
    df['Language'] = df['Before_Trans'].apply(lambda x: translator.detect(x).lang)
    return df

openai.api_key = sec.OpenAI_api_key

def get_gpt_response(prompt, model):
    try:
        # API 호출
        response = openai.ChatCompletion.create(
            model=model,  # 선택한 모델을 사용합니다.
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # 응답에서 텍스트 추출
        answer = response['choices'][0]['message']['content']
        return answer
    
    except Exception as e:
        return f"오류 발생: {str(e)}"

def generate_image(prompt):
    text = prompt
    translator = Translator()
    result= translator.translate(text, src='ko' ,dest='en')
    translated_text = result.text
    prompt = str(translated_text)
    try:
        # DALL·E API 호출
        response = openai.Image.create(
            prompt=prompt,
            n=1,
            size="1024x1024",  # 이미지 크기 설정
        )
        
        # 이미지 URL 추출
        image_url = response['data'][0]['url']
        return image_url
    
    except Exception as e:
        return f"오류 발생: {str(e)}"

async def get_user_credit(user_id):
    # 데이터베이스 경로 설정
    db_path = os.path.join('system_database', 'membership.db')
    try:
        # 데이터베이스 연결
        async with aiosqlite.connect(db_path) as conn:
            # 사용자 크레딧 조회 쿼리 실행
            async with conn.execute("SELECT credit FROM user WHERE id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                # 결과가 있으면 크레딧 반환, 없으면 0 반환
                return row[0] if row else 0
            await conn.commit()
    except aiosqlite.Error as e:
        # 오류 발생 시 메시지 출력
        print(f"Database error: {e}")
        return 0  # 오류 발생 시 기본값으로 0 반환

# 사용자에게 크레딧을 부여하는 함수
async def add_user_credit(user_id, amount):
    db_path = os.path.join('system_database', 'membership.db')
    async with aiosqlite.connect(db_path) as conn:
        # 사용자 존재 여부 확인
        async with conn.execute("SELECT credit FROM user WHERE id = ?", (user_id,)) as cursor:
            user_data = await cursor.fetchone()
        
        if user_data is None:
            # 사용자 데이터가 없다면 추가
            await conn.execute("INSERT INTO user (id, class, expiration_date, credit) VALUES (?, ?, ?, ?)", (user_id, 0, None, amount))
        else:
            # 사용자 데이터가 있다면 크레딧을 업데이트
            await conn.execute("UPDATE user SET credit = credit + ? WHERE id = ?", (amount, user_id))
        
        await conn.commit()

async def use_user_credit(user_id, amount):
    db_path = os.path.join('system_database', 'membership.db')
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute("UPDATE user SET credit = credit - ? WHERE id = ?", (amount, user_id))
        await conn.commit()

def send(username, content, avatar_url, url):
    webhook = DiscordWebhook(url=f'{sec.webhook}', content=f'{content}', username=f'{username}', avatar_url=f'{avatar_url}')
    webhook.execute()

async def fetch_user_data(user_id: int):
    db_path = os.path.join('system_database', 'economy.db')
    async with aiosqlite.connect(db_path) as conn:
        async with conn.execute('SELECT * FROM user WHERE id=?', (user_id,)) as cursor:
            return await cursor.fetchone()

async def fetch_tos_status(user_id: int):
    db_path = os.path.join('system_database', 'economy.db')
    async with aiosqlite.connect(db_path) as conn:
        async with conn.execute('SELECT tos FROM user WHERE id=?', (user_id,)) as cursor:
            return await cursor.fetchone()

async def fetch_money_ranking(excluded_ids: list, limit: int):
    db_path = os.path.join('system_database', 'economy.db')
    async with aiosqlite.connect(db_path) as conn:
        if excluded_ids:
            placeholders = ','.join('?' for _ in excluded_ids)
            query = f"SELECT id, money FROM user WHERE id NOT IN ({placeholders}) ORDER BY money DESC LIMIT ?"
            params = excluded_ids + [limit]
        else:
            query = "SELECT id, money FROM user ORDER BY money DESC LIMIT ?"
            params = [limit]
        
        async with conn.execute(query, params) as cursor:
            return await cursor.fetchall()

async def set_monster_type(server_id, channel_id, monster_type):
    db_path = os.path.join('system_database', 'economy.db')
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "INSERT OR REPLACE INTO set_monster_type (server_id, channel_id, monster_type) VALUES (?, ?, ?)",
            (server_id, channel_id, monster_type)
        )
        await db.commit()

async def get_monster_type(server_id, channel_id):
    db_path = os.path.join('system_database', 'economy.db')
    async with aiosqlite.connect(db_path) as db:
        async with db.cursor() as cursor:
            await cursor.execute(
                "SELECT monster_type FROM set_monster_type WHERE server_id = ? AND channel_id = ?",
                (server_id, channel_id)
            )
            result = await cursor.fetchone()
            return result[0] if result else None  # None 반환

async def get_item_damage(item_name):
    db_path = os.path.join('system_database', 'economy.db')
    async with aiosqlite.connect(db_path) as economy_aiodb:
        async with economy_aiodb.cursor() as aiocursor:
            await aiocursor.execute("SELECT damage FROM item WHERE name = ?", (item_name,))
            item_info = await aiocursor.fetchone()
            return item_info[0] if item_info else 0  # 기본 데미지 0 반환

async def get_item_class(user_id, item_name):
    db_path = os.path.join('system_database', 'economy.db')
    async with aiosqlite.connect(db_path) as economy_aiodb:
        async with economy_aiodb.cursor() as aiocursor:
            await aiocursor.execute("SELECT class FROM inventory WHERE id = ? AND name = ?", (user_id, item_name))
            item_info = await aiocursor.fetchone()
            return item_info[0] if item_info else 1  # 기본 class 1 반환

async def add_cash_item_count(user_id, count):
    db_path = os.path.join('system_database', 'economy.db')
    async with aiosqlite.connect(db_path) as economy_aiodb:
        async with economy_aiodb.cursor() as aiocursor:
            # 캐시 아이템의 현재 수량을 조회합니다.
            await aiocursor.execute("SELECT count FROM inventory WHERE id = ? AND name = ?", (user_id, "캐시"))
            existing_item = await aiocursor.fetchone()

            if existing_item:
                # 캐시 아이템이 존재하면 수량을 업데이트
                new_quantity = existing_item[0] + count
                await aiocursor.execute("UPDATE inventory SET count = ? WHERE id = ? AND name = ?", (new_quantity, user_id, "캐시"))
            else:
                # 캐시 아이템이 존재하지 않으면 새로 추가
                await aiocursor.execute("INSERT INTO inventory (id, name, count, class) VALUES (?, ?, ?, ?)", (user_id, "캐시", count, 0))

            await economy_aiodb.commit()

async def remove_cash_item_count(user_id, count):
    db_path = os.path.join('system_database', 'economy.db')
    async with aiosqlite.connect(db_path) as economy_aiodb:
        async with economy_aiodb.cursor() as aiocursor:
            # 캐시 아이템의 현재 수량을 조회합니다.
            await aiocursor.execute("SELECT count FROM inventory WHERE id = ? AND name = ?", (user_id, "캐시"))
            existing_item = await aiocursor.fetchone()

            if existing_item:
                current_quantity = existing_item[0]
                if current_quantity < count:
                    raise ValueError("캐시 인벤토리의 수량이 부족합니다.")  # 부족할 경우 예외 발생

                new_quantity = current_quantity - count
                await aiocursor.execute("UPDATE inventory SET count = ? WHERE id = ? AND name = ?", (new_quantity, user_id, "캐시"))
            else:
                raise ValueError("캐시 아이템이 인벤토리에 없습니다.")  # 캐시 아이템이 없으면 예외 발생

            await economy_aiodb.commit()

async def get_cash_item_count(user_id):
    db_path = os.path.join('system_database', 'economy.db')
    async with aiosqlite.connect(db_path) as economy_aiodb:
        async with economy_aiodb.cursor() as aiocursor:
            # 캐시 아이템의 현재 수량을 조회합니다.
            await aiocursor.execute("SELECT count FROM inventory WHERE id = ? AND name = ?", (user_id, "캐시"))
            existing_item = await aiocursor.fetchone()

            if existing_item:
                return existing_item[0]  # 수량 반환
            else:
                raise ValueError("캐시 아이템이 인벤토리에 없습니다.")  # 캐시 아이템이 없으면 예외 발생

async def get_items():
    # 데이터베이스에서 아이템 정보를 가져오는 비동기 함수
    db_path = os.path.join('system_database', 'economy.db')
    async with aiosqlite.connect(db_path) as db:
        async with db.execute("SELECT name, price, damage, add_exp FROM item") as cursor:
            items = await cursor.fetchall()
    return items

async def get_user_item(user_id, item_name):
    db_path = os.path.join('system_database', 'economy.db')
    async with aiosqlite.connect(db_path) as economy_aiodb:
        async with economy_aiodb.cursor() as aiocursor:
            await aiocursor.execute("SELECT name, count FROM inventory WHERE id = ? AND name = ?", (user_id, item_name))
            return await aiocursor.fetchone()
        
async def get_user_item_class(user_id, item_name):
    db_path = os.path.join('system_database', 'economy.db')
    async with aiosqlite.connect(db_path) as economy_aiodb:
        async with economy_aiodb.cursor() as aiocursor:
            await aiocursor.execute("SELECT name, class FROM inventory WHERE id = ? AND name = ?", (user_id, item_name))
            return await aiocursor.fetchone()

async def update_item_class(user_id, item_name, new_class):
    db_path = os.path.join('system_database', 'economy.db')
    async with aiosqlite.connect(db_path) as economy_aiodb:
        async with economy_aiodb.cursor() as aiocursor:
            await aiocursor.execute("UPDATE inventory SET class = ? WHERE id = ? AND name = ?", (new_class, user_id, item_name))
            await economy_aiodb.commit()

async def add_item(item_name, item_price, item_damage, item_exp):
    db_path = os.path.join('system_database', 'economy.db')
    async with aiosqlite.connect(db_path) as economy_aiodb:
        async with economy_aiodb.cursor() as aiocursor:
            # 아이템이 이미 존재하는지 확인
            await aiocursor.execute("SELECT price FROM item WHERE name = ?", (item_name,))
            existing_item = await aiocursor.fetchone()

            if existing_item:
                # 아이템이 존재하면 가격, 데미지, 경험치 업데이트
                await aiocursor.execute(
                    "UPDATE item SET price = ?, add_exp = ?, damage = ? WHERE name = ?", 
                    (item_price, item_exp, item_damage, item_name)
                )
            else:
                # 아이템이 존재하지 않으면 새로운 아이템 추가
                await aiocursor.execute(
                    "INSERT INTO item (name, price, add_exp, damage) VALUES (?, ?, ?, ?)", 
                    (item_name, item_price, item_exp, item_damage)
                )

            await economy_aiodb.commit()

async def get_user_inventory(user_id):
    db_path = os.path.join('system_database', 'economy.db')
    async with aiosqlite.connect(db_path) as db:
        async with db.execute("SELECT name, count, class FROM inventory WHERE id = ?", (user_id,)) as cursor:
            return await cursor.fetchall()

async def remove_item(item_name):
    db_path = os.path.join('system_database', 'economy.db')
    async with aiosqlite.connect(db_path) as economy_aiodb:
        async with economy_aiodb.cursor() as aiocursor:
            await aiocursor.execute("DELETE FROM item WHERE name = ?", (item_name,))
            await economy_aiodb.commit()

async def get_items():
    db_path = os.path.join('system_database', 'economy.db')
    async with aiosqlite.connect(db_path) as economy_aiodb:
        async with economy_aiodb.cursor() as aiocursor:
            await aiocursor.execute("SELECT name, price, add_exp, damage FROM item")
            data = await aiocursor.fetchall()
            return data

async def get_item_info(item_name):
    db_path = os.path.join('system_database', 'economy.db')
    async with aiosqlite.connect(db_path) as db:
        async with db.execute("SELECT price FROM item WHERE name = ?", (item_name,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {'price': row[0]}
            return None

async def get_user_item_count(user_id, item_name):
    db_path = os.path.join('system_database', 'economy.db')
    async with aiosqlite.connect(db_path) as db:
        async with db.execute("SELECT count FROM inventory WHERE id = ? AND name = ?", (user_id, item_name)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def add_item_to_user_inventory(user_id, item_name, quantity):
    # 아이템이 존재하는지 확인합니다.
    item_info = await get_item_info(item_name)  # 아이템 정보를 가져오는 함수
    if item_info is None:
        raise ValueError(f"{item_name} 아이템은 존재하지 않습니다.")  # 아이템이 없으면 예외 발생
    db_path = os.path.join('system_database', 'economy.db')
    async with aiosqlite.connect(db_path) as economy_aiodb:
        async with economy_aiodb.cursor() as aiocursor:
            # 사용자가 보유한 동일한 아이템이 있는지 확인
            await aiocursor.execute("SELECT count, class FROM inventory WHERE id = ? AND name = ?", (user_id, item_name))
            existing_item = await aiocursor.fetchone()

            if existing_item:
                # 아이템이 존재하면 개수를 업데이트
                new_quantity = existing_item[0] + quantity
                await aiocursor.execute("UPDATE inventory SET count = ? WHERE id = ? AND name = ?", (new_quantity, user_id, item_name))
            else:
                # 아이템이 존재하지 않으면 새로운 아이템 추가
                await aiocursor.execute("INSERT INTO inventory (id, name, count, class) VALUES (?, ?, ?, ?)", (user_id, item_name, quantity, 1))  # class는 기본값 1으로 설정

            await economy_aiodb.commit()

async def remove_item_from_user_inventory(user_id, item_name, quantity):
    db_path = os.path.join('system_database', 'economy.db')
    async with aiosqlite.connect(db_path) as db:
        # 수량 감소
        await db.execute("UPDATE inventory SET count = count - ? WHERE id = ? AND name = ?", 
                         (quantity, user_id, item_name))
        await db.commit()

        # 수량이 0 이하인 경우 아이템 삭제
        await db.execute("DELETE FROM inventory WHERE id = ? AND name = ? AND count <= 0", 
                         (user_id, item_name))
        await db.commit()

async def addcoin(_name, _price):
    db_path = os.path.join('system_database', 'economy.db')
    async with aiosqlite.connect(db_path) as economy_aiodb:
        async with economy_aiodb.cursor() as aiocursor:
            # 가상화폐가 이미 존재하는지 확인
            await aiocursor.execute("SELECT price FROM coin WHERE coin_name = ?", (_name,))
            existing_coin = await aiocursor.fetchone()

            if existing_coin:
                # 가상화폐가 존재하면 가격을 업데이트
                await aiocursor.execute("UPDATE coin SET price = ? WHERE coin_name = ?", (_price, _name))
            else:
                # 가상화폐가 존재하지 않으면 새로운 주식 추가
                await aiocursor.execute("INSERT INTO coin (coin_name, price) VALUES (?, ?)", (_name, _price))

            await economy_aiodb.commit()

async def getcoin():
    db_path = os.path.join('system_database', 'economy.db')
    economy_aiodb = await aiosqlite.connect(db_path)
    aiocursor = await economy_aiodb.cursor()
    await aiocursor.execute("SELECT coin_name, price FROM coin")
    data = await aiocursor.fetchall()
    await aiocursor.close()
    return data

async def removecoin(_name):
    db_path = os.path.join('system_database', 'economy.db')
    economy_aiodb = await aiosqlite.connect(db_path)
    aiocursor = await economy_aiodb.cursor()
    await aiocursor.execute("DELETE FROM coin WHERE coin_name=?", (_name, ))
    await economy_aiodb.commit()
    await aiocursor.close()

async def adduser_coin(user_id, _name, _count):
    # 가상화폐가 존재하는지 확인합니다.
    coins = await getcoin()
    coin_info = next(((name, price) for name, price in coins if name == _name), None)
    
    if coin_info is None:
        raise ValueError(f"{_name} 가상화폐는 존재하지 않습니다.")  # 가상화폐가 없으면 예외 발생

    _, coin_price = coin_info

    # 사용자가 충분한 돈을 가지고 있는지 확인합니다.
    user_money = await getmoney(user_id)
    total_price = coin_price * _count
    total_price_with_fee = total_price * 1.0005  # 수수료 0.05% 부과
    if user_money < total_price_with_fee:
        raise ValueError(f"돈이 부족합니다. 필요한 금액: {total_price_with_fee}, 현재 잔액: {user_money}")

    # 돈을 차감합니다.
    await removemoney(user_id, total_price_with_fee)

    db_path = os.path.join('system_database', 'economy.db')
    async with aiosqlite.connect(db_path) as economy_aiodb:
        async with economy_aiodb.cursor() as aiocursor:
            # 사용자가 보유한 동일한 가상화폐가 있는지 확인
            await aiocursor.execute("SELECT count FROM user_coin WHERE id = ? AND coin_name = ?", (user_id, _name))
            existing_coin = await aiocursor.fetchone()

            if existing_coin:
                # 가상화폐가 존재하면 개수를 업데이트
                new_count = existing_coin[0] + _count
                await aiocursor.execute("UPDATE user_coin SET count = ? WHERE id = ? AND coin_name = ?", (new_count, user_id, _name))
            else:
                # 가상화폐가 존재하지 않으면 새로운 주식 추가
                await aiocursor.execute("INSERT INTO user_coin (id, coin_name, count) VALUES (?, ?, ?)", (user_id, _name, _count))

            await economy_aiodb.commit()

async def getuser_coin(user_id):
    db_path = os.path.join('system_database', 'economy.db')
    economy_aiodb = await aiosqlite.connect(db_path)
    aiocursor = await economy_aiodb.cursor()
    await aiocursor.execute("SELECT coin_name, count FROM user_coin WHERE id=?", (user_id,))
    data = await aiocursor.fetchall()
    await aiocursor.close()
    return data

async def removeuser_coin(user_id, _name, _count):
    # 주식이 존재하는지 확인합니다.
    coins = await getcoin()
    coin_info = next((price for name, price in coins if name == _name), None)

    if coin_info is None:
        raise ValueError(f"{_name} 주식은 존재하지 않습니다.")
    else:
        coin_price = coin_info

    # 사용자가 보유한 가상화폐의 개수를 확인합니다.
    db_path = os.path.join('system_database', 'economy.db')
    async with aiosqlite.connect(db_path) as economy_aiodb:
        async with economy_aiodb.cursor() as aiocursor:
            await aiocursor.execute("SELECT count FROM user_coin WHERE id = ? AND coin_name = ?", (user_id, _name))
            user_coin = await aiocursor.fetchone()

            # 사용자가 보유 중인 가상화폐가 없거나 판매하려는 개수가 보유 개수를 초과하면 예외 발생
            if user_coin is None or user_coin[0] < _count:
                raise ValueError(f"{_name} 가상화폐를 충분히 보유하고 있지 않습니다. 현재 보유 개수: {user_coin[0] if user_coin else 0}")

            # 가상화폐를 판매하고 돈을 지급합니다.
            await aiocursor.execute("UPDATE user_coin SET count = count - ? WHERE id = ? AND coin_name = ?", (_count, user_id, _name))
            new_count = user_coin[0] - _count

            # 가상화폐의 개수가 0이면 레코드를 삭제합니다.
            if new_count == 0:
                await aiocursor.execute("DELETE FROM user_coin WHERE id = ? AND coin_name = ?", (user_id, _name))

            await economy_aiodb.commit()
    
    sell_price = coin_price * _count
    net_sell_price = sell_price * (1 - 0.0005)  # 수수료 0.05%
    await addmoney(user_id, round(net_sell_price))

async def addstock(_name, _price):
    db_path = os.path.join('system_database', 'economy.db')
    async with aiosqlite.connect(db_path) as economy_aiodb:
        async with economy_aiodb.cursor() as aiocursor:
            # 주식이 이미 존재하는지 확인
            await aiocursor.execute("SELECT price FROM stock WHERE stock_name = ?", (_name,))
            existing_stock = await aiocursor.fetchone()

            if existing_stock:
                # 주식이 존재하면 가격을 업데이트
                await aiocursor.execute("UPDATE stock SET price = ? WHERE stock_name = ?", (_price, _name))
            else:
                # 주식이 존재하지 않으면 새로운 주식 추가
                await aiocursor.execute("INSERT INTO stock (stock_name, price) VALUES (?, ?)", (_name, _price))

            await economy_aiodb.commit()

async def getstock():
    db_path = os.path.join('system_database', 'economy.db')
    economy_aiodb = await aiosqlite.connect(db_path)
    aiocursor = await economy_aiodb.cursor()
    await aiocursor.execute("SELECT stock_name, price FROM stock")
    data = await aiocursor.fetchall()
    await aiocursor.close()
    return data

async def removestock(_name):
    db_path = os.path.join('system_database', 'economy.db')
    economy_aiodb = await aiosqlite.connect(db_path)
    aiocursor = await economy_aiodb.cursor()
    await aiocursor.execute("DELETE FROM stock WHERE stock_name=?", (_name, ))
    await economy_aiodb.commit()
    await aiocursor.close()

async def adduser_stock(user_id, _name, _count):
    # 주식이 존재하는지 확인합니다.
    stocks = await getstock()
    stock_info = next(((name, price) for name, price in stocks if name == _name), None)
    
    if stock_info is None:
        raise ValueError(f"{_name} 주식은 존재하지 않습니다.")  # 주식이 없으면 예외 발생

    _, stock_price = stock_info

    # 사용자가 충분한 돈을 가지고 있는지 확인합니다.
    user_money = await getmoney(user_id)
    total_price = stock_price * _count
    if user_money < total_price:
        raise ValueError(f"돈이 부족합니다. 필요한 금액: {total_price}, 현재 잔액: {user_money}")

    # 돈을 차감합니다.
    await removemoney(user_id, total_price)

    db_path = os.path.join('system_database', 'economy.db')
    async with aiosqlite.connect(db_path) as economy_aiodb:
        async with economy_aiodb.cursor() as aiocursor:
            # 사용자가 보유한 동일한 주식이 있는지 확인
            await aiocursor.execute("SELECT count FROM user_stock WHERE id = ? AND stock_name = ?", (user_id, _name))
            existing_stock = await aiocursor.fetchone()

            if existing_stock:
                # 주식이 존재하면 개수를 업데이트
                new_count = existing_stock[0] + _count
                await aiocursor.execute("UPDATE user_stock SET count = ? WHERE id = ? AND stock_name = ?", (new_count, user_id, _name))
            else:
                # 주식이 존재하지 않으면 새로운 주식 추가
                await aiocursor.execute("INSERT INTO user_stock (id, stock_name, count) VALUES (?, ?, ?)", (user_id, _name, _count))

            await economy_aiodb.commit()

async def getuser_stock(user_id):
    db_path = os.path.join('system_database', 'economy.db')
    economy_aiodb = await aiosqlite.connect(db_path)
    aiocursor = await economy_aiodb.cursor()
    await aiocursor.execute("SELECT stock_name, count FROM user_stock WHERE id=?", (user_id,))
    data = await aiocursor.fetchall()
    await aiocursor.close()
    return data

async def removeuser_stock(user_id, _name, _count):
    # 주식이 존재하는지 확인합니다.
    stocks = await getstock()
    stock_info = next((price for name, price in stocks if name == _name), None)

    if stock_info is None:
        raise ValueError(f"{_name} 주식은 존재하지 않습니다.")
    else:
        stock_price = stock_info

    # 사용자가 보유한 주식의 개수를 확인합니다.
    db_path = os.path.join('system_database', 'economy.db')
    async with aiosqlite.connect(db_path) as economy_aiodb:
        async with economy_aiodb.cursor() as aiocursor:
            await aiocursor.execute("SELECT count FROM user_stock WHERE id = ? AND stock_name = ?", (user_id, _name))
            user_stock = await aiocursor.fetchone()

            # 사용자가 보유 중인 주식이 없거나 판매하려는 개수가 보유 개수를 초과하면 예외 발생
            if user_stock is None or user_stock[0] < _count:
                raise ValueError(f"{_name} 주식을 충분히 보유하고 있지 않습니다. 현재 보유 개수: {user_stock[0] if user_stock else 0}")

            # 주식을 판매하고 돈을 지급합니다.
            await aiocursor.execute("UPDATE user_stock SET count = count - ? WHERE id = ? AND stock_name = ?", (_count, user_id, _name))
            new_count = user_stock[0] - _count

            # 주식의 개수가 0이면 레코드를 삭제합니다.
            if new_count == 0:
                await aiocursor.execute("DELETE FROM user_stock WHERE id = ? AND stock_name = ?", (user_id, _name))

            await economy_aiodb.commit()

    sell_price = stock_price * _count
    net_sell_price = sell_price * (1 - 0.00015)  # 수수료 0.015%
    await addmoney(user_id, round(net_sell_price))

async def handle_bet(ctx, user, money, success_rate, win_multiplier, lose_multiplier, lose_exp_divisor):
    random_number = random.randrange(1, 101)
    if random_number <= success_rate:  # 성공
        earnings = round(money * win_multiplier)
        await addmoney(user.id, earnings)
        await add_exp(user.id, round(earnings / 600))
        embed = disnake.Embed(color=embedsuccess)
        embed.add_field(name="성공", value=f"{earnings:,}원을 얻었습니다.")
        await economy_log(ctx, "도박", "+", earnings)
    else:  # 실패
        loss = round(money * lose_multiplier)
        await removemoney(user.id, loss)
        await add_lose_money(user.id, loss)
        await add_exp(user.id, round(loss / lose_exp_divisor))
        embed = disnake.Embed(color=embederrorcolor)
        embed.add_field(name="실패", value=f"{loss:,}원을 잃었습니다.")
        await economy_log(ctx, "도박", "-", loss)
    
    await ctx.send(embed=embed)

async def addmoney(_id, _amount):
    db_path = os.path.join('system_database', 'economy.db')
    economy_aiodb = await aiosqlite.connect(db_path)

    try:
        aiocursor = await economy_aiodb.execute("SELECT * FROM user WHERE id=?", (_id,))
        dat = await aiocursor.fetchone()  # fetchone() 사용

        if dat is None:
            # 데이터가 없을 경우 새 사용자 추가
            await aiocursor.execute(
                "INSERT INTO user (id, money, tos, level, exp, lose_money, dm_on_off, checkin) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (_id, _amount, 0, 0, 0, 0, 0, 0)
            )
        else:
            # 데이터가 있을 경우 금액 업데이트
            new_balance = dat[1] + _amount
            await aiocursor.execute("UPDATE user SET money = ? WHERE id = ?", (new_balance, _id))

        await economy_aiodb.commit()  # 변경 사항 커밋

    finally:
        await aiocursor.close()
        await economy_aiodb.close()

async def getmoney(user_id):
    db_path = os.path.join('system_database', 'economy.db')
    async with aiosqlite.connect(db_path) as economy_aiodb:
        async with economy_aiodb.execute("SELECT * FROM user WHERE id=?", (user_id,)) as aiocursor:
            dat = await aiocursor.fetchall()  # 모든 데이터 가져오기
    await economy_aiodb.close()

    if not dat or len(dat) < 1 or len(dat[0]) < 2:
        print(f"사용자 {user_id}의 데이터가 없습니다.")
        return 0  # 기본값으로 0 반환

    return dat[0][1]  # 현재 보유 금액 반환

async def removemoney(_id, _amount):
    db_path = os.path.join('system_database', 'economy.db')
    economy_aiodb = await aiosqlite.connect(db_path)
    
    try:
        aiocursor = await economy_aiodb.execute("SELECT * FROM user WHERE id=?", (_id,))
        dat = await aiocursor.fetchone()  # fetchall() 대신 fetchone() 사용

        if dat is None:  # 데이터가 없을 경우
            return False
        if dat[1] < _amount:  # 현재 금액이 요청 금액보다 적을 경우
            return False
        
        # 금액 업데이트
        new_balance = dat[1] - _amount
        await aiocursor.execute("UPDATE user SET money = ? WHERE id = ?", (new_balance, _id))
        await economy_aiodb.commit()  # 변경 사항 커밋

    finally:
        await aiocursor.close()
        await economy_aiodb.close()
        
    return True

async def add_lose_money(_id, _amount):
    db_path = os.path.join('system_database', 'economy.db')
    economy_aiodb = await aiosqlite.connect(db_path)
    aiocursor = await economy_aiodb.execute("select * from user where id=?", (_id,))
    dat = await aiocursor.fetchall()
    if not dat:
        await aiocursor.execute("insert into user (id, money, tos, level, exp, lose_money, dm_on_off, checkin) values (?, ?, ?, ?, ?, ?, ?, ?)", (_id, 0, 0, 0, 0, _amount, 0, 0))
    else:
        await aiocursor.execute("update user set lose_money = ? where id = ?", (dat[0][5] + _amount, _id))
    await economy_aiodb.commit()
    await aiocursor.close()

async def get_lose_money(_id):
    db_path = os.path.join('system_database', 'economy.db')
    economy_aiodb = await aiosqlite.connect(db_path)
    aiocursor = await economy_aiodb.execute("select * from user where id=?", (_id, ))
    dat = await aiocursor.fetchall()
    await aiocursor.close()
    if dat == False: return 0
    return dat[0][5]

async def add_exp(user_id, amount):
    db_path = os.path.join('system_database', 'economy.db')
    
    try:
        economy_aiodb = await aiosqlite.connect(db_path)
        aiocursor = await economy_aiodb.execute("SELECT * FROM user WHERE id=?", (user_id,))
        dat = await aiocursor.fetchall()
        
        if not dat:
            return
        
        new_exp = dat[0][4] + amount
        await aiocursor.execute("UPDATE user SET exp = ? WHERE id = ?", (new_exp, user_id))
        await economy_aiodb.commit()  # 커밋은 업데이트 후에
    except Exception as e:
        print(f"오류 발생: {e}")  # 오류 로그 출력
    finally:
        await aiocursor.close()
        await economy_aiodb.close()

async def get_exp(_id):
    db_path = os.path.join('system_database', 'economy.db')
    economy_aiodb = await aiosqlite.connect(db_path)
    async with economy_aiodb:
        async with economy_aiodb.execute("SELECT exp FROM user WHERE id=?", (_id,)) as cursor:
            dat = await cursor.fetchone()

    return dat[0] if dat else 0  # 사용자가 존재하지 않는 경우 0 반환

async def dev_deactivate(ctx):
    embed = disnake.Embed(color=embederrorcolor)
    embed.add_field(name="❌ 오류", value=f"개발자에 의해 비활성화된 명령어입니다.\n개발자에게 문의하세요.")
    await ctx.send(embed=embed, ephemeral=True)
    return

async def dm_on_off(user):
    user_id = user.id  # User 객체에서 ID를 추출
    db_path = os.path.join('system_database', 'economy.db')
    async with aiosqlite.connect(db_path) as economy_aiodb:
        async with economy_aiodb.cursor() as aiocursor:
            await aiocursor.execute("SELECT dm_on_off FROM user WHERE id=?", (user_id,))
            dbdata = await aiocursor.fetchone()

            if dbdata is None or len(dbdata) < 1 or dbdata[0] is None:
                print(f"사용자 {user_id}의 DM 설정을 찾을 수 없습니다.")
                return 0  # 기본값으로 0을 반환

            # dbdata[0]이 None이 아닐 때만 int로 변환
            try:
                dm_on_off = int(dbdata[0])  # 0번 인덱스에서 DM 설정 가져오기
            except ValueError:
                print(f"사용자 {user_id}의 DM 설정이 정수로 변환할 수 없습니다.")
                return 0  # 변환 실패 시 기본값으로 0을 반환

            return dm_on_off  # DM 설정 값을 반환
    await economy_aiodb.commit()
    await economy_aiodb.close()

# 상수 정의
DB_PATH = os.path.join('system_database', 'economy.db')
ERROR_COLOR = 0xff0000  # 오류 색상 예시

async def member_status(ctx):
    if not ctx.response.is_done():
        await ctx.response.defer()
    db_path = os.path.join('system_database', 'economy.db')
    async with aiosqlite.connect(db_path) as economy_aiodb:
        async with economy_aiodb.execute("SELECT tos FROM user WHERE id=?", (ctx.author.id,)) as aiocursor:
            dbdata = await aiocursor.fetchone()
        await economy_aiodb.commit()
        await economy_aiodb.close()

    # dbdata가 None일 경우
        if dbdata is None:
            embed = disnake.Embed(color=ERROR_COLOR)
            embed.add_field(name="❌ 오류", value=f"{ctx.author.mention}\n가입되지 않은 유저입니다.")
            await ctx.followup.send(embed=embed, ephemeral=True)
            return False  # 상태를 반환하여 호출한 곳에서 처리 가능

        # tos 값이 1일 경우
        tos = int(dbdata[0])
        if tos == 1:
            embed = disnake.Embed(color=ERROR_COLOR)
            embed.add_field(name="❌ 오류", value="이용제한된 유저입니다.")
            await ctx.followup.send(embed=embed, ephemeral=True)
            return False  # 상태를 반환하여 호출한 곳에서 처리 가능

    return True  # 상태 확인 성공 시 True 반환
        
async def membership(ctx):
    db_path = os.path.join('system_database', 'membership.db')
    economy_aiodb = await aiosqlite.connect(db_path)
    aiocursor = await economy_aiodb.execute("SELECT class FROM user WHERE id=?", (ctx.author.id,))
    dbdata = await aiocursor.fetchone()
    
    if dbdata is None:
        # 데이터가 없을 경우 비회원으로 등록
        await economy_aiodb.execute("INSERT INTO user (id, class, expiration_date, credit) VALUES (?, ?, ?, ?)", (ctx.author.id, 0, None, 30))  # 0: 비회원
        dbdata = await aiocursor.fetchone()
    await economy_aiodb.commit()
    await economy_aiodb.close()

async def database_create(ctx):
    # 서버 아이디 및 서버 이름 가져오기
    server_id = str(ctx.guild.id)
    # 데이터베이스 생성
    conn = await aiosqlite.connect(f'database\\{server_id}.db')
    # 비동기로 커서를 가져옵니다.
    cursor = await conn.cursor()
    
    # 경고 테이블 생성
    await cursor.execute('''
        CREATE TABLE IF NOT EXISTS 경고 (
            아이디 INTEGER,
            관리자 INTEGER,
            맴버 INTEGER,
            경고 INTEGER,
            사유 INTEGER
        )
    ''')
    
    # 설정 테이블 생성, 각 기능의 기본값을 1로 설정
    await cursor.execute('''
        CREATE TABLE IF NOT EXISTS 설정 (
            공지채널 INTEGER,
            처벌로그 INTEGER,
            입장로그 INTEGER,
            퇴장로그 INTEGER,
            인증역할 INTEGER,
            인증채널 INTEGER,
            음악기능 INTEGER DEFAULT 1,
            경제기능 INTEGER DEFAULT 1,
            관리기능 INTEGER DEFAULT 1,
            유틸리티기능 INTEGER DEFAULT 1,
            주식명령어 INTEGER DEFAULT 1,
            코인명령어 INTEGER DEFAULT 1,
            게임명령어 INTEGER DEFAULT 1,
            인증 INTEGER DEFAULT 1,
            인증_문자 INTEGER DEFAULT 1,
            인증_이메일 INTEGER DEFAULT 1,
            채팅관리명령어 INTEGER DEFAULT 1,
            유저관리명령어 INTEGER DEFAULT 1
        )
    ''')

    await conn.commit()
    await conn.close()

async def database_create_server_join(guild):
    # 서버 아이디 및 서버 이름 가져오기
    server_id = str(guild)
    # 데이터베이스 생성
    conn = await aiosqlite.connect(f'database\\{server_id}.db')
    # 비동기로 커서를 가져옵니다.
    cursor = await conn.cursor()
    
    # 경고 테이블 생성
    await cursor.execute('''
        CREATE TABLE IF NOT EXISTS 경고 (
            아이디 INTEGER,
            관리자 INTEGER,
            맴버 INTEGER,
            경고 INTEGER,
            사유 INTEGER
        )
    ''')
    
    # 설정 테이블 생성
    await cursor.execute('''
        CREATE TABLE IF NOT EXISTS 설정 (
            공지채널 INTEGER,
            처벌로그 INTEGER,
            입장로그 INTEGER,
            퇴장로그 INTEGER,
            인증역할 INTEGER,
            인증채널 INTEGER,
            음악기능 INTEGER DEFAULT 1,
            경제기능 INTEGER DEFAULT 1,
            관리기능 INTEGER DEFAULT 1,
            유틸리티기능 INTEGER DEFAULT 1,
            주식명령어 INTEGER DEFAULT 1,
            코인명령어 INTEGER DEFAULT 1,
            게임명령어 INTEGER DEFAULT 1,
            인증 INTEGER DEFAULT 1,
            인증_문자 INTEGER DEFAULT 1,
            인증_이메일 INTEGER DEFAULT 1,
            채팅관리명령어 INTEGER DEFAULT 1,
            유저관리명령어 INTEGER DEFAULT 1
        )
    ''')

    # 기본 데이터 추가 (0으로 설정)
    await cursor.execute('''
        INSERT INTO 설정 (
            공지채널, 처벌로그, 입장로그, 퇴장로그, 인증역할, 인증채널
        ) VALUES (?, ?, ?, ?, ?, ?)
    ''', (0, 0, 0, 0, 0, 0))  # 모든 필드를 0으로 설정

    await conn.commit()
    await conn.close()

async def delete_server_database(guild_id):
    # 서버 ID에 해당하는 데이터베이스 파일 이름 생성
    db_filename = f"{guild_id}.db"
    
    # 파일이 존재하는지 확인하고 삭제
    if os.path.exists(db_filename):
        os.remove(db_filename)

def send_email(recipient, verifycode):
    msg = MIMEMultipart()
    msg['From'] = str(Address("NET CLOUD", addr_spec=sec.smtp_user))  
    msg['To'] = recipient
    msg['Subject'] = 'NET CLOUD 이메일 인증'
    msg['Date'] = formatdate(localtime=True)

    body = f"""
    <!DOCTYPE html>
    <html lang="ko">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>메일 인증</title>
            <script src="https://cdn.tailwindcss.com"></script>
            <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap" rel="stylesheet">
            <style>
                body {{font-family: 'Noto Sans KR', sans-serif; background-color: #1a202c; display: flex; align-items: center; justify-content: center; min-height: 100vh;}}
                .container {{background-color: #2d3748; padding: 1rem; border-radius: 1.5rem; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3); margin-left: 35%; margin-right: 35%; height: auto; text-align: center;}}
                .subtitle {{color: #81e6d9; font-size: 1.5rem; font-weight: bold; margin-bottom: 1.5rem;}}
                .text {{color: #fff; margin-bottom: 1rem;}}
                .button {{background-color: #38a169; color: white; padding: 0.5rem 1rem; border-radius: 0.25rem; margin-bottom: 1.5rem;}}
                .footer {{color: rgb(150, 150, 150);}}
            </style>
        </head>
        <body>
            <div class="container">
                <center><img src="https://i.ibb.co/J5dD23R/CLOUD1-nobg.png" alt="CLOUD1-nobg" width="230px" height="100px"></center>
                <h2 class="subtitle">메일인증 안내</h2>
                <p class="text">안녕하세요, 넷클라우드입니다.<br>넷클라우드를 이용해 주셔서 감사합니다.<br></p>
                <button class="button">{verifycode}</button>
                <p class="footer">요청하지 않으셨다면 무시해주세요.</p>
                <p class="footer">고객지원 0507-1374-6680</p>
            </div>
        </body>
    </html>
    """
    
    msg.attach(MIMEText(body, 'html'))
    
    with smtplib.SMTP(sec.smtp_server, 587) as server:
        server.starttls()
        server.login(sec.smtp_user, sec.smtp_password)
        server.send_message(msg)

# 쿨다운 정보를 로드하는 함수
def load_cooldowns():
    try:
        with open(cooldown_file, "r") as f:
            try:
                cooldowns = json.load(f)
            except json.JSONDecodeError:
                cooldowns = {}
    except FileNotFoundError:
        cooldowns = {}
    return cooldowns

# 쿨다운 정보를 저장하는 함수
def save_cooldowns(cooldowns):
    with open(cooldown_file, "w") as f:
        json.dump(cooldowns, f)

async def addwarn(ctx, _user, _warn, _reason):
    db_path = os.path.join(os.getcwd(), "database", f"{ctx.guild.id}.db")
    if not os.path.exists(db_path):
            await database_create(ctx)
    try:
        aiodb = await aiosqlite.connect(db_path)
        aiocursor = await aiodb.cursor()     # 커서 생성
    except Exception as e:
        print(f"Database connection error: {e}")
        return
    aiocursor = await aiodb.execute("select * from 경고 order by 아이디 desc")
    dat = await aiocursor.fetchone()
    await aiocursor.close()
    if dat is None:
        dat = [0, "asdf"]
    new_id = dat[0] + 1 if dat else 1
    aiocursor = await aiodb.execute("INSERT INTO 경고 (아이디, 관리자, 맴버, 경고, 사유) VALUES (?, ?, ?, ?, ?)", (new_id, ctx.author.id, _user.id, _warn, _reason))
    await aiodb.commit()
    await aiocursor.close()
    aiocursor = await aiodb.execute("SELECT SUM(경고) FROM 경고 WHERE 맴버 = ?", (_user.id,))
    accumulatewarn_result = await aiocursor.fetchone()
    await aiocursor.close()
    accumulatewarn = accumulatewarn_result[0] if accumulatewarn_result and accumulatewarn_result[0] else 0
    embed = disnake.Embed(color=embedsuccess)
    embed.add_field(name="✅경고를 지급했어요", value="", inline=False)
    embed.add_field(name="대상", value=_user.mention)
    max_warning = 10
    embed.add_field(name="누적 경고", value=f"{accumulatewarn} / {max_warning} (+ {_warn})")
    embed.add_field(name="사유", value=_reason, inline=False)
    await ctx.send(embed=embed)
    aiocursor = await aiodb.execute("SELECT 처벌로그 FROM 설정")
    설정_result = await aiocursor.fetchone()
    await aiocursor.close()
    return new_id, accumulatewarn, 설정_result  # 설정_result 추가

async def getwarn(ctx, user):
    db_path = os.path.join(os.getcwd(), "database", f"{ctx.guild.id}.db")
    if not os.path.exists(db_path):
        await database_create(ctx)
    aiodb = await aiosqlite.connect(db_path)
    aiocursor = await aiodb.execute(f"SELECT * FROM 경고 WHERE 맴버 = {user.id}")
    dat = await aiocursor.fetchall()
    await aiocursor.close()
    aiocursor = await aiodb.execute("SELECT SUM(경고) FROM 경고 WHERE 맴버 = ?", (user.id,))
    accumulatewarn_result = await aiocursor.fetchone()
    await aiocursor.close()
    accumulatewarn = accumulatewarn_result[0] if accumulatewarn_result and accumulatewarn_result[0] else 0
    return dat, accumulatewarn

async def removewarn(ctx, warn_id):
    db_path = os.path.join(os.getcwd(), "database", f"{ctx.guild.id}.db")
    if not os.path.exists(db_path):
        await database_create(ctx)
    aiodb = await aiosqlite.connect(db_path)
    aiocursor = await aiodb.execute("SELECT * FROM 경고 WHERE 아이디 = ?", (warn_id,))
    dat = await aiocursor.fetchall()
    if not dat:
        return None
    else:
        await aiocursor.execute("DELETE FROM 경고 WHERE 아이디 = ?", (warn_id,))
        await aiodb.commit()  # 변경 사항을 데이터베이스에 확정합니다.
        return warn_id