import os
import sqlite3

def get_permissions(guild_id: str):
    file_path = f"./database/{guild_id}.db"
    if not os.path.isfile(file_path):
        return [1, 1, 1, 1]

    conn = sqlite3.connect(file_path)
    cursor = conn.cursor()
    cursor.execute("SELECT 음악기능, 경제기능, 관리기능, 유틸리티기능 FROM 설정")
    permissions = cursor.fetchone()
    conn.close()

    # 설정값이 없다면 모두 활성화 (기본값)
    if permissions == None:
        return [1, 1, 1, 1]

    return permissions