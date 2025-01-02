import disnake
import os
import aiosqlite
import security as sec

TOKEN = sec.token
DATABASE_FOLDER = 'database'  # 데이터베이스 파일이 저장된 폴더

bot = disnake.Client()

async def create_database_if_not_exists(guild_id):
    # 서버 아이디를 문자열로 변환
    server_id = str(guild_id)
    # 데이터베이스 파일 경로 설정
    db_path = f'{DATABASE_FOLDER}\\{server_id}.db'
    
    # 데이터베이스 파일이 존재하지 않으면 생성
    if not os.path.exists(db_path):
        conn = await aiosqlite.connect(db_path)
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
        print(f"데이터베이스 파일이 생성되었습니다: {db_path}")
    else:
        print(f"데이터베이스 파일이 이미 존재합니다: {db_path}")

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    await create_databases_for_all_guilds()

async def create_databases_for_all_guilds():
    # 봇이 들어가 있는 서버의 ID를 가져옵니다.
    guild_ids = [guild.id for guild in bot.guilds]

    # 각 서버에 대해 데이터베이스 파일이 없으면 생성
    for guild_id in guild_ids:
        await create_database_if_not_exists(guild_id)

@bot.event
async def on_guild_join(guild):
    await create_database_if_not_exists(guild.id)
    print(f'새로운 서버에 입장했습니다: {guild.name} (ID: {guild.id})')

bot.run(TOKEN)