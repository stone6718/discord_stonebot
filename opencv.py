import sqlite3
import os
import matplotlib.pyplot as plt
from matplotlib import font_manager, rc

# 한글 폰트 설정
font_path = 'NanumGothic.ttf'  # 시스템에 맞는 한글 폰트 경로로 변경
font_manager.fontManager.addfont(font_path)
rc('font', family='NanumGothic')

def baccarat():
    # SQLite 데이터베이스 경로 설정
    db_path = os.path.join('system_database', 'baccarat.db')  # 데이터베이스 파일 경로를 설정합니다.

    # SQLite 데이터베이스 연결
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    query = "SELECT winner, COUNT(*) as count FROM winner GROUP BY winner"
    cursor.execute(query)

    # 결과 가져오기
    results = cursor.fetchall()

    # 데이터 분리
    commands = [row[0] for row in results]
    counts = [row[1] for row in results]

    # 그래프 그리기
    plt.figure(figsize=(12, 6))
    bars = plt.bar(commands, counts, color='skyblue')
    plt.xlabel('결과')
    plt.ylabel('횟수')
    plt.title('분석')
    plt.xticks(rotation=45)
    plt.tight_layout()

    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, yval, int(yval), ha='center', va='bottom')

    plt.show()
    conn.close()