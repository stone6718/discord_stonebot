import disnake
import os
import security as sec

TOKEN = sec.token
DATABASE_FOLDER = 'database'  # 데이터베이스 파일이 저장된 폴더

bot = disnake.Client()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    await delete_unwanted_databases()

async def delete_unwanted_databases():
    # 봇이 들어가 있는 서버의 ID를 가져옵니다.
    guild_ids = [guild.id for guild in bot.guilds]

    # 데이터베이스 폴더의 모든 파일을 확인합니다.
    for filename in os.listdir(DATABASE_FOLDER):
        if filename.endswith('.db'):
            # 파일 이름에서 서버 ID를 추출합니다. (예: '123456789012345678.db')
            file_guild_id = int(filename[:-3])  # '.db'를 제거하고 int로 변환

            # 서버 ID가 봇이 들어가 있는 서버 리스트에 없으면 삭제합니다.
            if file_guild_id not in guild_ids:
                file_path = os.path.join(DATABASE_FOLDER, filename)
                os.remove(file_path)
                print(f'Deleted database file: {filename}')

bot.run(TOKEN)