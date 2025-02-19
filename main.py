import security as sec
import logging

# 로깅 설정
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')
import yt_dlp as youtube_dl
import bs4, re, pytz, math, time, os, coolsms_kakao
import asyncio, disnake, aiosqlite, platform, tempfile, requests
import random, string, datetime, psutil, websocket, aiohttp, cpuinfo
from gtts import gTTS
from def_list import *
import matplotlib.pyplot as plt
from matplotlib import font_manager, rc
from googletrans import Translator
from disnake.ext import commands, tasks
from collections import defaultdict
from importlib.metadata import version
from permissions import get_permissions
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
from disnake.ui import Button, View, Modal, TextInput
from disnake import TextInputStyle, ButtonStyle, FFmpegPCMAudio
from disnake import FFmpegPCMAudio

#intents = disnake.Intents.all()
bot = commands.AutoShardedBot(command_prefix="/") #intents=intents)
shard_count = min(2, max(1, len(bot.guilds) // 1000))
token = sec.token
developer = [int(dev_id) for dev_id in sec.developer_id]

# 시작 시간 기록
start_time = datetime.now()

embedcolor = 0xff00ff
embedwarning = 0xff9900
embedsuccess = 0x00ff00
embederrorcolor = 0xff0000

cpu_info = cpuinfo.get_cpu_info()

# 한글 폰트 설정
font_path = 'NanumGothic.ttf'  # 시스템에 맞는 한글 폰트 경로로 변경
font_manager.fontManager.addfont(font_path)
rc('font', family='NanumGothic')
##################################################################################################
# 데이터베이스에서 권한을 가져오는 함수
async def get_permissions(server_id: int):
    db_path = f"database/{server_id}.db"
    async with aiosqlite.connect(db_path) as db:
        async with db.execute("SELECT 음악기능, 경제기능, 관리기능, 유틸리티기능, 주식명령어, 코인명령어, 게임명령어, 인증, 인증_문자, 인증_이메일, 채팅관리명령어, 유저관리명령어 FROM 설정") as cursor:
            row = await cursor.fetchone()
            return list(row) if row else [1] * 11  # 기본값: 모두 활성화

# 명령어 사용 권한 체크
async def check_permissions(ctx):
    command_permissions = {
        "음악기능": (0, "음악 기능이 비활성화되어 있습니다."),
        "경제기능": (1, "경제 기능이 비활성화되어 있습니다."),
        "관리기능": (2, "관리 기능이 비활성화되어 있습니다."),
        "유틸리티기능": (3, "유틸리티 기능이 비활성화되어 있습니다."),
        "주식명령어": (4, "경제(주식) 명령어가 비활성화되어 있습니다."),
        "코인명령어": (5, "경제(코인) 명령어가 비활성화되어 있습니다."),
        "게임명령어": (6, "경제(게임) 명령어가 비활성화되어 있습니다."),
        "인증": (7, "관리(인증) 명령어가 비활성화되어 있습니다."),
        "인증_문자": (8, "관리(인증_문자) 명령어가 비활성화되어 있습니다."),
        "인증_이메일": (9, "관리(인증_이메일) 명령어가 비활성화되어 있습니다."),
        "채팅관리명령어": (10, "관리(채팅관리) 명령어가 비활성화되어 있습니다."),
        "유저관리명령어": (11, "관리(유저관리) 명령어가 비활성화되어 있습니다."),
    }

    permissions = await get_permissions(ctx.guild.id)

    command_name = ctx.data.name
    if command_name in command_permissions:
        index, error_message = command_permissions[command_name]
        if permissions[index] == 0:  # 0은 비활성화
            embed = disnake.Embed(color=embederrorcolor)
            embed.add_field(name="❌ 오류", value=error_message)
            await ctx.send(embed=embed, ephemeral=True)
            return

    return True  # 모든 권한 체크가 통과되었을 경우
##################################################################################################
# 지역코드
region_codes = {
    "서울특별시": "B10",
    "부산광역시": "C10",
    "대구광역시": "D10",
    "인천광역시": "E10",
    "광주광역시": "F10",
    "대전광역시": "G10",
    "울산광역시": "H10",
    "세종특별자치시": "I10",
    "경기도": "J10",
    "강원특별자치도": "K10",
    "충청북도": "M10",
    "충청남도": "N10",
    "전북특별자치도": "P10",
    "전라남도": "Q10",
    "경상북도": "R10",
    "경상남도": "S10",
    "제주특별자치도": "T10"
}

@bot.slash_command(name='급식', description="급식 메뉴를 알려줍니다.")
async def meal(ctx,
    지역=commands.Param(description="학교가 위치한 지역을 골라주세요.", choices=list(region_codes.keys())),
    학교명: str=commands.Param(description="학교명을 ~~학교 까지 입력해주세요."), 
    날짜:str=commands.Param(description="YYYYMMDD  8자를 입력해주세요.", default=None)):
    if not await tos(ctx):
        return
    try:
        if 학교명.endswith('초') or 학교명.endswith('고'):
            학교명 += '등학교'
        elif 학교명.endswith('중') or 학교명.endswith('대'):
            학교명 += '학교'

        edu_office_code = region_codes[지역]

        if 날짜 is None:
            date = datetime.now().strftime('%Y%m%d')
        else:
            date = 날짜

        # 응답을 지연
        await ctx.response.defer(ephemeral=False)

        meal_info_task = get_meal_info_async(학교명, edu_office_code, date)
        calorie_info_task = get_calorie_info_async(학교명, edu_office_code, date)
        meal_info, meal_date = await meal_info_task
        calorie_info, _ = await calorie_info_task 

        if meal_date is None or not isinstance(meal_date, str):
            raise ValueError("급식 날짜 정보가 유효하지 않습니다.")

        meal_datetime = datetime.strptime(meal_date, '%Y%m%d')
        weekday_kor = ['월', '화', '수', '목', '금', '토', '일']
        weekday_str = weekday_kor[meal_datetime.weekday()]
        
        embed = disnake.Embed(
            title=f"{학교명}",
            description=f'날짜 : {meal_datetime.month}월 {meal_datetime.day}일 ({weekday_str})',
            color=disnake.Color(0xD3851F)
        )
        embed.add_field(name='메뉴 목록', value=f"```\n{meal_info}\n```", inline=False)
        
        if calorie_info != "칼로리 정보가 없습니다.":
            embed.set_footer(text=f'칼로리 정보: {calorie_info}')
        else:
            embed.set_footer(text=None)

        interaction_user_id = ctx.user.id

        이전날 = Button(label="전날", style=ButtonStyle.danger)
        세부사항 = Button(label="▼", style=ButtonStyle.gray)
        다음날 = Button(label="다음날", style=ButtonStyle.blurple)
        세부사항2 = Button(label="▲", style=ButtonStyle.gray)

        async def check_user(interaction: disnake.Interaction):
            if interaction.user.id != interaction_user_id:
                await interaction.response.send_message("다른 사람의 상호작용입니다.", ephemeral=True)
                return False
            return True
        
        async def previous_day_callback(interaction: disnake.Interaction):
            if not await check_user(interaction):
                return

            try:
                await interaction.response.defer(ephemeral=False)
                await interaction.message.edit(embed=embed, view=View())

                nonlocal meal_date
                if meal_date is None:
                    meal_date = datetime.now().strftime('%Y%m%d')

                previous_date = datetime.strptime(meal_date, '%Y%m%d') - timedelta(days=1)
                meal_info, meal_date = await get_meal_info_async(학교명, edu_office_code, previous_date.strftime('%Y%m%d'))
                meal_info_formatted = meal_info.replace('<br/>', '\n')
                calorie_info, _ = await get_calorie_info_async(학교명, edu_office_code, previous_date.strftime('%Y%m%d'))
                meal_datetime = datetime.strptime(meal_date, '%Y%m%d')
                weekday_str = weekday_kor[meal_datetime.weekday()]

                embed.description = f'날짜 : {meal_datetime.month}월 {meal_datetime.day}일 ({weekday_str})'
                embed.set_field_at(0, name='메뉴 목록', value=f"```\n{meal_info_formatted}\n```", inline=False)
                
                if calorie_info != "칼로리 정보가 없습니다.":
                    embed.set_footer(text=f'칼로리 정보: {calorie_info}')
                else:
                    embed.set_footer(text=None)

                if len(embed.fields) > 1:
                    embed.remove_field(1)
                if len(embed.fields) > 1:
                    embed.remove_field(1)

                세부사항.disabled = meal_info == "급식 정보가 없습니다."
                await interaction.message.edit(embed=embed, view=myview)

            except Exception as e:
                await interaction.channel.send(f"Error: {str(e)}")

        async def next_day_callback(interaction: disnake.Interaction):
            if not await check_user(interaction):
                return

            try:
                await interaction.response.defer(ephemeral=False)
                await interaction.message.edit(embed=embed, view=View())

                nonlocal meal_date
                if meal_date is None:
                    meal_date = datetime.now().strftime('%Y%m%d')
                next_date = datetime.strptime(meal_date, '%Y%m%d') + timedelta(days=1)
                meal_info, meal_date = await get_meal_info_async(학교명, edu_office_code, next_date.strftime('%Y%m%d'))
                meal_info_formatted = meal_info.replace('<br/>', '\n')
                calorie_info, _ = await get_calorie_info_async(학교명, edu_office_code, next_date.strftime('%Y%m%d'))
                meal_datetime = datetime.strptime(meal_date, '%Y%m%d')
                weekday_str = weekday_kor[meal_datetime.weekday()]

                embed.description = f'날짜 : {meal_datetime.month}월 {meal_datetime.day}일 ({weekday_str})'
                embed.set_field_at(0, name='메뉴 목록', value=f"```\n{meal_info_formatted}\n```", inline=False)
                
                if calorie_info != "칼로리 정보가 없습니다.":
                    embed.set_footer(text=f'칼로리 정보: {calorie_info}')
                else:
                    embed.set_footer(text=None)

                if len(embed.fields) > 1:
                    embed.remove_field(1)
                if len(embed.fields) > 1:
                    embed.remove_field(1)

                세부사항.disabled = meal_info == "급식 정보가 없습니다."
                await interaction.message.edit(embed=embed, view=myview)

            except Exception as e:
                await interaction.channel.send(f"Error: {str(e)}")

        async def details_callback(interaction: disnake.Interaction):
            if not await check_user(interaction):
                return

            try:
                await interaction.response.defer(ephemeral=False)
                await interaction.message.edit(embed=embed, view=View())

                nonlocal meal_date
                if meal_date is None:
                    meal_date = datetime.now().strftime('%Y%m%d')
                
                nutrition_info = await get_nutrition_info_async(학교명, edu_office_code, meal_date)
                origin_info = await get_origin_info_async(학교명, edu_office_code, meal_date)

                nutrition_list = nutrition_info.replace('<br/>', '\n')
                origin_list = origin_info.replace('<br/>', '\n')

                embed.add_field(name='영양 정보', value=f"```\n{nutrition_list}\n```", inline=False)
                embed.add_field(name='원산지 정보', value=f"```\n{origin_list}\n```", inline=False)

                myview = View(timeout=1800)
                세부사항2.callback = details_callback2

                myview.add_item(이전날)
                myview.add_item(세부사항2)
                myview.add_item(다음날)

                await interaction.message.edit(embed=embed, view=myview)

            except Exception as e:
                await interaction.channel.send(f"Error: {str(e)}")

        async def details_callback2(interaction: disnake.Interaction):
            if not await check_user(interaction):
                return

            await interaction.response.defer(ephemeral=False)
            await interaction.message.edit(embed=embed, view=View())
            
            embed.remove_field(1)
            embed.remove_field(1)

            세부사항.callback = details_callback

            myview = View(timeout=180)
            myview.add_item(이전날)
            myview.add_item(세부사항)
            myview.add_item(다음날)

            await interaction.message.edit(embed=embed, view=myview)

        세부사항2.callback = details_callback2
        세부사항.callback = details_callback
        이전날.callback = previous_day_callback
        다음날.callback = next_day_callback

        myview = View(timeout=1800)
        myview.add_item(이전날)

        세부사항.disabled = meal_info == "급식 정보가 없습니다."
        myview.add_item(세부사항)

        myview.add_item(다음날)

        if meal_info:  
            await ctx.send(embed=embed, view=myview)
        else:
            await ctx.send("해당 날짜의 급식 정보가 없습니다.")

    except Exception as e:
        await ctx.response.defer(ephemeral=False)
        await ctx.send(f"Error: {str(e)}")

@bot.slash_command(name="날씨", description="날씨를 볼 수 있습니다.")
async def weather(ctx, region: str = commands.Param(name="지역", description="지역을 입력하세요.")):
    if ctx.guild is None or not await check_permissions(ctx):
        return
    if not await tos(ctx):
        return
    await command_use_log(ctx, "날씨", f"{region}")
    if not ctx.response.is_done():
        await ctx.response.defer(ephemeral=False)
    try:
        now = datetime.now()  # 현재 시각 가져오기

        search = region + " 날씨"
        url = "https://search.naver.com/search.naver?where=nexearch&sm=top_hty&fbm=0&ie=utf8&query=" + search
        hdr = {'User-Agent': 'Mozilla/5.0'}
        req = requests.get(url, headers=hdr)
        html = req.text
        bsObj = bs4.BeautifulSoup(html, "html.parser")

        temperature = bsObj.find('div', class_='temperature_text')
        온도텍 = temperature.text
        온도결과 = re.sub(r'[^0-9.]', '', 온도텍.strip().split('°')[0])

        체감온도 = bsObj.find('div', class_='sort')
        체감온도텍 = 체감온도.text
        체감온도결과 = re.sub(r'[^0-9.]', '', 체감온도텍.strip().split('°')[0])

        미세먼지 = bsObj.find('li', class_='item_today level2')
        미세2 = 미세먼지.find('span', class_='txt')
        미세먼지결과 = 미세2.text
        
        if 미세먼지결과 == "좋음":
            미세결과 = "😀(좋음)"
        elif 미세먼지결과 == "보통":
            미세결과 = "😐(보통)"
        elif 미세먼지결과 == "나쁨":
            미세결과 = "😷(나쁨)"
        elif 미세먼지결과 == "매우나쁨":
            미세결과 = "😡(매우나쁨)"
        else:
            미세결과 = "정보 없음"

        초미세먼지들 = bsObj.find_all('li', class_='item_today level2')
        if len(초미세먼지들) >= 2:
            초미세먼지 = 초미세먼지들[1]  
            미세2 = 초미세먼지.find('span', class_='txt')
            초미세먼지결과 = 미세2.text
            if 초미세먼지결과 == "좋음":
                초미세결과 = "😀(좋음)"
            elif 초미세먼지결과 == "보통":
                초미세결과 = "😐(보통)"
            elif 초미세먼지결과 == "나쁨":
                초미세결과 = "😷(나쁨)"
            elif 초미세먼지결과 == "매우나쁨":
                초미세결과 = "😡(매우나쁨)"
            else:
                초미세결과 = "정보 없음"
        else:
            초미세결과 = "정보 없음"

        기후 = bsObj.find('p', class_='summary')
        기후2 = 기후.find('span', class_='weather before_slash')
        기후결과 = 기후2.text

        embed = disnake.Embed(title=region + ' 날씨 정보', description='현재 온도', color=disnake.Color(0x2ECCFA))
        embed.add_field(name=f"{온도결과}℃", value=f'체감 {체감온도결과}', inline=False)
        embed.add_field(name="미세먼지", value=f"{미세결과}", inline=False)
        embed.add_field(name="초미세먼지", value=f"{초미세결과}", inline=False)
        embed.add_field(name="기후", value=f"{기후결과}", inline=False)

        embed.set_footer(text=f"시각 : {now.hour}시 {now.minute}분 {now.second}초")
    
        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send("올바른 지역을 입력해주세요")

@bot.slash_command(name="ai질문", description="GPT에게 질문하거나 DALL·E에게 이미지 생성을 요청합니다.")
async def ai_ask(ctx,
                  choice: str = commands.Param(name="모델", choices=["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo", "gpt-4o", "gpt-4o-mini", "DALL·E"]), 
                  ask: str = commands.Param(name="질문")):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return

    await command_use_log(ctx, "ai질문", f"{choice}, {ask}")
    if not await member_status(ctx):
        return
    await membership(ctx)  # 회원 상태 확인

    # 응답 지연
    if not ctx.response.is_done():
        await ctx.response.defer()  # 응답 지연

    # 사용자의 크레딧 확인
    user_credit = await get_user_credit(ctx.author.id)

    # DALL·E 사용 시 2크레딧, 다른 모델 사용 시 1크레딧
    credit_cost = 2 if choice == "DALL·E" else 1

    if user_credit < credit_cost:
        return await ctx.followup.send("크레딧이 부족합니다. 더 이상 질문할 수 없습니다.")

    # 크레딧 사용
    await use_user_credit(ctx.author.id, credit_cost)

    try:
        if choice == "DALL·E":
            # DALL·E 호출
            image_url = generate_image(ask)
            if "오류" in image_url:
                await ctx.followup.send(image_url)  # 오류 메시지 전송
            else:
                embed = disnake.Embed(title="이미지 생성", color=0x00ff00)
                embed.add_field(name="질문", value=f"{ask}", inline=False)
                embed.set_image(url=image_url)
                embed.add_field(name="이미지 링크", value=f"[전체 크기 보기]({image_url})", inline=False)
                await ctx.followup.send(embed=embed)  # 후속 응답으로 보내기
        else:
            # GPT API 호출
            answer = get_gpt_response(ask, choice)

            if len(answer) > 1024:
                # 답변이 1024자를 초과할 경우 텍스트 파일로 저장
                file_path = os.path.join(os.getcwd(), "답변.txt")  # 현재 작업 디렉토리 경로
                with open(file_path, "w", encoding="utf-8") as file:
                    file.write(answer)
                await ctx.followup.send("답변이 너무 길어 텍스트 파일로 전송합니다.", file=disnake.File(file_path))
                os.remove(file_path)  # 파일 전송 후 삭제
            else:
                # 임베드 응답 생성
                embed = disnake.Embed(title="GPT 응답", color=0x00ff00)
                embed.add_field(name="모델", value=f"{choice}", inline=False)
                embed.add_field(name="질문", value=f"{ask}", inline=False)
                embed.add_field(name="답변", value=f"{answer}", inline=False)
                await ctx.followup.send(embed=embed)  # 후속 응답으로 보내기

    except Exception as e:
        print(f"오류 발생: {e}")  # 로그 출력
        await ctx.followup.send("오류가 발생했습니다. 다시 시도해 주세요.")

@bot.slash_command(name="ai대화", description="스톤 AI와 대화합니다.")
async def ai_chat(ctx, ask: str = commands.Param(name="내용")):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return

    await command_use_log(ctx, "ai대화", f"{ask}")
    if not await member_status(ctx):
        return
    await membership(ctx)  # 회원 상태 확인

    # 응답 지연
    if not ctx.response.is_done():
        await ctx.response.defer()  # 응답 지연

    try:
        # GPT API 호출
        answer = get_gpt_response(('''너는 이제부터 스톤이야, 
        돌맹이는 스톤을 만든 개발자야, 
        반말로 말을 해줘, 
        친근하게 말을 해줘, 
        이모지를 사용해서 말을 해줘, 
        너는 돌맹이가 만들었어, 
        ''' + ask), "gpt-4o-mini")

        if len(answer) > 500:
            pass
        else:
            # 임베드 응답 생성
            embed = disnake.Embed(title="스톤 AI", description=f"{answer}", color=0x00ff00)
            await ctx.followup.send(embed=embed)  # 후속 응답으로 보내기

    except Exception as e:
        print(f"오류 발생: {e}")  # 로그 출력
        await ctx.followup.send("오류가 발생했습니다. 다시 시도해 주세요.")

LANGUAGES = {
    'af': '아프리칸스 (afrikaans)',
    'sq': '알바니아어 (albanian)',
    'am': '암하라어 (amharic)',
    'ar': '아랍어 (arabic)',
    'hy': '아르메니아어 (armenian)',
    'az': '아제르바이잔어 (azerbaijani)',
    'eu': '바스크어 (basque)',
    'be': '벨라루스어 (belarusian)',
    'bn': '벵골어 (bengali)',
    'bs': '보스니아어 (bosnian)',
    'bg': '불가리아어 (bulgarian)',
    'ca': '카탈루냐어 (catalan)',
    'ceb': '세부아노어 (cebuano)',
    'ny': '치체와어 (chichewa)',
    'zh-cn': '중국어 (간체) (chinese (simplified))',
    'zh-tw': '중국어 (번체) (chinese (traditional))',
    'co': '코르시카어 (corsican)',
    'hr': '크로아티아어 (croatian)',
    'cs': '체코어 (czech)',
    'da': '덴마크어 (danish)',
    'nl': '네덜란드어 (dutch)',
    'en': '영어 (english)',
    'eo': '에스페란토 (esperanto)',
    'et': '에스토니아어 (estonian)',
    'tl': '필리핀어 (filipino)',
    'fi': '핀란드어 (finnish)',
    'fr': '프랑스어 (french)',
    'fy': '프리슬란드어 (frisian)',
    'gl': '갈리시아어 (galician)',
    'ka': '조지아어 (georgian)',
    'de': '독일어 (german)',
    'el': '그리스어 (greek)',
    'gu': '구자라트어 (gujarati)',
    'ht': '아이티 크리올어 (haitian creole)',
    'ha': '하우사어 (hausa)',
    'haw': '하와이어 (hawaiian)',
    'iw': '히브리어 (hebrew)',
    'he': '히브리어 (hebrew)',
    'hi': '힌디어 (hindi)',
    'hmn': '몽골어 (hmong)',
    'hu': '헝가리어 (hungarian)',
    'is': '아이슬란드어 (icelandic)',
    'ig': '이그보어 (igbo)',
    'id': '인도네시아어 (indonesian)',
    'ga': '아일랜드어 (irish)',
    'it': '이탈리아어 (italian)',
    'ja': '일본어 (japanese)',
    'jw': '자바어 (javanese)',
    'kn': '칸나다어 (kannada)',
    'kk': '카자흐어 (kazakh)',
    'km': '크메르어 (khmer)',
    'ko': '한국어 (korean)',
    'ku': '쿠르드어 (kurmanji)',
    'ky': '키르기스어 (kyrgyz)',
    'lo': '라오어 (lao)',
    'la': '라틴어 (latin)',
    'lv': '라트비아어 (latvian)',
    'lt': '리투아니아어 (lithuanian)',
    'lb': '룩셈부르크어 (luxembourgish)',
    'mk': '마케도니아어 (macedonian)',
    'mg': '말라가시어 (malagasy)',
    'ms': '말레이어 (malay)',
    'ml': '말라얄람어 (malayalam)',
    'mt': '몰타어 (maltese)',
    'mi': '마오리어 (maori)',
    'mr': '마라티어 (marathi)',
    'mn': '몽골어 (mongolian)',
    'my': '미얀마어 (burmese)',
    'ne': '네팔어 (nepali)',
    'no': '노르웨이어 (norwegian)',
    'or': '오디아어 (odia)',
    'ps': '파슈토어 (pashto)',
    'fa': '페르시아어 (persian)',
    'pl': '폴란드어 (polish)',
    'pt': '포르투갈어 (portuguese)',
    'pa': '펀자브어 (punjabi)',
    'ro': '루마니아어 (romanian)',
    'ru': '러시아어 (russian)',
    'sm': '사모아어 (samoan)',
    'gd': '스코틀랜드 게일어 (scots gaelic)',
    'sr': '세르비아어 (serbian)',
    'st': '세소토어 (sesotho)',
    'sn': '쇼나어 (shona)',
    'sd': '신디어 (sindhi)',
    'si': '신할라어 (sinhala)',
    'sk': '슬로바키아어 (slovak)',
    'sl': '슬로베니아어 (slovenian)',
    'so': '소말리어 (somali)',
    'es': '스페인어 (spanish)',
    'su': '순다어 (sundanese)',
    'sw': '스와힐리어 (swahili)',
    'sv': '스웨덴어 (swedish)',
    'tg': '타지크어 (tajik)',
    'ta': '타밀어 (tamil)',
    'te': '텔루구어 (telugu)',
    'th': '태국어 (thai)',
    'tr': '터키어 (turkish)',
    'uk': '우크라이나어 (ukrainian)',
    'ur': '우르두어 (urdu)',
    'ug': '위구르어 (uyghur)',
    'uz': '우즈벡어 (uzbek)',
    'vi': '베트남어 (vietnamese)',
    'cy': '웨일스어 (welsh)',
    'xh': '코사어 (xhosa)',
    'yi': '이디시어 (yiddish)',
    'yo': '요루바어 (yoruba)',
    'zu': '줄루어 (zulu)'
}

# LANGUAGES 딕셔너리를 언어 코드 목록으로 변환
LANGUAGE_CHOICES = list(LANGUAGES.keys())

@bot.slash_command(name="번역", description="텍스트를 선택한 언어로 번역합니다.")
async def translation(ctx, languages: str = commands.Param(name="언어"), text: str = commands.Param(name="내용")):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "번역", f"{languages}, {text}")
    translator = Translator()
    
    # 유효한 언어 코드인지 확인
    if languages not in LANGUAGE_CHOICES:
        embed = disnake.Embed(color=0xFF0000)
        embed.add_field(name="❌ 오류", value="유효한 언어 코드를 입력하세요.")
        await ctx.send(embed=embed, ephemeral=True)
        return
    
    result = translator.translate(text, dest=languages)
    translated_text = result.text

    embed = disnake.Embed(title="번역 결과", color=0x00ff00)
    embed.add_field(name="언어", value=f"{LANGUAGES[languages]}")  # 선택한 언어 이름을 표시
    embed.add_field(name="원본 텍스트", value=text, inline=False)
    embed.add_field(name="번역된 텍스트", value=translated_text, inline=False)
    await ctx.send(embed=embed)

class LanguageView(disnake.ui.View):
    def __init__(self, languages, per_page=5):
        super().__init__(timeout=None)
        self.languages = languages
        self.per_page = per_page
        self.current_page = 0
        self.max_page = (len(languages) - 1) // per_page
        self.message = None

        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        if self.current_page > 0:
            self.add_item(PreviousButton())
        if self.current_page < self.max_page:
            self.add_item(NextButton())

    async def update_message(self, ctx=None):
        embed = await self.create_embed()
        self.update_buttons()
        if ctx:
            await ctx.followup.edit_message(embed=embed, view=self)
        elif self.message:
            await self.message.edit(embed=embed, view=self)

    async def create_embed(self):
        embed = disnake.Embed(title="지원 언어 목록", color=0x00ff00)
        start = self.current_page * self.per_page
        end = start + self.per_page

        for lang_code, lang_name in list(self.languages.items())[start:end]:
            embed.add_field(name=lang_code, value=lang_name, inline=False)

        embed.add_field(name="", value=f"📄 페이지 {self.current_page + 1}/{self.max_page + 1}", inline=False)
        return embed

class PreviousButton(disnake.ui.Button):
    def __init__(self):
        super().__init__(label="이전", style=disnake.ButtonStyle.primary)

    async def callback(self, ctx: disnake.Interaction):
        view: LanguageView = self.view
        if view.current_page > 0:
            view.current_page -= 1
            await view.update_message(ctx)

class NextButton(disnake.ui.Button):
    def __init__(self):
        super().__init__(label="다음", style=disnake.ButtonStyle.primary)

    async def callback(self, ctx: disnake.Interaction):
        view: LanguageView = self.view
        if view.current_page < view.max_page:
            view.current_page += 1
            await view.update_message(ctx)

@bot.slash_command(name="언어목록", description="지원하는 언어 목록을 확인합니다.")
async def language_list(ctx: disnake.CommandInteraction):
    if not await tos(ctx):
        return
    view = LanguageView(LANGUAGES)
    view.message = await ctx.send(embed=await view.create_embed(), view=view)

@bot.slash_command(name="tts", description="입력한 텍스트를 음성으로 변환하여 재생합니다.")
async def tts(ctx: disnake.CommandInteraction, text: str = commands.Param(name="텍스트")):
    if not await tos(ctx):
        return
    await ctx.response.defer()  # 응답 지연

    # 음성 채널에 연결
    voice_channel = ctx.author.voice.channel if ctx.author.voice else None
    if voice_channel is None:
        return await ctx.response.send_message("음성 채널에 들어가야 합니다.", ephemeral=True)

    # 현재 연결된 음성 클라이언트가 있는지 확인
    voice_client = disnake.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice_client is None:
        voice_client = await voice_channel.connect()
    else:
        # 이미 연결되어 있다면 기존 음성 클라이언트 사용
        await voice_client.move_to(voice_channel)

    # TTS 변환
    tts = gTTS(text=text, lang='ko')  # 한국어로 변환
    with tempfile.NamedTemporaryFile(delete=True) as tmp_file:
        tts.save(f"{tmp_file.name}.mp3")  # 임시 파일로 저장

        # 음성 파일 재생
        voice_client.play(disnake.FFmpegPCMAudio(f"{tmp_file.name}.mp3"))

        embed = disnake.Embed(title="TTS 재생", description=f"입력한 텍스트가 음성으로 변환되어 재생 중입니다:\n\n**{text}**", color=0x00ff00)
        await ctx.followup.send(embed=embed, ephemeral=True)

        # 재생이 끝날 때까지 대기
        while voice_client.is_playing():
            await asyncio.sleep(1)  # asyncio.sleep 사용

# 유튜브 다운로드 설정
youtube_dl.utils.bug_reports_message = lambda: ''
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}
ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}
ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

# 음악 소스 클래스
class YTDLSource(disnake.PCMVolumeTransformer):
    YTDL_OPTIONS = {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'audioformat': 'mp3',
        'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': True,
    }

    def __init__(self, source, *, data):
        super().__init__(source)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.thumbnail = data.get('thumbnail')
        self.original = source  # Ensure original is set correctly

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        ydl = youtube_dl.YoutubeDL(cls.YTDL_OPTIONS)
        data = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=not stream))
        if 'entries' in data:
            data = data['entries'][0]
        filename = data['url'] if stream else ydl.prepare_filename(data)
        source = FFmpegPCMAudio(filename, **ffmpeg_options)
        return cls(source, data=data)

class VolumeChangeModal(disnake.ui.Modal):
    def __init__(self):
        components = [
            disnake.ui.TextInput(
                label="변경할 음량 (1~100)",
                placeholder="음량을 입력하세요",
                custom_id="volume_input",
                style=TextInputStyle.short,
                max_length=3
            )
        ]
        super().__init__(title="음량 변경", components=components)

    async def callback(self, ctx: disnake.ModalInteraction):
        try:
            change = int(ctx.text_values['volume_input'])

            if not (1 <= change <= 100):
                await ctx.send("음량은 1에서 100 사이의 값이어야 합니다.", ephemeral=True)
                return
            
            # 1~100을 0.0~1.0으로 변환
            new_volume = (change / 100)
            if ctx.guild.voice_client and ctx.guild.voice_client.source:
                ctx.guild.voice_client.source.volume = new_volume
                await ctx.send(f"현재 음량: {change}", ephemeral=True)
            else:
                await ctx.send("음성을 재생 중이지 않습니다.", ephemeral=True)
        except ValueError:
            await ctx.send("올바른 음량 값을 입력하세요.", ephemeral=True)

class MusicChangeModal(Modal):
    def __init__(self):
        components = [
            TextInput(
                label="변경할 음악 제목이나 링크",
                placeholder="제목이나 링크를 입력하세요",
                custom_id="new_music_input",
                style=TextInputStyle.short
            )
        ]
        super().__init__(title="음악 변경", components=components)

    async def callback(self, ctx: disnake.ModalInteraction):
        try:
            new_url_or_name = ctx.text_values['new_music_input']
            # URL인지 확인하고, 그렇지 않으면 검색어로 처리
            if not new_url_or_name.startswith("http"):
                new_url_or_name = f"ytsearch:{new_url_or_name}"
            
            new_player = await YTDLSource.from_url(new_url_or_name, loop=asyncio.get_event_loop(), stream=True)

            if ctx.guild.voice_client.source:
                ctx.guild.voice_client.stop()
                ctx.guild.voice_client.play(new_player)

                change_embed = disnake.Embed(color=0x00ff00, description=f"새로운 음악을 재생합니다: {new_url_or_name}")
                await ctx.response.edit_message(embed=change_embed)
            else:
                await ctx.send("음성을 재생 중이지 않습니다.", ephemeral=True)
        except Exception as e:
            await ctx.send("음악 변경 중 오류가 발생했습니다. 다시 시도해주세요.", ephemeral=True)
            logging.error("음악 변경 중 오류가 발생했습니다.", exc_info=True)  # 오류 로그를 기록하여 문제를 확인할 수 있도록 합니다.
            await ctx.send("음악 변경 중 오류가 발생했습니다. 다시 시도해주세요.", ephemeral=True)
            print(e)  # 오류 로그를 출력하여 문제를 확인할 수 있도록 합니다.

def cleanup(self):
    if hasattr(self, 'original'):
        self.original.cleanup()

@asynccontextmanager
async def connect_db():
    db_path = os.path.join('system_database', 'music.db')
    conn = await aiosqlite.connect(db_path)
    try:
        yield conn
    finally:
        await conn.close()

waiting_songs = defaultdict(list)
voice_clients = {}

@bot.slash_command(name='재생', description='유튜브 링크 또는 제목으로 음악을 재생합니다.')
async def play(ctx, url_or_name: str):
    await ctx.response.defer()
    if not await check_permissions(ctx):
        return

    await command_use_log(ctx, "재생", url_or_name)

    if ctx.author.voice is None:
        return await ctx.send("음성 채널에 연결되어 있지 않습니다. 먼저 음성 채널에 들어가세요.")

    channel_id = ctx.author.voice.channel.id
    voice_client = await connect_voice_client(ctx, channel_id)

    if voice_client.is_playing():
        waiting_songs[channel_id].append(url_or_name)
        return await ctx.send(f"현재 음악이 재생 중입니다. '{url_or_name}'가 끝나면 재생됩니다.")

    if await is_playlist(url_or_name):
        await handle_playlist(ctx, url_or_name, channel_id)
    else:
        await play_song(ctx, channel_id, url_or_name, ctx.author)

async def connect_voice_client(ctx, channel_id):
    if channel_id not in voice_clients or not voice_clients[channel_id].is_connected():
        try:
            voice_client = await ctx.author.voice.channel.connect()
            voice_clients[channel_id] = voice_client
        except disnake.ClientException:
            voice_client = voice_clients[channel_id]
    return voice_clients[channel_id]

async def handle_playlist(ctx, url_or_name, channel_id):
    playlist_owner = await get_playlist_owner(url_or_name)
    if playlist_owner != ctx.author.id:
        return await ctx.send(embed=disnake.Embed(color=0xff0000, title="오류", description="이 플레이리스트의 소유자가 아닙니다."))

    songs = await get_songs_from_playlist(url_or_name)
    waiting_songs[channel_id].extend(songs)
    await play_next_song(ctx, channel_id)

async def play_song(ctx, channel_id, url_or_name, author):
    voice_client = voice_clients.get(channel_id)

    if voice_client is None or not voice_client.is_connected():
        return await ctx.send("음성 채널에 연결되어 있지 않습니다.")

    try:
        player = await YTDLSource.from_url(f"ytsearch:{url_or_name}", loop=bot.loop, stream=True)
        voice_client.play(player, after=lambda e: bot.loop.create_task(play_next_song(ctx, channel_id, player)) if e is None else print(f"Error: {e}"))
        await send_webhook_message(f"{author.id}님이 {ctx.guild.id}에서 {player.title} 음악을 재생했습니다.")
        embed = disnake.Embed(color=0x00ff00, title="음악 재생", description=player.title)
        if player.thumbnail:
            embed.set_image(url=player.thumbnail)
        
        # 음악 길이와 현재 재생 분초 표시
        duration = player.data.get('duration')
        if duration:
            days, remainder = divmod(duration, 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, seconds = divmod(remainder, 60)
            if days > 0:
                length_str = f"{days}일 {hours:02d}:{minutes:02d}:{seconds:02d}"
            elif hours > 0:
                length_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            else:
                length_str = f"{minutes:02d}:{seconds:02d}"
            embed.set_footer(text=f"재생한 사람: {author.display_name} | 길이: {length_str}")
        else:
            embed.set_footer(text=f"재생한 사람: {author.display_name}")
        
        await send_control_buttons(ctx, embed)

    except Exception as e:
        await ctx.send(embed=disnake.Embed(color=0xff0000, title="오류", description=str(e)))

async def play_next_song(ctx, channel_id, player=None):
    # 대기 중인 곡이 없을 경우 처리
    if not waiting_songs.get(channel_id):
        channel = bot.get_channel(ctx.channel.id)
        if channel:
            await send_webhook_message(f"{ctx.author.id}님이 {ctx.guild.id}에서 재생한 {player.title} 음악이 끝났습니다.")
        else:
            return
    else:
        next_song = waiting_songs[channel_id].pop(0)

    next_song = waiting_songs[channel_id].pop(0)
    await play_song(ctx, channel_id, next_song, ctx.author)

@asynccontextmanager
async def connect_db():
    db_path = os.path.join('system_database', 'music.db')
    conn = await aiosqlite.connect(db_path)
    try:
        yield conn
    finally:
        await conn.close()

async def is_playlist(name):
    async with connect_db() as conn:
        cursor = await conn.execute("SELECT COUNT(DISTINCT playlist_name) FROM playlists WHERE playlist_name = ?", (name,))
        result = await cursor.fetchone()
        return result[0] > 0

async def get_playlist_owner(playlist_name):
    async with connect_db() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT user_id FROM playlists WHERE playlist_name = ?", (playlist_name,))
            owner = await cursor.fetchone()
    return owner[0] if owner else None

async def get_songs_from_playlist(playlist_name):
    async with connect_db() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT song FROM playlists WHERE playlist_name = ?", (playlist_name,))
            return [row[0] for row in await cursor.fetchall()]

async def send_control_buttons(ctx, embed):
    buttons = [
        disnake.ui.Button(label="일시 정지", style=disnake.ButtonStyle.red, custom_id="pause"),
        disnake.ui.Button(label="다시 재생", style=disnake.ButtonStyle.green, custom_id="resume"),
        disnake.ui.Button(label="음량 변경", style=disnake.ButtonStyle.blurple, custom_id="volume_change"),
        disnake.ui.Button(label="노래 변경", style=disnake.ButtonStyle.grey, custom_id="change_song"),
        disnake.ui.Button(label="반복", style=disnake.ButtonStyle.green, custom_id="repeat"),
    ]

    button_row = disnake.ui.View(timeout=None)
    for button in buttons:
        button_row.add_item(button)

    await ctx.send(embed=embed, view=button_row)

    button_row.children[0].callback = pause_callback
    button_row.children[1].callback = resume_callback
    button_row.children[2].callback = volume_change_callback
    button_row.children[3].callback = change_song_callback
    button_row.children[4].callback = repeat_callback

async def pause_callback(interaction):
    interaction.guild.voice_client.pause()
    embed = disnake.Embed(color=0x00ff00)
    embed.add_field(name="일시 정지", value="음악이 일시 정지되었습니다.")
    await interaction.response.send_message(embed=embed, ephemeral=True)

async def resume_callback(interaction):
    if interaction.guild.voice_client.is_paused():
        interaction.guild.voice_client.resume()
        embed = disnake.Embed(color=0x00ff00)
        embed.add_field(name="다시 재생", value="음악이 다시 재생되었습니다.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        embed = disnake.Embed(color=0xff0000)
        embed.add_field(name="오류", value="현재 재생 중인 음악이 없습니다.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def volume_change_callback(interaction):
    await interaction.response.send_modal(VolumeChangeModal())

async def change_song_callback(interaction):
    await interaction.response.send_modal(MusicChangeModal())

async def repeat_callback(interaction):
    if interaction.guild.voice_client and interaction.guild.voice_client.source:
        current_song = interaction.guild.voice_client.source.data['url']
        channel_id = interaction.guild.voice_client.channel.id
        waiting_songs[channel_id].append(current_song)
        embed = disnake.Embed(color=0x00ff00)
        embed.add_field(name="반복", value="현재 재생 중인 곡이 대기열에 추가되었습니다.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        embed = disnake.Embed(color=0xff0000)
        embed.add_field(name="오류", value="현재 재생 중인 곡이 없습니다.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

class VolumeChangeModal(disnake.ui.Modal):
    def __init__(self):
        components = [
            disnake.ui.TextInput(
                label="변경할 음량 (1~100)",
                placeholder="음량을 입력하세요",
                custom_id="volume_input",
                style=TextInputStyle.short,
                max_length=3
            )
        ]
        super().__init__(title="음량 변경", components=components)

    async def callback(self, ctx: disnake.ModalInteraction):
        try:
            change = int(ctx.text_values['volume_input'])

            if not (1 <= change <= 100):
                await ctx.send("음량은 1에서 100 사이의 값이어야 합니다.", ephemeral=True)
                return
            
            # 1~100을 0.0~1.0으로 변환
            new_volume = (change / 100)
            if ctx.guild.voice_client and ctx.guild.voice_client.source:
                ctx.guild.voice_client.source.volume = new_volume
                embed = disnake.Embed(color=0x00ff00)
                embed.add_field(name="음량 변경", value=f"현재 음량: {new_volume * 100:.0f}%")
                await ctx.send(embed=embed, ephemeral=True)
            else:
                await ctx.send("음성을 재생 중이지 않습니다.", ephemeral=True)
        except ValueError:
            await ctx.send("올바른 음량 값을 입력하세요.", ephemeral=True)

class MusicChangeModal(Modal):
    def __init__(self):
        components = [
            TextInput(
                label="변경할 음악 제목이나 링크",
                placeholder="제목이나 링크를 입력하세요",
                custom_id="new_music_input",
                style=TextInputStyle.short
            )
        ]
        super().__init__(title="음악 변경", components=components)

    async def callback(self, ctx: disnake.ModalInteraction):
        try:
            new_url_or_name = ctx.text_values['new_music_input']
            # URL인지 확인하고, 그렇지 않으면 검색어로 처리
            if not new_url_or_name.startswith("http"):
                new_url_or_name = f"ytsearch:{new_url_or_name}"
            
            new_player = await YTDLSource.from_url(new_url_or_name, loop=asyncio.get_event_loop(), stream=True)

            if ctx.guild.voice_client.source:
                ctx.guild.voice_client.stop()
                ctx.guild.voice_client.play(new_player)

                change_embed = disnake.Embed(color=0x00ff00, description=f"새로운 음악을 재생합니다: {new_url_or_name}")
                await ctx.response.edit_message(embed=change_embed)
            else:
                await ctx.send("음성을 재생 중이지 않습니다.", ephemeral=True)
        except Exception as e:
            await ctx.send("음악 변경 중 오류가 발생했습니다. 다시 시도해주세요.", ephemeral=True)
            logging.error("음악 변경 중 오류가 발생했습니다.", exc_info=True)  # 오류 로그를 기록하여 문제를 확인할 수 있도록 합니다.
            await ctx.send("음악 변경 중 오류가 발생했습니다. 다시 시도해주세요.", ephemeral=True)
            print(e)  # 오류 로그를 출력하여 문제를 확인할 수 있도록 합니다.

@bot.slash_command(name='입장', description="음성 채널에 입장합니다.")
async def join(ctx):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "입장", None)
    embed = disnake.Embed(color=0x00ff00)
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        if ctx.guild.voice_client is not None:
            await ctx.guild.voice_client.move_to(channel)
            embed.description = "음성 채널로 이동했습니다."
        else:
            await channel.connect()
            embed.description = "음성 채널에 연결되었습니다."
    else:
        embed.description = "음성 채널에 연결되어 있지 않습니다."
        embed.color = 0xff0000

    await ctx.send(embed=embed)

@bot.slash_command(name='볼륨', description="플레이어의 볼륨을 변경합니다.")
async def volume(ctx, volume: int):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "볼륨", f"{volume}")
    embed = disnake.Embed(color=0x00ff00)
    if ctx.guild.voice_client is None:
        embed.description = "음성 채널에 연결되어 있지 않습니다."
        embed.color = 0xff0000
    else:
        ctx.guild.voice_client.source.volume = volume / 100
        embed.description = f"볼륨을 {volume}%로 변경했습니다."

    await ctx.send(embed=embed)

@bot.slash_command(name='정지', description="음악을 중지하고 음성 채널에서 나갑니다.")
async def stop(ctx):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "정지", None)
    await ctx.response.defer()
    embed = disnake.Embed(color=0x00ff00)
    if ctx.guild.voice_client:
        await ctx.guild.voice_client.disconnect()
        embed.description = "음악을 중지하고 음성 채널에서 나갔습니다."
    else:
        embed.description = "봇이 음성 채널에 연결되어 있지 않습니다."
        embed.color = 0xff0000

    await ctx.send(embed=embed)

@bot.slash_command(name='일시정지', description="음악을 일시정지합니다.")
async def pause(ctx):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "일시정지", None)
    embed = disnake.Embed(color=0x00ff00)
    if ctx.guild.voice_client is None or not ctx.guild.voice_client.is_playing():
        embed.description = "음악이 이미 일시 정지 중이거나 재생 중이지 않습니다."
        embed.color = 0xff0000
    else:
        ctx.guild.voice_client.pause()
        embed.description = "음악을 일시 정지했습니다."

    await ctx.send(embed=embed)

@bot.slash_command(name='다시재생', description="일시중지된 음악을 다시 재생합니다.")
async def resume(ctx):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "다시재생", None)
    voice_client = ctx.guild.voice_client

    if voice_client is None:
        await ctx.send("봇이 음성 채널에 연결되어 있지 않습니다.")
        return

    embed = disnake.Embed(color=0x00ff00)
    if voice_client.is_playing() or not voice_client.is_paused():
        embed.description = "음악이 이미 재생 중이거나 재생할 음악이 존재하지 않습니다."
        embed.color = 0xff0000
    else:
        voice_client.resume()
        embed.description = "음악을 재개했습니다."

    await ctx.send(embed=embed)

# 플레이리스트 생성 제한 설정
MAX_PLAYLISTS = {
    0 : 5,
    1 : 20,
    2 : 30,
    3 : 50,
    4 : 80,
    5 : 100
}

@bot.slash_command(name='플레이리스트', description='플레이리스트를 확인합니다.')
async def view_playlist(ctx, playlist_name: str):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "플레이리스트", f"{playlist_name}")
    db_path = os.path.join('system_database', 'music.db')
    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.execute('SELECT song FROM playlists WHERE user_id = ? AND playlist_name = ?',
                                     (ctx.author.id, playlist_name))
        songs = await cursor.fetchall()
        
        embed = disnake.Embed(title=f"{playlist_name} 플레이리스트", color=0x00FF00)  # 초록색 임베드

        if songs:
            song_list = "\n".join([song[0] for song in songs])
            embed.add_field(name="곡 목록", value=song_list, inline=False)
        else:
            embed.add_field(name="정보", value=f"{playlist_name} 플레이리스트가 비어 있습니다.", inline=False)

        await ctx.send(embed=embed)

@bot.slash_command(name='플레이리스트_추가', description='플레이리스트에 음악을 추가합니다.')
async def add_to_playlist(ctx, playlist_name: str, song: str):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "플레이리스트_추가", f"{playlist_name}")
    db_path = os.path.join('system_database', 'music.db')
    async with aiosqlite.connect(db_path) as economy_aiodb:
        db_path = os.path.join('system_database', 'membership.db')
        async with aiosqlite.connect(db_path) as membership_db:
            # 사용자 클래스 확인
            async with membership_db.execute('SELECT class FROM user WHERE id = ?', (ctx.author.id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    user_class = row[0]
                else:
                    await ctx.send("사용자 정보를 찾을 수 없습니다.")
                    return

            # 최대 플레이리스트 수 확인
            async with economy_aiodb.execute('SELECT COUNT(*) FROM playlists WHERE user_id = ?', (ctx.author.id,)) as cursor:
                count = await cursor.fetchone()
                current_count = count[0]

            if current_count >= MAX_PLAYLISTS.get(user_class, 0):
                embed = disnake.Embed(color=0xFF0000)
                if user_class == 0:
                    user_class_text = "비회원"
                elif user_class == 1:
                    user_class_text = "브론즈_회원"
                elif user_class == 2:
                    user_class_text = "실버_회원"
                elif user_class == 3:
                    user_class_text = "다이아_회원"
                elif user_class == 4:
                    user_class_text = "레전드_회원"
                elif user_class == 5:
                    user_class_text = "개발자"
                else:
                    print("플레이리스트 오류")
                    return
                max_playlists = MAX_PLAYLISTS.get(user_class)
                embed.add_field(name="오류", value=f"{user_class_text}는 최대 {max_playlists}개의 플레이리스트를 생성할 수 있습니다.", inline=False)
                await ctx.send(embed=embed)
                return

            # 음악 추가
            try:
                async with economy_aiodb.execute('INSERT INTO playlists (user_id, playlist_name, song) VALUES (?, ?, ?)',
                                                  (ctx.author.id, playlist_name, song)):
                    await economy_aiodb.commit()
                embed = disnake.Embed(title="추가 완료", color=0x00FF00)
                embed.add_field(name="플레이리스트", value=f"{playlist_name} 플레이리스트에 {song}이(가) 추가되었습니다.", inline=False)
                await ctx.send(embed=embed)
            except aiosqlite.IntegrityError:
                embed = disnake.Embed(title="오류", color=0xFF0000)
                embed.add_field(name="오류", value=f"{playlist_name} 플레이리스트에 이미 {song}이(가) 존재합니다.", inline=False)
                await ctx.send(embed=embed)

@bot.slash_command(name='플레이리스트_삭제', description='플레이리스트에서 음악을 삭제합니다.')
async def remove_from_playlist(ctx, playlist_name: str, song: str):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "플레이리스트_삭제", f"{playlist_name}, {song}")
    db_path = os.path.join('system_database', 'music.db')
    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.execute('DELETE FROM playlists WHERE user_id = ? AND playlist_name = ? AND song = ?',
                                     (ctx.author.id, playlist_name, song))
        await conn.commit()
        
        embed = disnake.Embed(title="삭제 결과", color=0x00FF00)

        if cursor.rowcount > 0:
            embed.add_field(name="성공", value=f"{playlist_name} 플레이리스트에서 {song}이(가) 삭제되었습니다.", inline=False)
        else:
            embed.add_field(name="정보", value=f"{playlist_name} 플레이리스트에 {song}이(가) 없습니다.", inline=False)

        await ctx.send(embed=embed)

@bot.slash_command(name='통계', description='봇의 통계를 확인합니다.')
async def statistics(ctx):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "통계", None)

    db_path = os.path.join('system_database', 'log.db')
    async with aiosqlite.connect(db_path) as conn:
        async with conn.cursor() as cursor:
            # 오늘 날짜의 명령어 사용 수 조회
            today = datetime.now().strftime('%Y-%m-%d')
            await cursor.execute("SELECT COUNT(*) FROM command WHERE DATE(time) = ?", (today,))
            command_count_today = await cursor.fetchone()
            command_count_today = command_count_today[0] if command_count_today else 0

            # 오늘 날짜의 많이 사용된 명령어 5개 조회
            await cursor.execute("SELECT command, COUNT(*) as count FROM command WHERE DATE(time) = ? GROUP BY command ORDER BY count DESC LIMIT 5", (today,))
            top_commands = await cursor.fetchall()

    # 새로운 서버 수와 나간 서버 수 조회
    db_path = os.path.join('system_database', 'system.db')
    async with aiosqlite.connect(db_path) as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT new_server FROM info")
            new_servers = await cursor.fetchone()
            new_servers_count = new_servers[0] if new_servers else 0

            await cursor.execute("SELECT lose_server FROM info")
            left_servers = await cursor.fetchone()
            left_servers_count = left_servers[0] if left_servers else 0

    total_members = 0  # 총 유저 수 초기화

    # 봇이 참여하고 있는 모든 서버를 반복
    for guild in bot.guilds:
        total_members += guild.member_count  # 각 서버의 멤버 수를 누적
    
    embed = disnake.Embed(title="봇 통계", color=0x00ff00)
    embed.add_field(name="서버 통계", value=f'''현재 서버 수 : {len(bot.guilds)}개\n오늘 추가된 서버 : {new_servers_count}개\n오늘 삭제된 서버 : {left_servers_count}개''', inline=False)
    embed.add_field(name="기타 통계", value=f'''현재 유저 수 : {total_members}명\n현재 채널 수 : {len([channel for channel in bot.get_all_channels()])}개''', inline=False)
    embed.add_field(name="명령어 통계", value=f"오늘 사용된 명령어 수 : {command_count_today}회", inline=False)

    if top_commands:
        top_commands_str = "\n".join([f"{command}: {count}회" for command, count in top_commands])
        embed.add_field(name="", value=f"오늘 많이 사용된 명령어 TOP 5\n{top_commands_str}", inline=False)
    else:
        embed.add_field(name="", value="오늘 많이 사용된 명령어 TOP 5\n데이터 없음", inline=False)

    await ctx.send(embed=embed)

class verify_Modal_Captcha(disnake.ui.Modal):
    def __init__(self):
        global verify_random
        verify_random = random.randint(100000, 999999)
        components = [
            disnake.ui.TextInput(
                label=f"{verify_random}을 입력해주세요",
                placeholder="인증번호를 입력해주세요",
                custom_id="text1",
                style=TextInputStyle.short,
                max_length=6
            )
        ]
        super().__init__(title="인증번호", components=components)

    async def callback(self, ctx: disnake.ModalInteraction):
        global key, verify_random

        key = ctx.text_values['text1']

        if str(verify_random) == key:
            global global_role_captcha
            role = global_role_captcha
            await ctx.author.add_roles(role)
            embed = disnake.Embed(color=embedsuccess)
            embed.add_field(name="인증 완료", value=f"{ctx.author.mention} 인증이 완료되었습니다.")
            await ctx.send(embed=embed)
        else:
            embed = disnake.Embed(color=embederrorcolor)
            embed.add_field(name="❌ 오류", value="인증번호가 일치하지 않습니다.")
            await ctx.send(embed=embed, ephemeral=True)

@bot.slash_command(name="인증", description="번호를 눌러 인증합니다.")
async def calculate_verify(ctx):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "인증", None)
    db_path = os.path.join(os.getcwd(), "database", f"{ctx.guild.id}.db")
    if not os.path.exists(db_path):
        await database_create(ctx)
    else:
        aiodb = await aiosqlite.connect(db_path)
        aiocursor = await aiodb.execute("SELECT 인증역할, 인증채널 FROM 설정")
        role_id, channel_id = await aiocursor.fetchone()
        await aiocursor.close()
        await aiodb.close()
    if role_id:
        role_id = role_id
        global global_role_captcha
        role = ctx.guild.get_role(role_id)
        global_role_captcha = role
        if role:
            # 인증 역할이 이미 부여된 경우
            if role in ctx.author.roles:
                embed = disnake.Embed(color=embederrorcolor)
                embed.add_field(name="❌ 오류", value="이미 인증된 상태입니다.")
                await ctx.send(embed=embed, ephemeral=True)
                return
            if channel_id:
                channel_id = channel_id
                channel = ctx.guild.get_channel(channel_id)
                if channel and channel == ctx.channel:
                    pass
                else:
                    embed = disnake.Embed(color=embederrorcolor)
                    embed.add_field(name="❌ 오류", value="인증 채널에서만 인증 명령어를 사용할 수 있습니다.")
                    await ctx.send(embed=embed, ephemeral=True)
                    return
            else:
                embed = disnake.Embed(color=embederrorcolor)
                embed.add_field(name="❌ 오류", value="인증채널이 설정되지 않은 서버입니다.\n서버 관리자에게 문의하세요.")
                await ctx.send(embed=embed, ephemeral=True)
                return
        else:
            embed = disnake.Embed(color=embederrorcolor)
            embed.add_field(name="❌ 오류", value="**인증역할**이 설정되지 않은 서버입니다.\n서버 관리자에게 문의하세요.")
            await ctx.send(embed=embed, ephemeral=True)
            return
    else:
        embed = disnake.Embed(color=embederrorcolor)
        embed.add_field(name="❌ 오류", value="**인증역할**이 설정되지 않은 서버입니다.\n서버 관리자에게 문의하세요.")
        await ctx.send(embed=embed, ephemeral=True)
        return
    
    await ctx.response.send_modal(modal=verify_Modal_Captcha())

def send_sms_verify(phone_number):
    global global_verify_code_sms
    verify_code = random.randint(100000, 999999)
    global_verify_code_sms = verify_code

    text = f"인증번호: {verify_code}"
                        
    # 카카오 알림톡 메시지 전송
    message = {
        'messages': [{
            'to': phone_number,
            'from': sec.send_number,
            'text': text,
            'kakaoOptions': {
                'pfId': sec.kakao_pfid,
                'templateId': sec.kakao_templateid,
                'variables': {
                    '#{verify_code}': verify_code,
                    '#{activity}': "스톤봇 인증"
                }
            }
        }]
    }
    if coolsms_kakao.send_kakao(message):  # 카카오 알림톡 전송
        print(f'''인증번호({verify_code})가 "{phone_number}"로 전송되었습니다.''')

class verify_Modal_SMS(disnake.ui.Modal):
    def __init__(self):
        components = [
            disnake.ui.TextInput(
                label="인증번호",
                placeholder="인증번호를 입력해주세요.",
                custom_id="text1",
                style=TextInputStyle.short,
                max_length=6
            )
        ]
        super().__init__(title="인증번호", components=components)
        global global_phone_number_sms
        phone_number = global_phone_number_sms
        send_sms_verify(phone_number)

    async def callback(self, ctx: disnake.ModalInteraction):
        global key
        global global_verify_code_sms

        verify_code = global_verify_code_sms
        key = ctx.text_values['text1']

        if str(verify_code) == key:
            global global_role_sms
            role = global_role_sms
            await ctx.author.add_roles(role)
            embed = disnake.Embed(color=embedsuccess)
            embed.add_field(name="문자 인증", value=f"{ctx.author.mention} 문자 인증이 완료되었습니다.")
            await ctx.send(embed=embed)
        else:
            embed = disnake.Embed(color=embederrorcolor)
            embed.add_field(name="❌ 오류", value="인증번호가 일치하지 않습니다.")
            await ctx.send(embed=embed, ephemeral=True)

@bot.slash_command(name='인증_문자', description='문자를 이용해서 인증을 합니다.')
async def sms_verify(ctx, phone_number: str):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "인증_문자", f"{phone_number}")
    db_path = os.path.join(os.getcwd(), "database", f"{ctx.guild.id}.db")
        
    if not os.path.exists(db_path):
        await database_create(ctx)
    else:
        try:
            aiodb = await aiosqlite.connect(db_path)
            aiocursor = await aiodb.execute("SELECT 인증역할, 인증채널 FROM 설정")
            role_id, channel_id = await aiocursor.fetchone()
            await aiocursor.close()
            await aiodb.close()
        except Exception as e:
            embed = disnake.Embed(color=embederrorcolor)
            embed.add_field(name="❌ 오류", value="데이터베이스 오류가 발생했습니다. 관리자에게 문의하세요.")
            await ctx.send(embed=embed, ephemeral=True)
            return
    if role_id:
        global global_role_sms
        role = ctx.guild.get_role(role_id)
        global_role_sms = role
        if role:
            # 인증 역할이 이미 부여된 경우
            if role in ctx.author.roles:
                embed = disnake.Embed(color=embederrorcolor)
                embed.add_field(name="❌ 오류", value="이미 인증된 상태입니다.")
                await ctx.send(embed=embed, ephemeral=True)
                return
                
            if channel_id:
                channel = ctx.guild.get_channel(channel_id)
                if channel and channel == ctx.channel:
                    pass
                else:
                    embed = disnake.Embed(color=embederrorcolor)
                    embed.add_field(name="❌ 오류", value="인증 채널에서만 인증 명령어를 사용할 수 있습니다.")
                    await ctx.send(embed=embed, ephemeral=True)
                    return
            else:
                embed = disnake.Embed(color=embederrorcolor)
                embed.add_field(name="❌ 오류", value="인증채널이 설정되지 않은 서버입니다.\n서버 관리자에게 문의하세요.")
                await ctx.send(embed=embed, ephemeral=True)
                return
        else:
            embed = disnake.Embed(color=embederrorcolor)
            embed.add_field(name="❌ 오류", value="**인증역할**이 설정되지 않은 서버입니다.\n서버 관리자에게 문의하세요.")
            await ctx.send(embed=embed, ephemeral=True)
            return
    else:
        embed = disnake.Embed(color=embederrorcolor)
        embed.add_field(name="❌ 오류", value="**인증역할**이 설정되지 않은 서버입니다.\n서버 관리자에게 문의하세요.")
        await ctx.send(embed=embed, ephemeral=True)
        return
    
    global global_phone_number_sms
    global_phone_number_sms = phone_number
    await ctx.response.send_modal(modal=verify_Modal_SMS())

def send_email_verify(email):
    # 인증 코드 생성 및 이메일 전송
    global global_verify_code_email
    verify_code = random.randint(100000, 999999)
    global_verify_code_email = verify_code
    send_email(email, verify_code)
    print(f'''인증번호({verify_code})가 "{email}"로 전송되었습니다.''')

class verify_Modal_EMAIL(disnake.ui.Modal):
    def __init__(self):
        components = [
            disnake.ui.TextInput(
                label="인증번호",
                placeholder="인증번호를 입력해주세요.",
                custom_id="text1",
                style=TextInputStyle.short,
                max_length=6
            )
        ]
        super().__init__(title="인증번호", components=components)
        global global_email
        email = global_email
        send_email_verify(email)

    async def callback(self, ctx: disnake.ModalInteraction):
        global key
        global global_verify_code_email

        verify_code = global_verify_code_email
        key = ctx.text_values['text1']

        if str(verify_code) == key:
            global global_role_email
            role = global_role_email
            await ctx.author.add_roles(role)
            embed = disnake.Embed(color=embedsuccess)
            embed.add_field(name="이메일 인증", value=f"{ctx.author.mention} 메일 인증이 완료되었습니다.")
            await ctx.send(embed=embed)
        else:
            embed = disnake.Embed(color=embederrorcolor)
            embed.add_field(name="❌ 오류", value="인증번호가 일치하지 않습니다.")
            await ctx.send(embed=embed, ephemeral=True)

@bot.slash_command(name='인증_이메일', description='이메일을 이용해서 인증을 합니다.')
async def email_verify(ctx, email: str):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "인증_이메일", f"{email}")
    db_path = os.path.join(os.getcwd(), "database", f"{ctx.guild.id}.db")

    # 데이터베이스가 존재하지 않는 경우
    if not os.path.exists(db_path):
        await database_create(ctx)

    # 데이터베이스 연결 및 설정 가져오기
    aiodb = await aiosqlite.connect(db_path)
    aiocursor = await aiodb.execute("SELECT 인증역할, 인증채널 FROM 설정")
    row = await aiocursor.fetchone()
    await aiocursor.close()
    await aiodb.close()

    role_id, channel_id = row if row else (None, None)

    if role_id:
        role = ctx.guild.get_role(role_id)
        global global_role_email
        global_role_email = role

        if role:
            # 인증 역할이 이미 부여된 경우
            if role in ctx.author.roles:
                embed = disnake.Embed(color=embederrorcolor)
                embed.add_field(name="❌ 오류", value="이미 인증된 상태입니다.")
                await ctx.send(embed=embed, ephemeral=True)
                return
            
            if channel_id:
                channel = ctx.guild.get_channel(channel_id)
                if channel and channel == ctx.channel:
                    pass
                else:
                    embed = disnake.Embed(color=embederrorcolor)
                    embed.add_field(name="❌ 오류", value="인증 채널에서만 인증 명령어를 사용할 수 있습니다.")
                    await ctx.send(embed=embed, ephemeral=True)
                    return
            else:
                embed = disnake.Embed(color=embederrorcolor)
                embed.add_field(name="❌ 오류", value="인증채널이 설정되지 않은 서버입니다.\n서버 관리자에게 문의하세요.")
                await ctx.send(embed=embed, ephemeral=True)
                return
        else:
            embed = disnake.Embed(color=embederrorcolor)
            embed.add_field(name="❌ 오류", value="**인증역할**이 설정되지 않은 서버입니다.\n서버 관리자에게 문의하세요.")
            await ctx.send(embed=embed, ephemeral=True)
            return
    else:
        embed = disnake.Embed(color=embederrorcolor)
        embed.add_field(name="❌ 오류", value="**인증역할**이 설정되지 않은 서버입니다.\n서버 관리자에게 문의하세요.")
        await ctx.send(embed=embed, ephemeral=True)
        return
    
    global global_email
    global_email = email
    await ctx.response.send_modal(modal=verify_Modal_EMAIL())

@bot.slash_command(name="지갑", description="자신이나 다른 유저의 지갑을 조회합니다.")
async def wallet(ctx, member_id: int = None):
    if not await check_permissions(ctx):
        return

    if not await member_status(ctx):
        return

    await command_use_log(ctx, "지갑", f"{member_id}")
    
    user = ctx.author if member_id is None else await bot.fetch_user(member_id)
    if user is None:
        await ctx.followup.send("유효하지 않은 유저 ID입니다.", ephemeral=True)
        return

    user_data = await fetch_user_data(user.id)
    if user_data is None:
        await ctx.followup.send(f"{user.mention}, 가입되지 않은 유저입니다.", ephemeral=True)
        return

    tos_data = await fetch_tos_status(user.id)
    tos = tos_data[0] if tos_data else None

    if tos is None:
        await ctx.followup.send(f"{user.mention}, TOS 정보가 없습니다.", ephemeral=True)
        return
    elif tos == 1:
        await ctx.followup.send(f"{user.mention}, 이용이 제한된 유저 입니다.", ephemeral=True)
        return

    money, level, exp, lose_money = user_data[1], user_data[3], user_data[4], user_data[5]
        
    embed = disnake.Embed(title=f"{user.name}님의 지갑 💰", color=0x00ff00)
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name="아이디", value=f"{user.id}", inline=False)
    embed.add_field(name="레벨", value=f"{level:,}({exp:,}) Level", inline=False)
    embed.add_field(name="잔액", value=f"{money:,}원", inline=False)
    embed.add_field(name="잃은돈", value=f"{lose_money:,}원", inline=False)

    await ctx.followup.send(embed=embed, ephemeral=True)

@bot.slash_command(name="돈순위", description="가장 돈이 많은 유저의 리스트를 보여줍니다.")
async def money_ranking(ctx):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return
    
    await command_use_log(ctx, "돈순위", None)
    limit = 10

    excluded_ids = [id for id in developer] if isinstance(developer, list) else [developer]
    richest_users = await fetch_money_ranking(excluded_ids, limit)

    if not richest_users:
        embed = disnake.Embed(color=embederrorcolor, description="등록된 유저가 없습니다.")
        await ctx.send(embed=embed, ephemeral=True)
    else:
        embed = disnake.Embed(title="돈순위", color=0x00ff00)
        for rank, (user_id, money) in enumerate(richest_users, start=1):
            embed.add_field(name=f"{rank}위", value=f"<@{user_id}> | {money:,}원", inline=False)

        await ctx.send(embed=embed)

class EarnButton(disnake.ui.Button):
    def __init__(self):
        super().__init__(label="돈 받기", style=ButtonStyle.primary)

    async def callback(self, interaction: disnake.MessageInteraction):
        random_add_money = random.randrange(30000, 100001)
        random_add_money = int(round(random_add_money, -3))

        embed = disnake.Embed(color=embedsuccess)
        await addmoney(interaction.author.id, random_add_money)
        await add_exp(interaction.author.id, round(random_add_money / 300))
        embed.add_field(name="돈 지급", value=f"{interaction.author.mention}, {random_add_money:,}원이 지급되었습니다.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

        # 버튼 비활성화
        self.disabled = True
        view = disnake.ui.View()
        view.add_item(self)
        await interaction.message.edit(view=view)

        # 로그 기록
        await economy_log(interaction, "일하기", "+", random_add_money)

@bot.slash_command(name="일하기", description="버튼을 눌러 30,000 ~ 100,000원을 얻습니다.")
async def earn_money(ctx):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "일하기", None)
    if not await member_status(ctx):
        return
    
    cooldowns = load_cooldowns()
    last_execution_time = cooldowns.get(str(ctx.author.id), 0)
    current_time = time.time()
    cooldown_time = 180
    
    if current_time - last_execution_time < cooldown_time:
        remaining_time = round(cooldown_time - (current_time - last_execution_time))
        embed = disnake.Embed(color=embederrorcolor)
        embed.add_field(name="쿨타임", value=f"{ctx.author.mention}, {remaining_time}초 후에 다시 시도해주세요.")
        await ctx.send(embed=embed)
        await economy_log(ctx, "일하기", "0", 0)
    else:
        cooldowns[str(ctx.author.id)] = current_time
        save_cooldowns(cooldowns)
        
        # 버튼을 포함한 응답
        button = EarnButton()
        view = disnake.ui.View()
        view.add_item(button)
        embed = disnake.Embed(title="돈 받기!", description="아래 버튼을 눌러 돈을 받으세요.")
        await ctx.send(embed=embed, view=view)

@bot.slash_command(name="출석체크", description="봇 투표 여부를 확인하고 돈을 지급합니다.")
async def recommend_reward(ctx):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "출석체크", None)
    if not await member_status(ctx):
        return

    # 쿨타임 확인
    cooldowns = load_cooldowns()
    last_execution_time = cooldowns.get(f"recommend_reward_{ctx.author.id}", 0)
    current_time = time.time()
    cooldown_time = 12 * 60 * 60  # 12시간

    if current_time - last_execution_time < cooldown_time:
        remaining_time = round((cooldown_time - (current_time - last_execution_time)) / 3600, 2)
        embed = disnake.Embed(color=embederrorcolor)
        embed.add_field(name="쿨타임", value=f"{ctx.author.mention}, {remaining_time}시간 후에 다시 시도해주세요.")
        await ctx.send(embed=embed)
        return

    # 한국디스코드리스트 API를 이용하여 추천 여부 확인
    api_url = f"https://koreanbots.dev/api/v2/bots/{bot.user.id}/vote?userID={ctx.author.id}"
    headers = {
        "Authorization": f"{sec.koreanbots_api_key}",
        "Content-Type": "application/json"
    }
    
    response = requests.get(api_url, headers=headers)
    if response.status_code != 200:
        await ctx.send("투표 정보를 가져오는 데 실패했습니다.")
        return

    data = response.json().get("data", {})
    print(data)
    if data.get("voted", False):
        reward_amount = 200000  # 보상 금액 설정
        await addmoney(ctx.author.id, reward_amount)
        await economy_log(ctx, "출석체크", "+", reward_amount)
        embed = disnake.Embed(color=embedsuccess)
        embed.add_field(name="출석체크", value=f"{ctx.author.mention}, {reward_amount:,}원이 지급되었습니다.")
        await ctx.send(embed=embed)  # 메시지 전송

        # 쿨타임 설정
        cooldowns[f"recommend_reward_{ctx.author.id}"] = current_time
        save_cooldowns(cooldowns)
    else:
        embed = disnake.Embed(color=embederrorcolor)
        embed.add_field(name="❌ 오류", value="아직 투표를 하지 않으셨습니다.")
        label = "투표하기"
        url = f"https://koreanbots.dev/bots/{bot.user.id}/vote"
        button = disnake.ui.Button(label=label, style=disnake.ButtonStyle.url, url=url)
        view = disnake.ui.View()
        view.add_item(button)
        await ctx.send(embed=embed, view=view)

@bot.slash_command(name="송금", description="다른사람에게 돈을 송금합니다.")
async def send_money(ctx, get_user: disnake.Member = commands.Param(name="받는사람"), money: int = commands.Param(name="금액")):
    if not await limit(ctx):
        return
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "송금", f"{get_user}, {money}")
    if not await member_status(ctx):
        return
    db_path = os.path.join('system_database', 'economy.db')
    economy_aiodb = await aiosqlite.connect(db_path)


    aiocursor = await economy_aiodb.execute("SELECT tos FROM user WHERE id=?", (get_user.id,))
    dbdata = await aiocursor.fetchone()
    await aiocursor.close()
    if dbdata is not None:
        if int(dbdata[0]) == 1:
            embed=disnake.Embed(color=embederrorcolor)
            embed.add_field(name="❌ 오류", value="받는사람이 이용제한상태이므로 송금할수없습니다.")
            await ctx.send(embed=embed, ephemeral=True)
            return
        else:
            pass
    else:
        embed=disnake.Embed(color=embederrorcolor)
        embed.add_field(name="❌ 오류", value="받는사람이 미가입상태이므로 송금할수없습니다.")
        await ctx.send(embed=embed, ephemeral=True)
        return

    if money < 1:
        embed = disnake.Embed(color=embederrorcolor)
        embed.add_field(name="❌ 오류", value="송금 금액은 1원이상부터 가능합니다.")
        await ctx.send(embed=embed, ephemeral=True)
        return

    send_user = ctx.author
    send_user_money = await getmoney(send_user.id)
    if send_user_money < money:
        return await ctx.send(f"{send_user.mention}님의 잔액이 부족하여 송금할 수 없습니다.")
    await removemoney(send_user.id, money) 
    await economy_log(send_user, "송금", "-", money)
    await addmoney(get_user.id, money)
    await economy_log(ctx, "송금", "+", money)
    embed = disnake.Embed(title="송금 완료", color=embedsuccess)
    embed.add_field(name="송금인", value=f"{send_user.mention}")
    embed.add_field(name="받는사람", value=f"{get_user.mention}")
    embed.add_field(name="송금 금액", value=f"{money:,}")
    await ctx.send(embed=embed)

@bot.slash_command(name="가위바위보", description="봇과 가위바위보 도박을 합니다. (확률 33.3%, 2배, 실패시 -1배)")
async def rock_paper_scissors_betting(ctx, user_choice: str = commands.Param(name="선택", choices=["가위", "바위", "보"]), bet_amount: int = commands.Param(name="금액")):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "가위바위보", f"{user_choice}, {bet_amount}")
    if not await member_status(ctx):
        return
    user = ctx.author
    current_money = await getmoney(user.id)  # 현재 보유 금액 조회

    # 배팅 금액이 음수이거나 0일 경우 오류 메시지 전송
    if bet_amount <= 0:
        embed = disnake.Embed(color=embederrorcolor)
        embed.add_field(name="❌ 오류", value="배팅 금액은 1원 이상이어야 합니다.")
        await ctx.send(embed=embed, ephemeral=True)
        return
    
    if bet_amount > current_money:
        embed = disnake.Embed(color=embederrorcolor)
        embed.add_field(name="❌ 오류", value="가지고 있는 돈보다 배팅 금액이 많습니다.")
        await ctx.send(embed=embed, ephemeral=True)
        return

    bot_choice = random.choice(["가위", "바위", "보"])

    # 결과 판단
    result_embed = disnake.Embed(title="게임 결과", color=0x00FF00)  # 초록색 임베드
    result_embed.add_field(name="당신의 선택", value=user_choice, inline=True)
    result_embed.add_field(name="봇의 선택", value=bot_choice, inline=True)

    if user_choice == bot_choice:
        result = "비겼습니다!"
        result_embed.add_field(name="결과", value=result, inline=False)
        result_embed.add_field(name="돈은 그대로 유지됩니다.", value=f"현재 금액: {current_money:,}원", inline=False)
        await economy_log(ctx, "가위바위보", "0", 0)
    elif (user_choice == "가위" and bot_choice == "보") or \
         (user_choice == "바위" and bot_choice == "가위") or \
         (user_choice == "보" and bot_choice == "바위"):
        result = "당신이 이겼습니다!"
        await addmoney(user.id, bet_amount)  # 돈을 추가
        await add_exp(user.id, round(bet_amount / 600))
        result_embed.add_field(name="결과", value=result, inline=False)
        result_embed.add_field(name="보상", value=f"{bet_amount * 2:,}원을 얻었습니다.", inline=False)
        await economy_log(ctx, "가위바위보", "+", bet_amount * 2)
    else:
        result = "당신이 졌습니다!"
        await removemoney(user.id, bet_amount)  # 돈을 제거
        await add_lose_money(user.id, bet_amount)
        await add_exp(user.id, round(bet_amount / 1200))
        result_embed.add_field(name="결과", value=result, inline=False)
        result_embed.add_field(name="패배", value=f"{bet_amount:,}원을 잃었습니다.", inline=False)
        await economy_log(ctx, "가위바위보", "-", bet_amount)

    # 결과 메시지 전송
    await ctx.send(embed=result_embed)

betting_method_choices = ["도박 (확률 30%, 2배, 실패시 -1배)", "도박2 (확률 50%, 1.5배, 실패시 -0.75배)"]
@bot.slash_command(name="도박", description="보유금액으로 도박을 합니다.")
async def betting(ctx, money: int = commands.Param(name="금액"), betting_method: str = commands.Param(name="배팅종류", choices=betting_method_choices)):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "도박", f"{money}, {betting_method}")
    if not await member_status(ctx):
        return
    user = ctx.author
    current_money = await getmoney(user.id)  # 현재 보유 금액 조회

    if money <= 0:
        embed = disnake.Embed(color=embederrorcolor)
        embed.add_field(name="❌ 오류", value="배팅 금액은 1원 이상이어야 합니다.")
        await ctx.send(embed=embed, ephemeral=True)
        return

    if money > current_money:
        embed = disnake.Embed(color=embederrorcolor)
        embed.add_field(name="❌ 오류", value="가지고 있는 돈보다 배팅 금액이 많습니다.")
        await ctx.send(embed=embed, ephemeral=True)
        return

    if betting_method == "도박 (확률 30%, 2배, 실패시 -1배)":
        await handle_bet(ctx, user, money, success_rate=30, win_multiplier=2, lose_multiplier=1, lose_exp_divisor=1200)
    elif betting_method == "도박2 (확률 50%, 1.5배, 실패시 -0.75배)":
        await handle_bet(ctx, user, money, success_rate=50, win_multiplier=0.5, lose_multiplier=0.75, lose_exp_divisor=1200)

@bot.slash_command(name="숫자도박", description="보유금액으로 도박을 합니다. (숫자맞추기 1~4, 확률 25%, 최대 3배, 실패시 -2배)")
async def betting_number(ctx, number: int = commands.Param(name="숫자"), money: int = commands.Param(name="금액")):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "숫자도박", f"{number}, {money}")
    if not await member_status(ctx):
        return
    user = ctx.author
    current_money = await getmoney(user.id)  # 현재 보유 금액 조회

    # 배팅 금액이 음수이거나 0일 경우 오류 메시지 전송
    if money <= 0:
        embed = disnake.Embed(color=embederrorcolor)
        embed.add_field(name="❌ 오류", value="배팅 금액은 1원 이상이어야 합니다.")
        await ctx.send(embed=embed, ephemeral=True)
        return

    if round(money * 2) > current_money:
        embed = disnake.Embed(color=embederrorcolor)
        embed.add_field(name="❌ 오류", value="가진금액보다 배팅금이 많습니다.")
        await ctx.send(embed=embed, ephemeral=True)
        return
    else:
        if number < 1 or number > 4:  # 1~4 범위 체크
            embed = disnake.Embed(color=embederrorcolor)
            embed.add_field(name="❌ 오류", value="1 ~ 4 중에서 선택해주세요.")
            await ctx.send(embed=embed, ephemeral=True)
            return

        random_number = random.randint(1, 5)  # 1~4 범위의 랜덤 숫자 생성
        if random_number == number:
            await addmoney(user.id, (money * 2))
            await add_exp(user.id, round((money * 2) / 600))
            embed = disnake.Embed(color=embedsuccess)
            money = money * 3
            await economy_log(ctx, "숫자도박", "+", money)
            embed.add_field(name="성공", value=f"{money:,}원을 얻었습니다.")
            await ctx.send(embed=embed)
        else:
            await removemoney(user.id, round(money * 2))
            await add_lose_money(user.id, round(money * 2))
            await add_exp(user.id, round((money * 2) / 1200))
            embed = disnake.Embed(color=embederrorcolor)
            money = round(money * 2)
            await economy_log(ctx, "숫자도박", "-", money)
            embed.add_field(name="실패", value=f"{money:,}원을 잃었습니다.")
            await ctx.send(embed=embed)

# 카드 점수 계산 함수
def get_card_value(card):
    shape_score = {
        'A': 1,
        'J': 0,
        'Q': 0,
        'K': 0,
        '2': 2,
        '3': 3,
        '4': 4,
        '5': 5,
        '6': 6,
        '7': 7,
        '8': 8,
        '9': 9,
        '10': 0
    }
    return shape_score.get(card, 0)

@bot.slash_command(name="도박_바카라", description="보유금액으로 도박을 합니다.")
async def betting_card(ctx, money: int = commands.Param(name="금액"), method: str = commands.Param(name="배팅", choices=["플레이어", "무승부", "뱅커"])):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return
    
    if not await member_status(ctx):
        return
    
    await command_use_log(ctx, "도박_바카라", f"{money}, {method}")
    if not ctx.response.is_done():
        await ctx.response.defer()
    
    user = ctx.author
    current_money = await getmoney(user.id)  # 현재 보유 금액 조회

    # 배팅 금액 검증
    if money <= 0:
        embed = disnake.Embed(color=embederrorcolor)
        embed.add_field(name="❌ 오류", value="배팅 금액은 1원 이상이어야 합니다.")
        await ctx.send(embed=embed, ephemeral=True)
        return

    if money > current_money:
        embed = disnake.Embed(color=embederrorcolor)
        embed.add_field(name="❌ 오류", value="가진 금액보다 배팅 금액이 많습니다.")
        await ctx.send(embed=embed, ephemeral=True)
        return

    # 카드 랜덤 생성 함수
    def random_card():
        return random.choice(['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K'])

    def random_shape():
        return random.choice(['♠️', '♣️', '♥️', '♦️'])

    # 카드와 모양 랜덤 생성
    mix_p = [random_card() for _ in range(2)]  # 플레이어는 처음 2장
    mix_b = [random_card() for _ in range(2)]  # 뱅커도 처음 2장
    shape_p = [random_shape() for _ in range(2)]
    shape_b = [random_shape() for _ in range(2)]

    # 점수 계산
    score_calculate_p = (get_card_value(mix_p[0]) + get_card_value(mix_p[1])) % 10
    score_calculate_b = (get_card_value(mix_b[0]) + get_card_value(mix_b[1])) % 10

    # 플레이어 추가 카드 규칙 적용
    if score_calculate_p <= 6:
        mix_p.append(random_card())  # 새 카드 추가
        shape_p.append(random_shape())
        score_calculate_p = (get_card_value(mix_p[0]) + get_card_value(mix_p[1]) + get_card_value(mix_p[2])) % 10

    # 뱅커의 추가 카드 규칙 적용
    if score_calculate_b <= 2 or (
        score_calculate_b == 3 and score_calculate_p != 8) or (
        score_calculate_b == 4 and score_calculate_p in range(2, 8)) or (
        score_calculate_b == 5 and score_calculate_p in range(4, 8)) or (
        score_calculate_b == 6 and score_calculate_p in [6, 7]):
        mix_b.append(random_card())  # 새 카드 추가
        shape_b.append(random_shape())
        score_calculate_b = (get_card_value(mix_b[0]) + get_card_value(mix_b[1]) + get_card_value(mix_b[2])) % 10

    # 승자 결정
    winner = "플레이어" if score_calculate_p > score_calculate_b else "뱅커" if score_calculate_p < score_calculate_b else "무승부"

    # 승리 데이터 업데이트
    db_path = os.path.join('system_database', 'log.db')

    try:
        conn = await aiosqlite.connect(db_path)  # db는 데이터베이스 파일의 경로입니다.
        await conn.execute('INSERT INTO winner (winner) VALUES (?)', (winner,))
        await conn.commit()
        await conn.close()
    except Exception as e:
        print(f"데이터베이스 업데이트 중 오류 발생: {e}")

    # 배팅 결과 처리
    embed = disnake.Embed(color=embedsuccess if winner == method else embederrorcolor)

    if winner == method:  # win
        if winner == "플레이어":
            win_money = money * 2
        elif winner == "뱅커":
            win_money = money * 1.95
        elif winner == "무승부":
            win_money = money * 8
        else:
            print("Error")
        
        win_money = round(win_money)
        await addmoney(user.id, win_money - money)
        await add_exp(user.id, round(win_money / 600))
        embed.add_field(name="성공", value=f"{win_money:,}원을 얻었습니다.", inline=False)
        await economy_log(ctx, "도박_바카라", "+", win_money)
    else:  # lose
        if winner == "무승부":
            embed.add_field(name="무승부", value="배팅 금액이 유지됩니다.", inline=False)
        else:
            await removemoney(user.id, money)
            await add_lose_money(user.id, money)
            await add_exp(user.id, round(money / 1200))
            embed.add_field(name="실패", value=f"{money:,}원을 잃었습니다.", inline=False)
            await economy_log(ctx, "도박_바카라", "-", money)

    # 카드 결과 출력
    embed.add_field(name="결과", value=f"배팅 : {method}\n배팅금액 : {money:,}원\n승리 : {winner}!", inline=False)

    # 추가 카드 결과 표시
    card_results = f"플레이어 : {', '.join([f'{mix_p[i]}{shape_p[i]}' for i in range(len(mix_p))])}, {score_calculate_p}\n"
    card_results += f"뱅커 : {', '.join([f'{mix_b[i]}{shape_b[i]}' for i in range(len(mix_b))])}, {score_calculate_b}"
    embed.add_field(name="카드 결과", value=card_results)
    await ctx.send(embed=embed)

@bot.slash_command(name="바카라_분석", description="분석 데이터를 그래프로 보여줍니다.")
async def baccarat(ctx):
    if not await tos(ctx):
        return
    db_path = os.path.join('system_database', 'log.db')

    async with aiosqlite.connect(db_path) as conn:
        async with conn.cursor() as cursor:
            query = "SELECT winner, COUNT(*) as count FROM winner GROUP BY winner"
            await cursor.execute(query)

            # 결과 가져오기
            results = await cursor.fetchall()

    # 데이터 분리
    commands = [row[0] for row in results]
    counts = [row[1] for row in results]
    total_counts = sum(counts)

    # 퍼센트 계산
    percentages = [(count / total_counts) * 100 for count in counts]

    # 그래프 그리기
    plt.figure(figsize=(12, 6))
    bars = plt.bar(commands, counts, color='skyblue')
    plt.xlabel('결과')
    plt.ylabel('횟수')
    plt.title('분석')
    plt.xticks(rotation=45)
    plt.tight_layout()

    # 바 위에 횟수와 퍼센트 표시
    for bar, percentage in zip(bars, percentages):
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, yval, f'{int(yval)}\n({percentage:.2f}%)', ha='center', va='bottom')

    # 그래프 이미지 저장
    image_path = 'baccarat_analysis.png'
    plt.savefig(image_path)
    plt.close()  # 그래프 닫기

    # 임베드 메시지 생성
    embed = disnake.Embed(title="바카라 분석 결과", color=0x00ff00)
    embed.set_image(url="attachment://baccarat_analysis.png")  # 첨부된 이미지 URL 설정

    # Discord에 이미지와 함께 임베드 메시지 전송
    await ctx.send(embed=embed, file=disnake.File(image_path, filename='baccarat_analysis.png'))

    # 데이터베이스 연결 종료
    conn.close()

@bot.slash_command(name="로또구매", description="로또를 구매합니다.")
async def purchase_lottery(ctx, auto: str = commands.Param(name="종류", choices=["자동", "수동"], default="자동"),
                           count: int = commands.Param(name="개수", default=1),
                           numbers: str = commands.Param(name="번호", default=None)):
    if not await tos(ctx):
        return
    user_id = ctx.author.id

    # 최대 구매 개수 제한
    if count > 100:
        await ctx.send("최대 100개까지 로또를 구매할 수 있습니다.")
        return

    # 로또 음수제한
    if count < 1:
        await ctx.send("로또는 1개 이상만 구매할 수 있습니다.")
        return

    # 사용자의 잔액을 가져옵니다.
    get_money = await getmoney(user_id)
    
    total_cost = count * 10000  # 총 비용 계산
    if get_money < total_cost:
        await ctx.send("잔액이 부족하여 로또를 구매할 수 없습니다.")
        return

    # 잔액 차감
    await removemoney(user_id, total_cost)
    await economy_log(ctx, "로또", "-", total_cost)

    await ctx.response.defer()  # 응답을 미리 지연

    # 데이터베이스 파일 경로
    db_path = os.path.join('system_database', 'lotto.db')
    purchased_numbers = []  # 구매한 로또 번호를 저장할 리스트
    # 텍스트 파일 경로
    text_file_path = os.path.join('system_database', 'purchased_lotteries.txt')

    if auto == "자동":
        async with aiosqlite.connect(db_path) as db:
            for _ in range(count):
                lottery_numbers = random.sample(range(1, 46), 6)
                lottery_numbers_str = ','.join(map(str, sorted(lottery_numbers)))
                await db.execute('INSERT OR IGNORE INTO lottery (user_id, numbers) VALUES (?, ?)', (user_id, lottery_numbers_str))
                purchased_numbers.append(lottery_numbers_str)
            await db.commit()
        await ctx.send(f"{count}개의 로또가 자동으로 구매되었습니다.")
    else:
        if numbers:
            try:
                manual_numbers = list(map(int, numbers.split(',')))
                if len(manual_numbers) != 6 or len(set(manual_numbers)) != 6 or any(num < 1 or num > 45 for num in manual_numbers):
                    raise ValueError
                lottery_numbers_str = ','.join(map(str, sorted(manual_numbers)))
                async with aiosqlite.connect(db_path) as db:
                    await db.execute('INSERT OR IGNORE INTO lottery (user_id, numbers) VALUES (?, ?)', (user_id, lottery_numbers_str))
                    await db.commit()
                purchased_numbers.append(lottery_numbers_str)
                await ctx.send(f"로또 번호 {manual_numbers}이(가) 구매되었습니다.")
            except ValueError:
                await ctx.send("잘못된 번호 형식입니다. 1부터 45 사이의 중복되지 않는 6개 숫자를 입력하세요.")
        else:
            await ctx.send("수동 구매를 원하시면 로또 번호를 입력해주세요.")

    # 구매한 로또 번호를 DM으로 임베드 형태로 전송
    if purchased_numbers:
        embed = disnake.Embed(title="구매한 로또 번호", description="\n".join(purchased_numbers), color=0x00ff00)
        embed.set_footer(text="행운을 빕니다!")
        await ctx.author.send(embed=embed)

    # 구매한 복권 번호를 텍스트 파일에 저장
    if purchased_numbers:
        with open(text_file_path, 'a') as file:
            for numbers in purchased_numbers:
                file.write(f"{user_id}: {numbers}\n")

@bot.slash_command(name="코드추가", description="멤버쉽 코드를 추가하고 기간을 설정합니다.[개발자전용]")
async def license_code_add(ctx, code: str = commands.Param(name="코드", choices=["gift", "reward", "general"]), date: int = commands.Param(name="기간")):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "코드추가", f"{code}, {date}")
    if ctx.author.id in developer:
        # 기간을 일 단위로 받아서 설정
        if date <= 0:
            embed = disnake.Embed(color=embederrorcolor)
            embed.add_field(name="❌ 오류", value="유효한 기간을 입력해야 합니다.")
            await ctx.send(embed=embed, ephemeral=True)
            return

        random_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

        if code == "gift":
            code = f"gift-{random_code}"
        elif code == "reward":
            code = f"reward-{random_code}"
        elif code == "general":
            code = f"{random_code}-{random_code}"
        else:
            print("코드추가 명령어 오류발생")
            return
        db_path = os.path.join('system_database', 'membership.db')
        economy_aiodb = await aiosqlite.connect(db_path)  # 데이터베이스 연결
        await economy_aiodb.execute("INSERT INTO license (code, day, use) VALUES (?, ?, ?)", (code, date, 0))
        await economy_aiodb.commit()

        embed = disnake.Embed(title="✅ 코드추가", color=0x00ff00)
        embed.add_field(name="코드", value=f"{code}")
        embed.add_field(name="기간", value=f"{date}")
        await ctx.send(embed=embed, ephemeral=True)
        await economy_aiodb.close()
    else:
        embed=disnake.Embed(color=embederrorcolor)
        embed.add_field(name="❌ 오류", value="개발자만 실행가능한 명령어입니다.")
        await ctx.send(embed=embed, ephemeral=True)

@bot.slash_command(name="코드삭제", description="멤버쉽 코드를 삭제합니다.")
async def license_code_remove(ctx, code: str):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "코드삭제", f"{code}")
    if ctx.author.id in developer:
        db_path = os.path.join('system_database', 'membership.db')
        economy_aiodb = await aiosqlite.connect(db_path)  # 데이터베이스 연결

        # 해당 코드가 존재하는지 확인
        aiocursor = await economy_aiodb.execute("SELECT * FROM license WHERE code=?", (code,))
        license_data = await aiocursor.fetchone()

        if license_data is None:
            embed = disnake.Embed(color=embederrorcolor)
            embed.add_field(name="❌ 오류", value="유효하지 않은 코드입니다.")
            await ctx.send(embed=embed, ephemeral=True)
            await aiocursor.close()
            await economy_aiodb.close()
            return

        # 코드 삭제
        await economy_aiodb.execute("DELETE FROM license WHERE code=?", (code,))
        await economy_aiodb.commit()

        embed = disnake.Embed(color=0x00ff00)
        embed.add_field(name="✅ 성공", value="코드가 삭제되었습니다.")
        await ctx.send(embed=embed, ephemeral=True)

        await aiocursor.close()
        await economy_aiodb.close()
    else:
        embed=disnake.Embed(color=embederrorcolor)
        embed.add_field(name="❌ 오류", value="개발자만 실행가능한 명령어입니다.")
        await ctx.send(embed=embed, ephemeral=True)

@bot.slash_command(name="멤버쉽등록", description="멤버쉽 회원으로 등록하거나 기간을 연장합니다.")
async def license_code_use(ctx, code: str):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "멤버쉽등록", f"{code}")
    db_path = os.path.join('system_database', 'membership.db')
    economy_aiodb = await aiosqlite.connect(db_path)

    # license 테이블에서 code 확인
    aiocursor = await economy_aiodb.execute("SELECT use, day FROM license WHERE code=?", (code,))
    license_data = await aiocursor.fetchone()

    if license_data is None:
        embed = disnake.Embed(color=embederrorcolor)
        embed.add_field(name="❌ 오류", value="유효하지 않은 코드입니다.")
        await ctx.send(embed=embed, ephemeral=True)
        await aiocursor.close()
        await economy_aiodb.close()
        return

    # use 값이 1이면 이미 사용된 코드
    if license_data[0] == 1:
        embed = disnake.Embed(color=embederrorcolor)
        embed.add_field(name="❌ 오류", value="이미 사용된 코드입니다.")
        await ctx.send(embed=embed, ephemeral=True)
        await aiocursor.close()
        await economy_aiodb.close()
        return

    # 현재 날짜 계산
    current_date = datetime.now()
    additional_days = license_data[1]
    expiration_date = current_date + timedelta(days=additional_days)

    # user 테이블에서 현재 사용자 확인
    aiocursor = await economy_aiodb.execute("SELECT class, expiration_date FROM user WHERE id=?", (ctx.author.id,))
    dbdata = await aiocursor.fetchone()

    if dbdata is None:
        # 데이터가 없을 경우 비회원으로 등록
        await economy_aiodb.execute("INSERT INTO user (id, class, expiration_date, credit) VALUES (?, ?, ?, ?)", 
                                     (ctx.author.id, 1, expiration_date.strftime('%Y/%m/%d'), 30))  # 1: 회원
        await economy_aiodb.commit()
        embed = disnake.Embed(color=0x00ff00)
        embed.add_field(name="✅ 성공", value="비회원에서 회원으로 등록되었습니다.")
        await ctx.send(embed=embed, ephemeral=True)
    else:
        member_class = int(dbdata[0])
        existing_expiration_date = datetime.strptime(dbdata[1], '%Y/%m/%d')

        if member_class == 0:  # 0: 비회원
            # 비회원에서 회원으로 변경
            await economy_aiodb.execute("UPDATE user SET class = ?, expiration_date = ? WHERE id = ?", 
                                         (1, expiration_date.strftime('%Y/%m/%d'), ctx.author.id))
            await economy_aiodb.commit()
            embed = disnake.Embed(color=0x00ff00)
            embed.add_field(name="✅ 성공", value="비회원에서 회원으로 변경되었습니다.")
            await ctx.send(embed=embed, ephemeral=True)
        else:
            # 기존 만료일에 추가
            new_expiration_date = existing_expiration_date + timedelta(days=additional_days)
            await economy_aiodb.execute("UPDATE user SET expiration_date = ? WHERE id = ?", 
                                         (new_expiration_date.strftime('%Y/%m/%d'), ctx.author.id))
            await economy_aiodb.commit()
            embed = disnake.Embed(color=0x00ff00)
            embed.add_field(name="✅ 성공", value="기간이 연장되었습니다.")
            await ctx.send(embed=embed, ephemeral=True)

    # 코드 사용 처리 (use 값을 1로 업데이트)
    await economy_aiodb.execute("UPDATE license SET use = ? WHERE code = ?", (1, code))
    await economy_aiodb.commit()

    await aiocursor.close()
    await economy_aiodb.close()

@bot.slash_command(name="멤버쉽", description="현재 멤버쉽 상태를 확인합니다.")
async def check_membership_status(ctx):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "멤버쉽", None)
    await membership(ctx)
    db_path = os.path.join('system_database', 'membership.db')
    economy_aiodb = await aiosqlite.connect(db_path)

    # user 테이블에서 현재 사용자 확인
    aiocursor = await economy_aiodb.execute("SELECT class, expiration_date, credit FROM user WHERE id=?", (ctx.author.id,))
    dbdata = await aiocursor.fetchone()

    credits = 0  # 기본값으로 초기화

    member_class = int(dbdata[0])
    expiration_date = dbdata[1]
    credits = dbdata[2]  # 사용자 데이터에서 크레딧 가져오기

    if member_class == 0:
        status = "비회원"
    elif member_class == 1:
        status = "브론즈_회원"
    elif member_class == 2:
        status = "실버_회원"
    elif member_class == 3:
        status = "다이아_회원"
    elif member_class == 4:
        status = "레전드_회원"
    elif member_class == 5:
        status = "개발자"
    else:
        print("error : 데이터값이 0, 1, 2, 3, 4, 5가 아닙니다.")

    embed = disnake.Embed(color=0x00ff00)
    embed.add_field(name=f"{ctx.author.name}님의 멤버십 📋", value=f"상태: {status}\n만료일: {expiration_date}\n💰 크레딧: {credits}")
    await ctx.send(embed=embed)

    await aiocursor.close()
    await economy_aiodb.close()

@bot.slash_command(name="가입", description="경제기능을 가입합니다.")
async def economy_join(ctx):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "가입", None)
    if ctx.guild is None:
        await ctx.send("이 명령어는 서버에서만 사용할 수 있습니다.")
        return
    db_path = os.path.join('system_database', 'economy.db')
    economy_aiodb = await aiosqlite.connect(db_path)
    aiocursor = await economy_aiodb.execute("SELECT tos FROM user WHERE id=?", (ctx.author.id,))
    dbdata = await aiocursor.fetchone()
    add_money = 50000
    await aiocursor.close()
    if dbdata == None:
        aiocursor = await economy_aiodb.execute("INSERT INTO user (id, money, tos, level, exp, lose_money, dm_on_off) VALUES (?, ?, ?, ?, ?, ?, ?)", (ctx.author.id, add_money, 0, 0, 0, 0, 0))
        await economy_aiodb.commit()
        await aiocursor.close()
        await addmoney(ctx.author.id, add_money)
        embed=disnake.Embed(color=embedsuccess)
        embed.add_field(name="✅ 가입", value=f"{ctx.author.mention} 가입이 완료되었습니다.\n지원금 {add_money:,}원이 지급되었습니다.")
        await ctx.send(embed=embed)
    else:
        embed=disnake.Embed(color=embederrorcolor)
        embed.add_field(name="❌ 오류", value=f"{ctx.author.mention} 이미 가입된 유저입니다.")
        await ctx.send(embed=embed, ephemeral=True)

@bot.slash_command(name="탈퇴", description="경제기능을 탈퇴합니다.")
async def economy_secession(ctx):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "탈퇴", None)
    db_path = os.path.join('system_database', 'economy.db')
    economy_aiodb = await aiosqlite.connect(db_path)
    aiocursor = await economy_aiodb.execute("SELECT tos FROM user WHERE id=?", (ctx.author.id,))
    dbdata = await aiocursor.fetchone()
    await aiocursor.close()
    
    if dbdata is not None:
        embed = disnake.Embed(color=0xffff00)
        embed.add_field(name="탈퇴", value="경고! 탈퇴시 모든 데이터가 **즉시 삭제**되며\n보유중인 잔액이 초기화됩니다.")
        message = await ctx.send(embed=embed, view=AuthButton(economy_aiodb, ctx.author.id))
    else:
        embed = disnake.Embed(color=embederrorcolor)
        embed.add_field(name="❌ 오류", value=f"{ctx.author.mention}\n가입되지 않은 유저입니다.")
        await ctx.send(embed=embed, ephemeral=True)

class AuthButton(disnake.ui.View):
    def __init__(self, economy_aiodb, author_id):
        super().__init__(timeout=None)
        self.economy_aiodb = economy_aiodb
        self.author_id = author_id
        self.closed = False  # 새로운 속성 추가

    @disnake.ui.button(label="탈퇴", style=disnake.ButtonStyle.green)
    async def 탈퇴(self, button: disnake.ui.Button, ctx: disnake.MessageInteraction):
        embed = disnake.Embed(color=0x00FF00)
        embed.add_field(name="탈퇴 완료!", value="탈퇴가 완료되었습니다!")
        await ctx.message.edit(embed=embed, view=None)
        aiocursor = await self.economy_aiodb.execute("DELETE FROM user WHERE id=?", (self.author_id,))
        await self.economy_aiodb.commit()
        await aiocursor.close()
        self.stop()
        button.disabled = True

    @disnake.ui.button(label="취소", style=disnake.ButtonStyle.red)
    async def 취소(self, button: disnake.ui.Button, ctx: disnake.MessageInteraction):
        embed = disnake.Embed(color=0x00FF00)
        embed.add_field(name="탈퇴 취소", value="탈퇴가 취소되었습니다.")
        await ctx.message.edit(embed=embed, view=None)
        self.stop()
        button.disabled = True

@bot.slash_command(name="몬스터타입설정", description="채널의 몬스터 타입을 설정합니다. [관리자전용]")
async def set_monster_type_command(ctx, monster_type: str = commands.Param(name="타입", choices=["초원", "무너진도시", "지옥"])):
    if not await tos(ctx):
        return
    # 서버의 관리자인지 확인
    if not ctx.author.guild_permissions.manage_channels:
        embed = disnake.Embed(color=0xff0000)
        embed.add_field(name="❌ 오류", value="이 명령어를 사용할 권한이 없습니다. 관리자만 사용할 수 있습니다.")
        await ctx.send(embed=embed)
        return

    server_id = str(ctx.guild.id)  # 서버 ID
    channel_id = str(ctx.channel.id)  # 채널 ID

    # 몬스터 타입 설정
    await set_monster_type(server_id, channel_id, monster_type)

    await ctx.send(f"{ctx.channel.name} 채널의 몬스터 타입이 '{monster_type}'으로 설정되었습니다.")

# 초원
weak_monsters = {
    "메뚜기": {"hp": 350, "reward": 500},
    "데구리": {"hp": 450, "reward": 600},
    "거북이": {"hp": 600, "reward": 750},
    "이상해씨": {"hp": 850, "reward": 1000},
    "피카츄": {"hp": 1000, "reward": 1150},
    "파이리": {"hp": 1200, "reward": 1400},
}
# 무너진도시
citi_monsters = {
    "라이츄": {"hp": 1500, "reward": 1900},
    "리자몽": {"hp": 1800, "reward": 2200},
    "마기라스": {"hp": 2150, "reward": 2550},
    "리자드": {"hp": 2500, "reward": 2900},
    "메타그로스": {"hp": 2850, "reward": 3300},
    "메가리자몽": {"hp": 3100, "reward": 3600},
}
# 지옥
hell_monsters = {
    "용암진드기": {"hp": 3400, "reward": 4100},
    "용암돼지": {"hp": 3800, "reward": 4500},
    "저승사자": {"hp": 4200, "reward": 4900},
    "가스트": {"hp": 4600, "reward": 5300},
    "드래곤": {"hp": 5000, "reward": 5750},
    "메가드래곤": {"hp": 5400, "reward": 6200},
}

sword = ["나무검", "돌검", "철검", "단단한검", # 초원
         "무적의검", "만용의검", "폭풍의검", # 무너진도시
         "화염의검", "사신의낫", "불타는도끼"] # 지옥

# 초원에서 사용할 수 없는 검 리스트
veld_restricted_swords = ["무적의검", "만용의검", "폭풍의검", "화염의검", "사신의낫", "불타는도끼"]
# 무너진도시에서 사용할 수 없는 검 리스트
master_restricted_swords = ["나무검", "돌검", "철검", "단단한검", "화염의검", "사신의낫", "불타는도끼"]
# 지옥에서 사용할 수 없는 검 리스트
hell_restricted_swords = ["나무검", "돌검", "철검", "단단한검","무적의검", "만용의검", "폭풍의검"]

@bot.slash_command(name="몬스터사냥", description="랜덤 몬스터를 잡습니다.")
async def catch_monster(ctx, sword_name: str = commands.Param(name="검이름", choices=sword)):
    if not await tos(ctx):
        return
    await ctx.response.defer()  # 응답 지연

    if ctx.author is None:
        embed = disnake.Embed(color=0xff0000)
        embed.add_field(name="❌ 오류", value="사용자 정보를 가져올 수 없습니다.")
        await ctx.send(embed=embed)
        return

    user_id = ctx.author.id  # 사용자 ID 가져오기

    # 사용자의 인벤토리에서 칼이 있는지 확인
    sword_info = await get_user_item(user_id, sword_name)

    if sword_info is None or (isinstance(sword_info, tuple) and sword_info[1] <= 0):
        embed = disnake.Embed(color=0xff0000)
        embed.add_field(name="❌ 오류", value=f"{sword_name}이(가) 인벤토리에 없습니다.")
        await ctx.send(embed=embed)
        return

    # 채널의 몬스터 타입 조회
    server_id = str(ctx.guild.id)
    channel_id = str(ctx.channel.id)
    monster_type = await get_monster_type(server_id, channel_id)

    # 초원 및 고수의 땅 제한 검사
    if (monster_type == "초원" and sword_name in veld_restricted_swords) or \
       (monster_type == "무너진도시" and sword_name in master_restricted_swords) or \
       (monster_type == "지옥" and sword_name in hell_restricted_swords) or \
       (monster_type is None and sword_name in veld_restricted_swords):
        embed = disnake.Embed(color=0xff0000)
        embed.add_field(name="❌ 오류", value=f"{sword_name}은(는) 해당 지역에서 사용할 수 없습니다.")
        await ctx.send(embed=embed)
        return

    # 몬스터 선택
    monsters_dict = {
        "초원": weak_monsters,
        "무너진도시": citi_monsters,
        "지옥": hell_monsters
    }
    monsters = monsters_dict.get(monster_type, weak_monsters)
    monster_name = random.choice(list(monsters.keys()))
    monster_hp = monsters[monster_name]["hp"]

    # 칼의 기본 데미지 조회
    sword_damage = await get_item_damage(sword_name)
    sword_class = await get_item_class(user_id, sword_name)
    total_damage = sword_damage * sword_class  # 최종 데미지 계산

    # 초기 메시지 임베드 생성
    embed = disnake.Embed(title="몬스터와의 전투!", description="", color=0x00ff00)
    embed.add_field(name=f"몬스터: {monster_name}", value=f"HP: {monster_hp}", inline=False)

    # 공격 버튼 생성
    attack_button = disnake.ui.Button(label="공격", style=disnake.ButtonStyle.primary)
    end_battle_button = disnake.ui.Button(label="전투 종료", style=disnake.ButtonStyle.danger)

    # 버튼 뷰 생성
    view = disnake.ui.View(timeout=None)  # 뷰의 타임아웃을 설정하지 않음
    view.add_item(attack_button)
    view.add_item(end_battle_button)

    # 메시지 전송
    try:
        await ctx.send(embed=embed, view=view)
    except Exception as e:
        await ctx.send(f"메시지를 전송하는 데 실패했습니다: {str(e)}")
        return

    async def attack_callback(interaction):
        await interaction.response.defer()  # 응답 지연
        nonlocal monster_hp

        # 몬스터 도망 확률 체크
        if random.random() < 0.05:  # 5% 확률로 도망
            embed = disnake.Embed(title="❌ 전투 실패", description="몬스터가 도망갔습니다.", color=0xff0000)
            await interaction.edit_original_message(embed=embed, view=None)  # 버튼 제거
            return

        # 공격 시 칼의 파괴 확률
        sword_destroy_chance = random.randint(1, 101)
        defense_item_info = await get_user_item(user_id, "파괴방어권")

        if sword_destroy_chance <= 15:  # 15% 확률로 칼이 파괴됨
            if defense_item_info and isinstance(defense_item_info, tuple) and defense_item_info[1] > 0:
                await remove_item_from_user_inventory(user_id, "파괴방어권", 1)
                embed = disnake.Embed(title="❌ 전투 실패", description="무기가 파괴될뻔했지만, 방어권 사용으로 파괴되지 않았습니다.", color=0x00ff00)
                await interaction.edit_original_message(embed=embed, view=None)
            else:
                await remove_item_from_user_inventory(user_id, sword_name, 1)
                embed = disnake.Embed(title="❌ 전투 실패", description="전투중 무기가 파괴되었습니다.", color=0xff0000)
                await interaction.edit_original_message(embed=embed, view=None)
        # 몬스터에게 데미지 입힘
        monster_hp -= total_damage

        if monster_hp > 0:
            embed = disnake.Embed(title="몬스터와의 전투!", color=0x00ff00)
            embed.add_field(name=f"몬스터: {monster_name}", value=f"HP: {monster_hp}", inline=False)
            await interaction.message.edit(embed=embed, view=view)
        else:
            reward = monsters[monster_name]["reward"]
            await add_cash_item_count(user_id, reward)
            embed = disnake.Embed(title="✅ 전투 성공", description="", color=0x00ff00)
            embed.add_field(name="", value=f"{monster_name}을(를) 처치했습니다! 보상으로 {reward}을(를) 받았습니다.")
            await interaction.message.edit(embed=embed, view=None)  # 버튼 제거

    async def end_battle_callback(interaction):
        await interaction.response.defer()  # 응답 지연
        embed = disnake.Embed(title="⚔️ 전투 종료", description="", color=0xff0000)
        embed.add_field(name="", value="전투가 종료되었습니다.")
        await interaction.followup.edit_message(embed=embed, view=None)  # 버튼 제거

    # 버튼 콜백 설정
    attack_button.callback = attack_callback
    end_battle_button.callback = end_battle_callback

@bot.slash_command(name="아이템사용", description="경험치 병을 사용하여 경험치를 증가시킵니다.")
async def use_experience_potion(ctx, count: int = commands.Param(name="개수")):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return

    await command_use_log(ctx, "경험치병사용", f"{count}")
    
    if not await member_status(ctx):
        return

    # 사용자의 인벤토리에서 경험치 병 수량 조회
    user_item_count = await get_user_item(ctx.author.id, "경험치 병")

    # 아이템 수량 검증
    if user_item_count is None or user_item_count <= 0:
        await send_error_embed(ctx, "경험치 병이 인벤토리에 없습니다.")
        return

    if count <= 0:
        await send_error_embed(ctx, "사용할 경험치 병의 수량은 1개 이상이어야 합니다.")
        return

    if user_item_count < count:
        await send_error_embed(ctx, "인벤토리에 요청한 수량만큼의 경험치 병이 없습니다.")
        return

    # 경험치 병의 add_exp 값을 아이템 테이블에서 조회
    experience_per_potion = await fetch_experience_per_potion()
    if experience_per_potion is None:
        await send_error_embed(ctx, "경험치 병의 경험치 정보가 없습니다.")
        return

    total_experience = experience_per_potion * count

    # 사용자 경험치 업데이트
    await add_exp(ctx.author.id, total_experience)
    await remove_item_from_user_inventory(ctx.author.id, "경험치 병", count)

    embed = disnake.Embed(color=0x00ff00, description=f"{count}개의 경험치 병을 사용하여 {total_experience} 경험치를 얻었습니다.")
    await ctx.send(embed=embed)

async def send_error_embed(ctx, error_message):
    embed = disnake.Embed(color=0xff0000, description=f"❌ 오류: {error_message}")
    await ctx.send(embed=embed)

async def fetch_experience_per_potion():
    db_path = os.path.join('system_database', 'economy.db')
    async with aiosqlite.connect(db_path) as economy_aiodb:
        async with economy_aiodb.cursor() as aiocursor:
            await aiocursor.execute("SELECT add_exp FROM item WHERE name = ?", ("경험치 병",))
            exp_info = await aiocursor.fetchone()
            return exp_info[0] if exp_info else None

class ItemView(disnake.ui.View):
    def __init__(self, data, per_page=5):
        super().__init__(timeout=None)
        self.data = data
        self.per_page = per_page
        self.current_page = 0
        self.max_page = (len(data) - 1) // per_page
        self.message = None
        self.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        if self.current_page > 0:
            self.add_item(PreviousButton())
        if self.current_page < self.max_page:
            self.add_item(NextButton())

    async def update_message(self, interaction=None):
        embed = await self.create_embed()
        self.update_buttons()
        if interaction:
            await interaction.response.defer()
            await interaction.edit_original_message(embed=embed, view=self)
        elif self.message:
            await self.message.edit(embed=embed, view=self)

    async def create_embed(self):
        embed = disnake.Embed(title="아이템 목록", color=0x00ff00)
        start = self.current_page * self.per_page
        end = start + self.per_page

        for item in self.data[start:end]:
            if len(item) == 4:
                name, price, add_exp, damage = item
                embed.add_field(name=name, value=f"가격: {price:,}원 | 피해: {damage} | 경험치: {add_exp}", inline=False)
            else:
                print(f"아이템 데이터 오류: {item}")

        embed.set_footer(text=f"페이지 {self.current_page + 1}/{self.max_page + 1} | 마지막 업데이트: {self.last_updated}")
        return embed

class PreviousButton(disnake.ui.Button):
    def __init__(self):
        super().__init__(label="이전", style=disnake.ButtonStyle.primary)

    async def callback(self, ctx: disnake.Interaction):
        view: ItemView = self.view
        if view.current_page > 0:
            view.current_page -= 1
            await view.update_message(ctx)

class NextButton(disnake.ui.Button):
    def __init__(self):
        super().__init__(label="다음", style=disnake.ButtonStyle.primary)

    async def callback(self, ctx: disnake.Interaction):
        view: ItemView = self.view
        if view.current_page < view.max_page:
            view.current_page += 1
            await view.update_message(ctx)

@bot.slash_command(name="아이템목록", description="아이템 목록을 확인합니다.")
async def item_list(ctx):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "아이템목록", None)
    data = await get_items()  # 아이템 정보를 가져옴
    view = ItemView(data)

    # 태스크가 이미 실행 중인지 확인
    if view_update3.is_running():
        view_update3.stop()  # 실행 중이면 중지

    embed = await view.create_embed()
    view.message = await ctx.send(embed=embed, view=view)
    view_update3.start(view)  # 태스크 시작

@tasks.loop(seconds=20)
async def view_update3(view: ItemView):
    view.data = await get_items()  # 아이템 정보를 다시 가져옴
    view.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    await view.update_message()

# 강화 확률을 정의합니다.
upgrade_chances = {
    1: 0.90,
    2: 0.85,
    3: 0.80,
    4: 0.75,
    5: 0.70,
    6: 0.65,
    7: 0.60,
    8: 0.50,
    9: 0.40,
    10: 0.30,
}

@bot.slash_command(name="강화", description="무기를 강화합니다.")
async def upgrade_item(ctx, weapon_name: str = commands.Param(name="아이템", choices=sword)):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return
    
    await command_use_log(ctx, "아이템강화", f"{weapon_name}")
    if not await member_status(ctx):
        return

    # 사용자 인벤토리에서 아이템 정보 가져오기
    item_info = await get_user_item_class(ctx.author.id, weapon_name)

    if not item_info:
        return await send_error_message(ctx, f"{weapon_name} 아이템이 인벤토리에 없습니다.")

    current_class = item_info[1]  # 현재 강화 등급
    if current_class >= 10:
        return await send_error_message(ctx, "이미 최대 강화 등급(10강)입니다.")

    # 강화 비용 계산
    item_info = await get_item_info(weapon_name)
    if item_info is None:
        return await send_error_message(ctx, f"{weapon_name} 아이템 정보를 찾을 수 없습니다.")
    
    item_price = item_info['price']
    global upgrade_cost
    upgrade_cost = round(((current_class + 1) * (item_price * 0.1) * 0.002) * 0.9)

    # 사용자 캐시 조회
    user_cash = await get_cash_item_count(ctx.author.id)
    if user_cash < upgrade_cost:
        return await send_error_message(ctx, "캐시가 부족하여 강화할 수 없습니다.")

    # 버튼 생성
    view = await create_upgrade_view(ctx, weapon_name, current_class, upgrade_cost)

    # 초기 메시지 전송
    embed = await create_upgrade_embed(weapon_name, current_class, upgrade_cost)
    await ctx.send(embed=embed, view=view)

async def create_upgrade_view(ctx, weapon_name, current_class, upgrade_cost, interaction_user_id):
    upgrade_button = disnake.ui.Button(label="강화", style=disnake.ButtonStyle.primary)
    cancel_button = disnake.ui.Button(label="강화 취소", style=disnake.ButtonStyle.danger)

    view = disnake.ui.View()
    view.add_item(upgrade_button)
    view.add_item(cancel_button)

    # 버튼 콜백 설정
    upgrade_button.callback = lambda interaction: upgrade_callback(interaction, weapon_name, current_class, upgrade_cost, view, interaction_user_id)
    cancel_button.callback = lambda interaction: cancel_callback(interaction, interaction_user_id)

    return view

async def create_upgrade_embed(weapon_name, current_class, upgrade_cost):
    embed = disnake.Embed(title="아이템 강화", color=0x00ffff)
    embed.add_field(name="강화할 아이템", value=weapon_name, inline=False)
    embed.add_field(name="현재 강화 등급", value=f"{current_class}강", inline=False)
    embed.add_field(name="비용", value=f"{upgrade_cost} 캐시", inline=False)
    return embed

async def upgrade_callback(interaction, weapon_name, current_class, upgrade_cost, view, interaction_user_id):
    if interaction.user.id != interaction_user_id:
        return await send_error_message(interaction, "이 버튼은 호출자만 사용할 수 있습니다.")

    # 사용자 캐시 조회
    user_cash = await get_cash_item_count(interaction.author.id)
    if user_cash < upgrade_cost:
        return await send_error_message(interaction, "캐시가 부족하여 강화할 수 없습니다.")

    # 캐시 차감
    await remove_cash_item_count(interaction.author.id, upgrade_cost)

    # 강화 중 파괴 확률 체크
    if await handle_destruction(interaction, weapon_name):
        return

    # 강화 성공 확률 확인
    success_chance = upgrade_chances.get(current_class + 1)
    if success_chance is None:
        return await send_error_message(interaction, "강화 성공 확률 정보를 찾을 수 없습니다.")

    if random.random() <= success_chance:
        await handle_upgrade_success(interaction, weapon_name, current_class, view)
    else:
        await handle_upgrade_failure(interaction, weapon_name, current_class, view)

async def handle_destruction(interaction, weapon_name):
    destruction_chance = random.random()
    if destruction_chance <= 0.05:  # 5% 확률로 파괴
        defense_item_info = await get_user_item(interaction.author.id, "파괴방어권")
        if defense_item_info and isinstance(defense_item_info, tuple) and defense_item_info[1] > 0:
            await remove_item_from_user_inventory(interaction.author.id, "파괴방어권", 1)
            embed = disnake.Embed(color=0x00ff00)
            embed.add_field(name="✅ 방어 성공", value=f"{weapon_name} 아이템이 파괴되지 않았습니다! '파괴방어권'이 사용되었습니다.")
            await interaction.response.edit_message(embed=embed, view=None)
            return True  # 방어 성공
        await remove_item_from_user_inventory(interaction.author.id, weapon_name, 1)
        embed = disnake.Embed(color=0xff0000)
        embed.add_field(name="❌ 아이템 파괴", value=f"{weapon_name} 아이템이 파괴되었습니다.")
        await interaction.response.edit_message(embed=embed, view=None)
        return True  # 아이템 파괴
    return False  # 파괴되지 않음

async def handle_upgrade_success(interaction, weapon_name, current_class, view):
    new_class = current_class + 1
    await update_item_class(interaction.author.id, weapon_name, new_class)
    embed = disnake.Embed(color=0x00ff00)
    embed.add_field(name="✅ 강화 성공", value=f"{weapon_name} 아이템이 {new_class}강으로 강화되었습니다.")
    await interaction.response.edit_message(embed=embed, view=None)

async def handle_upgrade_failure(interaction, weapon_name, current_class, view):
    await update_item_class(interaction.author.id, weapon_name, current_class)
    
    embed = disnake.Embed(color=0xff0000)
    embed.add_field(name="❌ 강화 실패", value=f"{weapon_name} 아이템의 강화에 실패했습니다.")
    embed.add_field(name="현재 등급", value=f"{current_class}강", inline=False)
    embed.add_field(name="비용", value=f"{upgrade_cost} 캐시", inline=False)
    embed.add_field(name="팁", value="다시 시도하거나 다른 아이템을 강화해 보세요!", inline=False)
    await interaction.response.edit_message(embed=embed, view=view)

async def cancel_callback(interaction, interaction_user_id):
    if interaction.user.id != interaction_user_id:
        return await send_error_message(interaction, "이 버튼은 호출자만 사용할 수 있습니다.")

    embed = disnake.Embed(color=0xff0000)
    embed.add_field(name="⚔️ 강화 취소", value="강화가 취소되었습니다.")
    await interaction.response.edit_message(embed=embed, view=None)

async def send_error_message(interaction, message):
    embed = disnake.Embed(color=0xff0000)
    embed.add_field(name="❌ 오류", value=message)
    await interaction.followup.send(embed=embed)

@bot.slash_command(name="아이템거래", description="아이템을 구매 또는 판매할 수 있습니다.")
async def item_trading(ctx, item_name: str = commands.Param(name="이름"), choice: str = commands.Param(name="선택", choices=["구매", "판매"]), count: int = commands.Param(name="개수", default=1)):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "아이템거래", f"{item_name}, {choice}, {count}")
    if not await member_status(ctx):
        return
    
    embed = disnake.Embed(color=0x00ff00)
    
    try:
        # 음수 거래 방지
        if count <= 0:
            raise ValueError("거래할 아이템 수량은 1개 이상이어야 합니다.")

        item_info = await get_item_info(item_name)  # 아이템 정보를 가져오는 함수
        if item_info is None:
            raise ValueError(f"{item_name} 아이템은 존재하지 않습니다.")
        
        item_price = item_info['price']  # 아이템의 가격
        total_price = item_price * count

        if choice == "구매":
            if item_name in ["나무검", "돌검", "철검", "단단한검", "무적의검", "만용의검", "폭풍의검", "화염의검", "사신의낫", "불타는도끼"]:
                user_item_quantity = await get_user_item_count(ctx.author.id, item_name)  # 사용자의 아이템 수량 조회
                if user_item_quantity >= 1:
                    raise ValueError(f"{item_name}은(는) 이미 1개 보유하고 있습니다. 추가 구매할 수 없습니다.")
                count = 1  # 수량을 1로 설정
                total_price = item_price  # 총 가격도 1개 가격으로 설정

            user_balance = await getmoney(ctx.author.id)  # 사용자의 잔액 조회
            if user_balance < total_price:
                raise ValueError("잔액이 부족합니다.")

            await removemoney(ctx.author.id, total_price)  # 잔액 차감
            await add_item_to_user_inventory(ctx.author.id, item_name, count)  # 인벤토리에 아이템 추가
            
            embed.title = "아이템 구매 완료"
            embed.add_field(name="아이템 이름", value=item_name, inline=False)
            embed.add_field(name="구매 수량", value=f"{count:,}개", inline=False)
            embed.add_field(name="총 구매 가격", value=f"{total_price:,}원", inline=False)

        elif choice == "판매":
            user_item_quantity = await get_user_item_count(ctx.author.id, item_name)  # 사용자의 아이템 수량 조회
            if user_item_quantity < count:
                raise ValueError("판매할 수량이 인벤토리보다 많습니다.")

            await remove_item_from_user_inventory(ctx.author.id, item_name, count)  # 인벤토리에서 아이템 제거
            await addmoney(ctx.author.id, total_price)  # 잔액에 판매 금액 추가
            
            embed.title = "아이템 판매 완료"
            embed.add_field(name="아이템 이름", value=item_name, inline=False)
            embed.add_field(name="판매 수량", value=f"{count:,}개", inline=False)
            embed.add_field(name="총 판매 가격", value=f"{total_price:,}원", inline=False)

        await ctx.send(embed=embed)
    except ValueError as e:
        embed = disnake.Embed(color=0xff0000)
        embed.add_field(name="❌ 오류", value=str(e))
        await ctx.send(embed=embed)

class ItemView2(disnake.ui.View):
    def __init__(self, items, per_page=5):
        super().__init__(timeout=None)
        self.items = items
        self.per_page = per_page
        self.current_page = 0
        self.max_page = (len(items) - 1) // per_page
        self.message = None

        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        if self.current_page > 0:
            self.add_item(PreviousButton())
        if self.current_page < self.max_page:
            self.add_item(NextButton())

    async def update_message(self, interaction):
        embed = await self.create_embed()
        self.update_buttons()
        await interaction.response.edit_message(embed=embed, view=self)

    async def create_embed(self):
        embed = disnake.Embed(title="인벤토리 📦", color=0x00ff00)
        start = self.current_page * self.per_page
        end = start + self.per_page

        if not self.items:
            embed.add_field(name="❌ 오류", value="보유하고 있는 아이템이 없습니다.")
            return embed

        for item_name, quantity, class_value in self.items[start:end]:
            embed.add_field(name=item_name, value=f"수량: {quantity:,}개, {class_value}강", inline=False)

        embed.add_field(name="", value=f"📄 페이지 {self.current_page + 1}/{self.max_page + 1}", inline=False)
        return embed

@bot.slash_command(name="인벤토리", description="보유 중인 아이템을 확인합니다.")
async def inventory(ctx):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "인벤토리", None)
    if not await member_status(ctx):
        return

    items = await get_user_inventory(ctx.author.id)  # 사용자의 인벤토리 아이템을 가져오는 함수

    # 사용자 이름 가져오기
    user_name = ctx.author.name

    embed = disnake.Embed(title=f"{user_name}의 인벤토리 📦", color=0x00ff00)

    if not items:
        embed.add_field(name="❌ 오류", value="보유하고 있는 아이템이 없습니다.")
        await ctx.send(embed=embed)
    else:
        # 아이템 정보를 담고 있는 ItemView 생성
        view = ItemView2(items)

        # 초기 임베드 생성 및 메시지 전송
        view.message = await ctx.send(embed=await view.create_embed(), view=view)

class PreviousButton(disnake.ui.Button):
    def __init__(self):
        super().__init__(label="이전", style=disnake.ButtonStyle.primary)

    async def callback(self, interaction: disnake.MessageInteraction):
        view: ItemView2 = self.view
        if view.current_page > 0:
            view.current_page -= 1
            await view.update_message(interaction)

class NextButton(disnake.ui.Button):
    def __init__(self):
        super().__init__(label="다음", style=disnake.ButtonStyle.primary)

    async def callback(self, interaction: disnake.MessageInteraction):
        view: ItemView2 = self.view
        if view.current_page < view.max_page:
            view.current_page += 1
            await view.update_message(interaction)

class CoinView1(disnake.ui.View):
    def __init__(self, data, per_page=5):
        super().__init__(timeout=None)
        self.data = data
        self.per_page = per_page
        self.current_page = 0
        self.max_page = (len(data) - 1) // per_page
        self.message = None
        self.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.last_interaction = None  # 마지막 상호작용 저장

        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        if self.current_page > 0:
            self.add_item(PreviousButton())
        if self.current_page < self.max_page:
            self.add_item(NextButton())

    async def update_message(self, interaction):
        embed = await self.create_embed()
        self.update_buttons()
        await interaction.response.edit_message(embed=embed, view=self)

    async def create_embed(self):
        embed = disnake.Embed(title="코인목록", color=0x00ff00)
        start = self.current_page * self.per_page
        end = start + self.per_page
        for name, price in self.data[start:end]:
            embed.add_field(name=name, value=f"{price:,}원", inline=False)
        embed.set_footer(text=f"페이지 {self.current_page + 1}/{self.max_page + 1} | 마지막 업데이트: {self.last_updated}")
        return embed

class PreviousButton(disnake.ui.Button):
    def __init__(self):
        super().__init__(label="이전", style=disnake.ButtonStyle.primary)

    async def callback(self, interaction: disnake.MessageInteraction):
        view: CoinView1 = self.view
        if view.current_page > 0:
            view.current_page -= 1
            view.last_interaction = interaction  # 현재 상호작용 저장
            await view.update_message(interaction)

class NextButton(disnake.ui.Button):
    def __init__(self):
        super().__init__(label="다음", style=disnake.ButtonStyle.primary)

    async def callback(self, interaction: disnake.MessageInteraction):
        view: CoinView1 = self.view
        if view.current_page < view.max_page:
            view.current_page += 1
            view.last_interaction = interaction  # 현재 상호작용 저장
            await view.update_message(interaction)

@bot.slash_command(name="코인목록", description="상장된 가상화폐를 확인합니다.")
async def coin_list(ctx):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "코인목록", None)
    data = await getcoin()
    view = CoinView1(data)

    # 태스크가 이미 실행 중인지 확인
    if view_update2.is_running():
        view_update2.cancel()  # 이미 실행 중이면 중지
    view_update2.start(view)  # 태스크 시작

    embed = await view.create_embed()
    view.message = await ctx.send(embed=embed, view=view)
    view_update2.start(view)  # 태스크 시작

@tasks.loop(seconds=60)
async def view_update2(view: CoinView1):
    if view.last_interaction:  # 마지막 상호작용이 있을 때만 업데이트
        await view.update_message(view.last_interaction)

class CoinView(disnake.ui.View):
    def __init__(self, coins, per_page=5):
        super().__init__(timeout=None)
        self.coins = coins
        self.per_page = per_page
        self.current_page = 0
        self.max_page = (len(coins) - 1) // per_page
        self.message = None

        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        if self.current_page > 0:
            self.add_item(PreviousButton())
        if self.current_page < self.max_page:
            self.add_item(NextButton())

    async def update_message(self, ctx=None):
        embed = await self.create_embed()
        self.update_buttons()
        if ctx:
            await ctx.followup.edit_message(embed=embed, view=self)
        elif self.message:
            await self.message.edit(embed=embed, view=self)

    async def create_embed(self):  
        embed = disnake.Embed(title="가상화폐 목록", color=0x00ff00)
        start = self.current_page * self.per_page
        end = start + self.per_page
        total_value = 0  

        for name, count in self.coins[start:end]:
            coin_price = next((price for coin_name, price in await getcoin() if coin_name == name), None)
            if coin_price is None:
                embed.add_field(name=name, value=f"{count}개 (현재 가격 정보를 가져오지 못했습니다.)", inline=False)
            else:
                total_value += coin_price * count
                embed.add_field(name=name, value=f"가격: {coin_price:,} 원 | 보유 수량: {count:,}개", inline=False)

        embed.add_field(name="", value=f"📄 페이지 {self.current_page + 1}/{self.max_page + 1}", inline=False)
        return embed

class PreviousButton(disnake.ui.Button):
    def __init__(self):
        super().__init__(label="이전", style=disnake.ButtonStyle.primary)

    async def callback(self, ctx: disnake.Interaction):
        view: CoinView = self.view
        if view.current_page > 0:
            view.current_page -= 1
            await view.update_message(ctx)

class NextButton(disnake.ui.Button):
    def __init__(self):
        super().__init__(label="다음", style=disnake.ButtonStyle.primary)

    async def callback(self, ctx: disnake.Interaction):
        view: CoinView = self.view
        if view.current_page < view.max_page:
            view.current_page += 1
            await view.update_message(ctx)

@bot.slash_command(name="코인지갑", description="보유중인 가상화폐를 확인합니다.")
async def coin_wallet(ctx):
    if not await tos(ctx):
        return
    await ctx.response.defer()
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "가상화폐통장", None)
    if not await member_status(ctx):
        return
    coins = await getuser_coin(ctx.author.id)

    # 사용자 이름 가져오기
    user_name = ctx.author.name

    embed = disnake.Embed(title=f"{user_name}의 가상화폐통장 💰", color=0x00ff00)

    if not coins:
        embed.add_field(name="❌ 오류", value="보유하고 있는 가상화폐가 없습니다.")
        await ctx.send(embed=embed)
    else:
        # 가상화폐 정보를 담고 있는 CoinView 생성
        view = CoinView(coins)

        # 초기 임베드 생성 및 메시지 전송
        view.message = await ctx.send(embed=await view.create_embed(), view=view)

@bot.slash_command(name="코인거래", description="가상화폐를 구매 또는 판매할 수 있습니다.")
async def coin_trading(ctx, _name: str = commands.Param(name="이름"), choice: str = commands.Param(name="선택", choices=["구매", "판매"]), _count: int = commands.Param(name="개수")):
    if not await tos(ctx):
        return
    await ctx.response.defer()
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "가상화폐거래", f"{_name}, {choice}, {_count}")
    if not await member_status(ctx):
        return
    
    embed = disnake.Embed(color=0x00ff00)
    
    try:
        # 음수 거래 방지
        if _count <= 0:
            raise ValueError("거래할 가상화폐 수량은 1개 이상이어야 합니다.")

        coins = await getcoin()
        coin_info = next((price for name, price in coins if name == _name), None)

        if coin_info is None:
            raise ValueError(f"{_name} 가상화폐는 존재하지 않습니다.")
        else:
            coin_price = coin_info

        total_price = coin_price * _count
        
        if choice == "구매":
            await adduser_coin(ctx.author.id, _name, _count)
            embed.title = "가상화폐 구매 완료"
            embed.add_field(name="가상화폐 이름", value=_name, inline=False)
            embed.add_field(name="구매 수량", value=f"{_count:,}개", inline=False)
            await add_exp(ctx.author.id, round((total_price * 0.5) / 1000))
            embed.add_field(name="총 구매 가격", value=f"{total_price:,}원", inline=False)

        elif choice == "판매":
            await removeuser_coin(ctx.author.id, _name, _count)
            embed.title = "가상화폐 판매 완료"
            embed.add_field(name="가상화폐 이름", value=_name, inline=False)
            embed.add_field(name="판매 수량", value=f"{_count:,}개", inline=False)
            await add_exp(ctx.author.id, round((total_price * 0.5) / 1000))
            embed.add_field(name="총 판매 가격", value=f"{total_price:,}원", inline=False)

        await ctx.send(embed=embed)
    except ValueError as e:
        embed = disnake.Embed(color=0xff0000)
        embed.add_field(name="❌ 오류", value=str(e))
        await ctx.send(embed=embed)

class StockView1(disnake.ui.View):
    def __init__(self, data, per_page=5):
        super().__init__(timeout=None)
        self.data = data
        self.per_page = per_page
        self.current_page = 0
        self.max_page = (len(data) - 1) // per_page
        self.message = None
        self.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        if self.current_page > 0:
            self.add_item(PreviousButton())
        if self.current_page < self.max_page:
            self.add_item(NextButton())

    async def update_message(self, interaction):
        embed = await self.create_embed()
        self.update_buttons()
        await interaction.response.edit_message(embed=embed, view=self)

    async def create_embed(self):
        embed = disnake.Embed(title="주식목록", color=0x00ff00)
        start = self.current_page * self.per_page
        end = start + self.per_page
        for name, price in self.data[start:end]:
            embed.add_field(name=name, value=f"{price:,}원", inline=False)
        embed.set_footer(text=f"페이지 {self.current_page + 1}/{self.max_page + 1} | 마지막 업데이트: {self.last_updated}")
        return embed

class PreviousButton(disnake.ui.Button):
    def __init__(self):
        super().__init__(label="이전", style=disnake.ButtonStyle.primary)

    async def callback(self, interaction: disnake.MessageInteraction):
        view: StockView1 = self.view
        view.current_page -= 1
        await view.update_message(interaction)

class NextButton(disnake.ui.Button):
    def __init__(self):
        super().__init__(label="다음", style=disnake.ButtonStyle.primary)

    async def callback(self, interaction: disnake.MessageInteraction):
        view: StockView1 = self.view
        view.current_page += 1
        await view.update_message(interaction)

@bot.slash_command(name="주식목록", description="상장된 주식을 확인합니다.")
async def stock_list(ctx):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "주식목록", None)
    data = await getstock()
    view = StockView1(data)
    embed = await view.create_embed()
    view.message = await ctx.send(embed=embed, view=view)

@tasks.loop(seconds=20)
async def view_update1(view:StockView1):
    view.data = await getstock()
    view.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    await view.update_message()

class StockView(disnake.ui.View):
    def __init__(self, stocks, per_page=5):
        super().__init__(timeout=None)
        self.stocks = stocks
        self.per_page = per_page
        self.current_page = 0
        self.max_page = (len(stocks) - 1) // per_page
        self.message = None

        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        if self.current_page > 0:
            self.add_item(PreviousButton())
        if self.current_page < self.max_page:
            self.add_item(NextButton())

    async def update_message(self, ctx=None):
        embed = await self.create_embed()  # 비동기 함수 호출
        self.update_buttons()
        if ctx:
            await ctx.followup.edit_message(embed=embed, view=self)
        elif self.message:
            await self.message.edit(embed=embed, view=self)

    async def create_embed(self):  # 비동기 함수로 변경
        embed = disnake.Embed(title="주식통장 💰", color=0x00ff00)
        start = self.current_page * self.per_page
        end = start + self.per_page

        for name, count in self.stocks[start:end]:
            stock_price = await get_stock_price(name)  # 주식 가격 가져오기
            if stock_price is None:
                embed.add_field(name=name, value=f"{count}개 (현재 가격 정보를 가져오지 못했습니다.)", inline=False)
            else:
                embed.add_field(name=name, value=f"가격: {stock_price:,} 원 | 보유 수량: {count:,}개", inline=False)

        embed.add_field(name="", value=f"📄 페이지 {self.current_page + 1}/{self.max_page + 1}", inline=False)

        return embed

async def get_stock_data(stock_name):
    # 데이터베이스에 연결
    db_path = os.path.join('system_database', 'economy.db')
    async with aiosqlite.connect(db_path) as conn:
        async with conn.cursor() as cursor:
            # 주식 정보를 가져오는 쿼리 실행
            await cursor.execute("SELECT price FROM stock WHERE stock_name = ?", (stock_name,))
            result = await cursor.fetchone()
            
            if result:
                return result[0]  # 가격 반환
            else:
                return None  # 주식이 없으면 None 반환

async def get_stock_price(stock_name):
    # 주식 심볼을 대문자로 변환
    stock_symbol = stock_name.upper()
    
    # 데이터베이스에서 주식 가격 가져오기
    stock_price = await get_stock_data(stock_symbol)  # 비동기 호출로 변경
    
    return stock_price  # 주식 가격 반환

async def getuser_stock(user_id):
    # 사용자 ID로 주식 정보를 가져오는 쿼리 실행
    db_path = os.path.join('system_database', 'economy.db')
    async with aiosqlite.connect(db_path) as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT stock_name, count FROM user_stock WHERE id = ?", (user_id,))
            stocks = await cursor.fetchall()
            return stocks if stocks else None  # 주식이 없으면 None 반환

@bot.slash_command(name="주식통장", description="보유중인 주식을 확인합니다.")
async def stock_wallet(ctx):
    if not await tos(ctx):
        return
    await ctx.response.defer()
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "주식통장", None)
    if not await member_status(ctx):
        return

    stocks = await getuser_stock(ctx.author.id)

    user_name = ctx.author.name

    if not stocks:
        embed = disnake.Embed(title=f"{user_name}의 주식통장 💰", color=0x00ff00)
        embed.add_field(name="❌ 오류", value="보유하고 있는 주식이 없습니다.")
        embed.add_field(name="💵 총 가격", value="0 원", inline=False)
        await ctx.send(embed=embed)
    else:
        view = StockView(stocks)
        view.message = await ctx.send(embed=await view.create_embed(), view=view)

@bot.slash_command(name="주식거래", description="주식을 구매 또는 판매할 수 있습니다.")
async def stock_trading(ctx, _name: str = commands.Param(name="이름"), choice: str = commands.Param(name="선택", choices=["구매", "판매"]), _count: int = commands.Param(name="개수")):
    if not await tos(ctx):
        return
    await ctx.response.defer()
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "주식거래", f"{_name}, {choice}, {_count}")
    if not await member_status(ctx):
        return
    
    embed = disnake.Embed(color=0x00ff00)
    
    try:
        # 음수 거래 방지
        if _count <= 0:
            raise ValueError("거래할 주식 수량은 1개 이상이어야 합니다.")

        stocks = await getstock()
        stock_info = next((price for name, price in stocks if name == _name), None)

        if stock_info is None:
            raise ValueError(f"{_name} 주식은 존재하지 않습니다.")
        else:
            stock_price = stock_info

        total_price = stock_price * _count
        
        if choice == "구매":
            await adduser_stock(ctx.author.id, _name, _count)
            embed.title = "주식 구매 완료"
            embed.add_field(name="주식 이름", value=_name, inline=False)
            embed.add_field(name="구매 수량", value=f"{_count:,}개", inline=False)
            await add_exp(ctx.author.id, round((total_price * 0.5) / 1000))
            embed.add_field(name="총 구매 가격", value=f"{total_price:,}원", inline=False)

        elif choice == "판매":
            await removeuser_stock(ctx.author.id, _name, _count)
            embed.title = "주식 판매 완료"
            embed.add_field(name="주식 이름", value=_name, inline=False)
            embed.add_field(name="판매 수량", value=f"{_count:,}개", inline=False)
            await add_exp(ctx.author.id, round((total_price * 0.5) / 1000))
            embed.add_field(name="총 판매 가격", value=f"{total_price:,}원", inline=False)

        await ctx.send(embed=embed)
    except ValueError as e:
        embed = disnake.Embed(color=0xff0000)
        embed.add_field(name="❌ 오류", value=str(e))
        await ctx.send(embed=embed)

@bot.slash_command(name="서버설정_채널", description="채널설정(로그채널 및 기타채널을 설정합니다) [관리자전용]")
async def server_set(ctx, kind: str = commands.Param(name="종류", choices=["공지채널", "처벌로그", "입장로그", "퇴장로그", "인증채널"]), channel: disnake.TextChannel = commands.Param(name="채널")):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "서버설정_채널", f"{kind}, {channel}")
    
    if ctx.author.guild_permissions.manage_messages:
        try:
            embed = await handle_database(ctx, kind, channel.id)
            await ctx.send(embed=embed)
        except Exception as e:
            embed = disnake.Embed(color=embederrorcolor)
            embed.add_field(name="오류 발생", value=f"데이터베이스 연결 중 오류가 발생했습니다: {e}")
            await ctx.send(embed=embed)
    else:
        embed = disnake.Embed(color=embederrorcolor)
        embed.add_field(name="❌ 오류", value="관리자만 실행 가능한 명령어입니다.")
        await ctx.send(embed=embed, ephemeral=True)

@bot.slash_command(name="서버설정_역할", description="역할설정(인증역할 및 기타역할을 설정합니다) [관리자전용]")
async def server_set_role(ctx, kind: str = commands.Param(name="종류", choices=["인증역할"]), role: disnake.Role = commands.Param(name="역할")):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "서버설정_역할", f"{kind}, {role}")
    
    if ctx.author.guild_permissions.manage_messages:
        try:
            embed = await handle_database(ctx, kind, role.id, is_role=True)
            await ctx.send(embed=embed)
        except Exception as e:
            embed = disnake.Embed(color=embederrorcolor)
            embed.add_field(name="오류 발생", value=f"데이터베이스 연결 중 오류가 발생했습니다: {e}")
            await ctx.send(embed=embed)
    else:
        embed = disnake.Embed(color=embederrorcolor)
        embed.add_field(name="❌ 오류", value="관리자만 실행 가능한 명령어입니다.")
        await ctx.send(embed=embed, ephemeral=True)

@bot.slash_command(name="서버정보", description="설정되있는 로그채널을 확인할수있습니다. [관리자전용]")
async def server_info(ctx):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "서버정보", None)
    if ctx.author.guild_permissions.manage_messages:
        db_path = os.path.join(os.getcwd(), "database", f"{ctx.guild.id}.db")
        if not os.path.exists(db_path):
            await database_create(ctx)
        aiodb = await aiosqlite.connect(db_path)
        aiocursor = await aiodb.execute("SELECT * FROM 설정")
        dat = await aiocursor.fetchone()
        await aiocursor.close()
        embed = disnake.Embed(title="서버설정", color=embedcolor)
        
        if dat:
            # 공지 채널
            if dat[0] is not None:
                announcement_channel = ctx.guild.get_channel(int(dat[0]))
                if announcement_channel:  # 채널이 존재하는지 확인
                    embed.add_field(name="공지채널", value=f"<#{announcement_channel.id}>", inline=False)
                else:
                    embed.add_field(name="공지채널", value="채널을 찾을 수 없음", inline=False)
            else:
                embed.add_field(name="공지채널", value="설정되지 않음", inline=False)

            # 처벌 로그 채널
            if dat[1] is not None:
                punishment_log_channel = ctx.guild.get_channel(int(dat[1]))
                if punishment_log_channel:
                    embed.add_field(name="처벌로그", value=f"<#{punishment_log_channel.id}>", inline=False)
                else:
                    embed.add_field(name="처벌로그", value="채널을 찾을 수 없음", inline=False)
            else:
                embed.add_field(name="처벌로그", value="설정되지 않음", inline=False)

            # 입장 로그 채널
            if dat[2] is not None:
                entry_log_channel = ctx.guild.get_channel(int(dat[2]))
                if entry_log_channel:
                    embed.add_field(name="입장로그", value=f"<#{entry_log_channel.id}>", inline=False)
                else:
                    embed.add_field(name="입장로그", value="채널을 찾을 수 없음", inline=False)
            else:
                embed.add_field(name="입장로그", value="설정되지 않음", inline=False)

            # 퇴장 로그 채널
            if dat[3] is not None:
                exit_log_channel = ctx.guild.get_channel(int(dat[3]))
                if exit_log_channel:
                    embed.add_field(name="퇴장로그", value=f"<#{exit_log_channel.id}>", inline=False)
                else:
                    embed.add_field(name="퇴장로그", value="채널을 찾을 수 없음", inline=False)
            else:
                embed.add_field(name="퇴장로그", value="설정되지 않음", inline=False)

            # 인증 역할
            if dat[4] is not None:
                auth_role = ctx.guild.get_role(int(dat[4]))
                if auth_role:
                    embed.add_field(name="인증역할", value=f"<@&{auth_role.id}>", inline=False)
                else:
                    embed.add_field(name="인증역할", value="역할을 찾을 수 없음", inline=False)
            else:
                embed.add_field(name="인증역할", value="설정되지 않음", inline=False)

            # 인증 채널
            if dat[5] is not None:
                exit_log_channel = ctx.guild.get_channel(int(dat[5]))
                if exit_log_channel:
                    embed.add_field(name="인증채널", value=f"<#{exit_log_channel.id}>")
                else:
                    embed.add_field(name="인증채널", value="채널을 찾을 수 없음")
            else:
                embed.add_field(name="인증채널", value="설정되지 않음")
        
        await ctx.send(embed=embed)
    else:
        embed = disnake.Embed(color=embederrorcolor)
        embed.add_field(name="❌ 오류", value="관리자만 실행가능한 명령어입니다.")
        await ctx.send(embed=embed, ephemeral=True)

@bot.slash_command(name="정보", description="봇의 실시간 상태와 정보를 알 수 있습니다.")
async def bot_info(ctx):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "정보", None)

    # 응답 지연
    await ctx.response.defer()

    # 핑 측정을 위한 웹소켓 연결 함수
    def ping_websocket():
        start_time = time.time()
        ws = None  # ws 변수를 None으로 초기화
        try:
            ws = websocket.create_connection("wss://gateway.discord.gg/?v=9&encoding=json")  # Discord Gateway URL
            ws.send('{"op": 1, "d": null}')  # Ping 요청
            ws.recv()  # 응답 대기
            end_time = time.time()
            return (end_time - start_time) * 1000  # 밀리초로 변환
        except Exception as e:
            print(f"웹소켓 오류: {e}")
            return None
        finally:
            if ws is not None:
                ws.close()

    # ThreadPoolExecutor를 사용하여 웹소켓 핑 측정
    with ThreadPoolExecutor() as executor:
        ping_time = await bot.loop.run_in_executor(executor, ping_websocket)

    if ping_time is None:
        ping_time = float('inf')  # 핑 측정 실패 시 최대값으로 설정

    # 응답 시간에 따라 임베드 색상 및 메시지 결정
    if ping_time < 100:
        embed_color = 0x00ff00  # 초록색 (좋음)
        status = "응답 속도가 매우 좋습니다! 🚀"
    elif ping_time < 300:
        embed_color = 0xffff00  # 노란색 (보통)
        status = "응답 속도가 좋습니다! 😊"
    elif ping_time < 1000:
        embed_color = 0xffa500  # 주황색 (나쁨)
        status = "응답 속도가 느립니다. 😕"
    else:
        embed_color = 0xff0000  # 빨간색 (매우 나쁨)
        status = "응답 속도가 매우 느립니다! ⚠️"

    total_members = 0  # 총 유저 수 초기화

    # 봇이 참여하고 있는 모든 서버를 반복
    for guild in bot.guilds:
        total_members += guild.member_count  # 각 서버의 멤버 수를 누적
    
    embed = disnake.Embed(title="봇 정보", color=embed_color)
    embed.add_field(name="서버수", value=f"{len(bot.guilds)}", inline=True)
    embed.add_field(name="유저수", value=f"{total_members:,}", inline=True)
    embed.add_field(name="샤드수", value=f"{bot.shard_count}", inline=True)
    embed.add_field(name="", value="", inline=False)
    embed.add_field(name="업타임", value=f"{get_uptime()}", inline=True)
    embed.add_field(name="개발자", value=f"{sec.developer_name}", inline=True)

    # CPU 정보 불러오기
    uname_info = platform.uname()
    memory_info = psutil.virtual_memory()

    total_memory = f"{memory_info.total / (1024 ** 3):.2f}"
    used_memory = f"{memory_info.used / (1024 ** 3):.2f}"
    percent_memory = memory_info.percent

    # 서버 시간
    server_date = datetime.now()
    embed.add_field(name="시스템 정보", value=f"```python {platform.python_version()}\ndiscord.py {version('discord.py')}\ndisnake {version('disnake')}\nCPU : {cpu_info['brand_raw']}\nOS : {uname_info.system} {uname_info.release}\nMemory : {used_memory}GB / {total_memory}GB ({percent_memory}%)```\n응답속도 : {int(ping_time)}ms / {status}\n{server_date.strftime('%Y년 %m월 %d일 %p %I:%M').replace('AM', '오전').replace('PM', '오후')}", inline=False)

    # 링크 버튼 추가
    support_button = Button(label="서포트 서버", url=sec.support_server_url, style=ButtonStyle.url)
    docs_button = Button(label="하트 누르기", url=f"https://koreanbots.dev/bots/{bot.user.id}/vote", style=ButtonStyle.url)  # 여기에 원하는 URL을 넣으세요.

    view = disnake.ui.View()
    view.add_item(support_button)
    view.add_item(docs_button)

    # 응답 전송
    await ctx.edit_original_response(embed=embed, view=view)

@bot.slash_command(name="슬로우모드", description="채팅방에 슬로우모드를 적용합니다. [관리자전용]")
async def slowmode(ctx, time: int = commands.Param(name="시간", description="시간(초)")):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "슬로우모드", f"{time}")
    if ctx.author.guild_permissions.manage_messages:
        if time == 0:
            embed = disnake.Embed(title="\✅슬로우모드를 껐어요.", color=embedsuccess)
            await ctx.send(embed=embed)
            await ctx.channel.edit(slowmode_delay=0)
            return
        elif time > 21600:
            embed = disnake.Embed(title="\❌슬로우모드를 6시간 이상 설정할수 없어요.", color=embederrorcolor)
            await ctx.send(embed=embed, ephemeral=True)
            return
        else:
            await ctx.channel.edit(slowmode_delay=time)
            embed = disnake.Embed(title=f"\✅ 성공적으로 슬로우모드를 {time}초로 설정했어요.", color=embedsuccess)
            await ctx.send(embed=embed)
    else:
        embed=disnake.Embed(color=embederrorcolor)
        embed.add_field(name="❌ 오류", value="관리자만 실행가능한 명령어입니다.")
        await ctx.send(embed=embed, ephemeral=True)

@bot.slash_command(name="청소", description="메시지를 삭제합니다. [관리자전용]")
async def clear(ctx, num: int = commands.Param(name="개수")):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return

    await command_use_log(ctx, "청소", f"{num}")
    await ctx.response.defer()  # 응답 지연

    if ctx.author.guild_permissions.manage_messages:
        try:
            num = int(num)
            if num <= 0 or num > 100:
                embed = disnake.Embed(color=embederrorcolor)
                embed.add_field(name="❌ 오류", value="삭제할 메시지 수는 1 이상 100 이하이어야 합니다.")
                await ctx.send(embed=embed)
            
            deleted_messages = await ctx.channel.purge(limit=num)
            await asyncio.sleep(3)
            embed = disnake.Embed(color=embedsuccess)
            embed.add_field(name=f"{len(deleted_messages)}개의 메시지를 지웠습니다.", value="")
            await ctx.send(embed=embed)  # 응답 전송
        except ValueError as ve:
            embed = disnake.Embed(color=embederrorcolor)
            embed.add_field(name="❌ 오류", value=str(ve))
            await ctx.send(embed=embed)  # 응답 전송
        except disnake.NotFound:
            embed = disnake.Embed(color=embederrorcolor)
            embed.add_field(name="❌ 오류", value="삭제할 메시지를 찾을 수 없습니다.")
            await ctx.send(embed=embed)  # 응답 전송
        except Exception:
            embed = disnake.Embed(color=embederrorcolor)
            embed.add_field(name="❌ 오류", value="메시지 삭제에 실패했습니다.")
            await ctx.send(embed=embed)  # 응답 전송
    else:
        embed = disnake.Embed(color=embederrorcolor)
        embed.add_field(name="❌ 오류", value="관리자만 실행가능한 명령어입니다.")
        await ctx.send(embed=embed)  # 응답 전송

@bot.slash_command(name="공지", description="서버에 공지를 전송합니다. [관리자전용]")
async def notification(ctx, content: str = commands.Param(name="내용")):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "공지", f"{content}")
    if ctx.author.guild_permissions.manage_messages:
        db_path = os.path.join(os.getcwd(), "database", f"{ctx.guild.id}.db")
        if not os.path.exists(db_path):
            await database_create(ctx)
        else:
            aiodb = await aiosqlite.connect(db_path)
            aiocursor = await aiodb.execute("SELECT 공지채널 FROM 설정")
            설정_result = await aiocursor.fetchone()
            await aiocursor.close()
            
            if 설정_result:
                공지채널_id = 설정_result[0]
                공지채널 = bot.get_channel(공지채널_id)
            
            if 공지채널:
                for guild in bot.guilds:
                    server_remove_date = datetime.now()
                    embed1 = disnake.Embed(title=f"{guild.name} 공지", description=f"```{content}```", color=embedcolor)
                    embed1.set_footer(text=f'To. {ctx.author.display_name}\n{server_remove_date.strftime("전송시간 %Y년 %m월 %d일 %p %I:%M").replace("AM", "오전").replace("PM", "오후")}')
                    try:
                        chan = guild.get_channel(공지채널_id)
                        if chan and chan.permissions_for(guild.me).send_messages:
                            await chan.send(embed=embed1)
                    except Exception as e:
                        print(f"Error sending message to {guild.name}: {e}")  # 예외 로그 추가
            else:
                embed = disnake.Embed(title="오류", description="공지채널이 없습니다.\n공지채널을 설정해주세요.")
                await ctx.send(embed=embed)  # 오류 메시지 전송

            embed = disnake.Embed(title="공지 업로드 완료!", color=embedsuccess)
            await ctx.send(embed=embed)
    else:
        embed = disnake.Embed(color=embederrorcolor)
        embed.add_field(name="❌ 오류", value="관리자만 실행가능한 명령어입니다.")
        await ctx.send(embed=embed, ephemeral=True)

@bot.slash_command(name="타임아웃", description="유저의 채팅을 제한합니다. [관리자전용]")
async def timeout(ctx, user: disnake.Member = commands.Param(name="유저"), duration: int = commands.Param(name="시간_분"), reason: str = commands.Param(name="사유", default=None)):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "타임아웃", f"{user}, {duration}, {reason}")
    if ctx.author.guild_permissions.moderate_members:
        try:
            if duration > 10080:  # 7일을 분으로 환산
                embed = disnake.Embed(title="❌ 타임아웃 실패", color=embederrorcolor)
                embed.add_field(name="오류", value="타임아웃 시간은 최대 7일(10080분)까지 설정할 수 있습니다.")
                await ctx.send(embed=embed)
                return

            await user.timeout(duration=duration*60, reason=reason)  # 분을 초로 변환
            embed = disnake.Embed(title="✅ 타임아웃 완료", color=embedsuccess)
            embed.add_field(name="대상", value=f"{user.mention}")
            embed.add_field(name="시간", value=f"{duration}분")
            embed.add_field(name="사유", value=f"{reason}", inline=False)
            await ctx.send(embed=embed)
        except Exception as e:
            embed = disnake.Embed(title="❌ 타임아웃 실패", color=embederrorcolor)
            embed.add_field(name="오류", value=str(e))
            await ctx.send(embed=embed)
    else:
        embed = disnake.Embed(color=embederrorcolor)
        embed.add_field(name="❌ 오류", value="관리자만 실행 가능한 명령어입니다.")
        await ctx.send(embed=embed, ephemeral=True)

@bot.slash_command(name="타임아웃해제", description="유저의 채팅 제한을 해제합니다. [관리자전용]")
async def timeout_release(ctx, user: disnake.Member = commands.Param(name="유저"), reason: str = commands.Param(name="사유", default=None)):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "타임아웃해제", f"{user}, {reason}")
    if ctx.author.guild_permissions.moderate_members:
        try:
            await user.timeout(duration=None, reason=reason)
            embed = disnake.Embed(title="✅ 타임아웃 해제 완료", color=embedsuccess)
            embed.add_field(name="대상", value=f"{user.mention}")
            embed.add_field(name="사유", value=f"{reason}", inline=False)
            await ctx.send(embed=embed)
        except Exception as e:
            embed = disnake.Embed(title="❌ 타임아웃 해제 실패", color=embederrorcolor)
            embed.add_field(name="오류", value=str(e))
            await ctx.send(embed=embed)
    else:
        embed = disnake.Embed(color=embederrorcolor)
        embed.add_field(name="❌ 오류", value="관리자만 실행 가능한 명령어입니다.")
        await ctx.send(embed=embed, ephemeral=True)

@bot.slash_command(name="추방", description="유저를 추방합니다. [관리자전용]")
async def kick(ctx, user: disnake.Member = commands.Param(name="유저"), reason: str = commands.Param(name="사유", default=None)):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "추방", f"{user}, {reason}")
    if ctx.author.guild_permissions.kick_members:
        try:
            await ctx.guild.kick(user)
        except:
            embed = disnake.Embed(title=f"{user.name}를 추방하기엔 권한이 부족해요...", color=embederrorcolor)
            await ctx.send(embed=embed)
        else:
            embed = disnake.Embed(title="✅추방을 완료했어요", color=embedsuccess)
            embed.add_field(name="대상", value=f"{user.mention}")
            embed.add_field(name="사유", value=f"{reason}", inline=False)
            await ctx.send(embed=embed)
            db_path = os.path.join(os.getcwd(), "database", f"{ctx.guild.id}.db")
            if not os.path.exists(db_path):
                await database_create(ctx)
            aiodb = await aiosqlite.connect(db_path)
            aiocursor = await aiodb.execute("select * from 설정 order by 공지채널 desc")
            dat = await aiocursor.fetchone()
            await aiocursor.close()
            aiocursor = await aiodb.execute("SELECT 처벌로그 FROM 설정")
            설정_result = await aiocursor.fetchone()
            await aiocursor.close()
            if 설정_result:
                경고채널_id = 설정_result[0]
                경고채널 = bot.get_channel(경고채널_id)
                if 경고채널:
                    embed = disnake.Embed(title="추방", color=embederrorcolor)
                    embed.add_field(name="관리자", value=f"{ctx.author.mention}")
                    embed.add_field(name="대상", value=f"{user.mention}")
                    embed.add_field(name="사유", value=f"{reason}", inline=False)
                    await ctx.send(embed=embed)
                else:
                    await ctx.send("경고채널을 찾을 수 없습니다.")
                    embed
            else:
                await ctx.send("경고채널이 설정되지 않았습니다.")
    else:
        embed=disnake.Embed(color=embederrorcolor)
        embed.add_field(name="❌ 오류", value="관리자만 실행가능한 명령어입니다.")
        await ctx.send(embed=embed, ephemeral=True)

@bot.slash_command(name="차단", description="유저를 차단합니다. [관리자전용]")
async def ban(ctx, user: disnake.Member = commands.Param(description="유저"), reason: str = commands.Param(name="사유", default=None)):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "차단", f"{user}, {reason}")
    if ctx.author.guild_permissions.ban_members:
        try:
            await ctx.guild.ban(user)
        except:
            embed = disnake.Embed(title=f"{user.name}를 차단하기엔 권한이 부족해요...", color=embederrorcolor)
            await ctx.send(embed=embed, ephemeral=True)
        else:
            embed = disnake.Embed(title="차단", color=embederrorcolor)
            embed.add_field(name="관리자", value=f"{ctx.author.mention}")
            embed.add_field(name="대상", value=f"{user.mention}")
            embed.add_field(name="사유", value=f"{reason}", inline=False)
            await ctx.send(embed=embed)
    else:
        embed=disnake.Embed(color=embederrorcolor)
        embed.add_field(name="❌ 오류", value="관리자만 실행가능한 명령어입니다.")
        await ctx.send(embed=embed, ephemeral=True)

@bot.slash_command(name="경고확인", description="보유중인 경고를 확인합니다.")
async def warning_check(ctx, user: disnake.Member = commands.Param(name="유저", default=None)):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "경고확인", f"{user}")
    max_warning = 10
    if user is None:
        user = ctx.author
    dat, accumulatewarn = await getwarn(ctx, user)
    
    if not dat:
        embed = disnake.Embed(color=embederrorcolor)
        embed.add_field(name="확인된 경고가 없습니다.", value="")
        await ctx.send(embed=embed)
    else:
        embed = disnake.Embed(title=f"{user.name}님의 경고 리스트", color=embedcolor)
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name=f"누적경고 : {accumulatewarn} / {max_warning}", value="", inline=False)
        for i in dat:
            embed.add_field(name=f"경고 #{i[0]}", value=f"경고수: {i[3]}\n사유: {i[4]}", inline=False)
        await ctx.send(embed=embed)

@bot.slash_command(name="경고", description="유저에게 경고를 지급합니다. [관리자전용]")
async def warning(ctx, user: disnake.Member, warn_num: int = None, reason: str = None):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "경고", f"{user}, {warn_num}, {reason}")
    max_warning = 10
    if ctx.author.guild_permissions.manage_messages:
        if warn_num is None:
            warn_num = "1"
        if reason is None:
            reason = "없음"
        new_id, accumulatewarn, 설정_result = await addwarn(ctx, user, warn_num, reason)
        if 설정_result:
            경고채널_id = 설정_result[0]
            경고채널 = bot.get_channel(경고채널_id)
            if 경고채널:
                embed = disnake.Embed(title=f"#{new_id} - 경고", color=embederrorcolor)
                embed.add_field(name="관리자", value=ctx.author.mention, inline=False)
                embed.add_field(name="대상", value=user.mention, inline=False)
                embed.add_field(name="사유", value=reason, inline=False)
                embed.add_field(name="누적 경고", value=f"{accumulatewarn} / {max_warning} (+ {warn_num})", inline=False)
                await 경고채널.send(embed=embed)
            else:
                await ctx.send("경고채널을 찾을 수 없습니다.")
        else:
            await ctx.send("경고채널이 설정되지 않았습니다.")
    else:
        embed=disnake.Embed(color=embederrorcolor)
        embed.add_field(name="❌ 오류", value="관리자만 실행가능한 명령어입니다.")
        await ctx.send(embed=embed, ephemeral=True)

@bot.slash_command(name="경고취소", description="지급한 경고를 취소합니다. [관리자전용]")
async def warning_cancel(ctx, warn_id: int, reason: str = None):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "경고취소", f"{warn_id}, {reason}")
    if ctx.author.guild_permissions.manage_messages:
        if reason is None:
            reason = "없음"
        warn_id = await removewarn(ctx, warn_id)
        if warn_id is None:
            embed = disnake.Embed(color=embederrorcolor)
            embed.add_field(name="이미 취소되었거나 없는 경고입니다.", value="")
            await ctx.send(embed=embed)
        else:
            await aiocursor.execute("DELETE FROM 경고 WHERE 아이디 = ?", (warn_id,))
            await aiodb.commit()  # 변경 사항을 데이터베이스에 확정합니다.
            embed = disnake.Embed(color=embedsuccess)
            embed.add_field(name=f"경고 #{warn_id}(이)가 취소되었습니다.", value="")
            embed.add_field(name="사유", value=reason, inline=False)
            await ctx.send(embed=embed)
            aiocursor = await aiodb.execute("SELECT 처벌로그 FROM 설정")
            set_result = await aiocursor.fetchone()
            await aiocursor.close()
            if set_result:
                warnlog_id = set_result[0]
                warnlog = bot.get_channel(warnlog_id)
                if warnlog:
                    embed = disnake.Embed(title=f"#{warn_id} - 경고 취소", color=embedwarning)
                    embed.add_field(name="관리자", value=ctx.author.mention, inline=False)
                    embed.add_field(name="사유", value=reason, inline=False)
                    await warnlog.send(embed=embed)
                else:
                    await ctx.send("경고채널을 찾을 수 없습니다.")
            else:
                await ctx.send("경고채널이 설정되지 않았습니다.")
        await aiocursor.close()
    else:
        embed=disnake.Embed(color=embederrorcolor)
        embed.add_field(name="❌ 오류", value="관리자만 실행가능한 명령어입니다.")
        await ctx.send(embed=embed, ephemeral=True)

@bot.slash_command(name="문의", description="개발자에게 문의를 보냅니다.")
async def inquire(ctx):
    if not await tos(ctx):
        return
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "문의", None)
    embed = disnake.Embed(color=embederrorcolor)
    embed.add_field(name="❌ 오류", value=f"{ctx.author.mention}, 문의는 봇 DM으로 부탁드립니다!")
    await ctx.send(embed=embed)

@bot.slash_command(name="dm설정", description="레벨업 DM 수신 상태를 설정합니다.")
async def dm_toggle(ctx, state: str = commands.Param(name="dm여부", choices=["on", "off"])):
    if not await check_permissions(ctx):
        return
    
    if not await member_status(ctx):
        return
    
    await command_use_log(ctx, "dm_toggle", f"{state}")

    db_path = os.path.join('system_database', 'economy.db')
    economy_aiodb = await aiosqlite.connect(db_path)
    async with economy_aiodb.cursor() as aiocursor:
        await aiocursor.execute("SELECT dm_on_off FROM user WHERE id=?", (ctx.author.id,))
        dbdata = await aiocursor.fetchone()

        if dbdata is not None:
            current_state = int(dbdata[0])
            if state == "on" and current_state == 1:
                embed = disnake.Embed(color=embederrorcolor)
                embed.add_field(name="❌ 오류", value="이미 DM 수신이 활성화되어 있습니다.")
            elif state == "on" and current_state == 0:
                await aiocursor.execute("UPDATE user SET dm_on_off=? WHERE id=?", (1, ctx.author.id))
                await economy_aiodb.commit()
                embed = disnake.Embed(color=embedsuccess)
                embed.add_field(name="✅ DM 수신 활성화", value="이제 DM을 수신합니다.")
            elif state == "off" and current_state == 0:
                embed = disnake.Embed(color=embederrorcolor)
                embed.add_field(name="❌ 오류", value="이미 DM 수신이 비활성화되어 있습니다.")
            elif state == "off" and current_state == 1:
                await aiocursor.execute("UPDATE user SET dm_on_off=? WHERE id=?", (0, ctx.author.id))
                await economy_aiodb.commit()
                embed = disnake.Embed(color=embedsuccess)
                embed.add_field(name="✅ DM 수신 비활성화", value="이제 DM을 수신하지 않습니다.")
        else:
            embed = disnake.Embed(color=embederrorcolor)
            embed.add_field(name="❌ 오류", value="가입이 되어있지 않습니다.")
    
    await ctx.send(embed=embed, ephemeral=True)

@bot.slash_command(name="수동추첨", description="로또를 수동으로 추첨합니다. [개발자전용]")
async def manual_lottery_draw(ctx):
    # 개발자 ID 확인
    if ctx.author.id not in developer:
        embed = disnake.Embed(color=embederrorcolor)
        embed.add_field(name="❌ 오류", value="이 명령어는 개발자만 사용할 수 있습니다.")
        await ctx.send(embed=embed)
        return
    
    await command_use_log(ctx, "수동추첨", None)
    # 자동으로 번호 생성
    winning_numbers = random.sample(range(1, 46), 6)
    bonus_number = random.choice([num for num in range(1, 46) if num not in winning_numbers])  # 보너스 번호
    winning_numbers_str = ','.join(map(str, sorted(winning_numbers)))

    # 당첨자 확인
    async with aiosqlite.connect(db_path) as db:
        async with db.execute('SELECT user_id, numbers FROM lottery') as cursor:
            winners = await cursor.fetchall()

    # 등수별 당첨자 수 초기화
    prize_counts = {
        "1등": 0,
        "2등": 0,
        "3등": 0,
        "4등": 0,
        "5등": 0,
    }

    embed = disnake.Embed(title="로또 자동 추첨 결과 (수동)", color=0x00ff00)
    embed.add_field(name="당첨 번호", value=f"{winning_numbers_str} (보너스: {bonus_number})", inline=False)

    for winner in winners:
        user_id = winner[0]
        matched_numbers = len(set(winning_numbers) & set(map(int, winner[1].split(','))))
        
        # 당첨자 수 업데이트
        if matched_numbers == 6:
            prize_counts["1등"] += 1
            rank = "1등"
        elif matched_numbers == 5 and bonus_number in map(int, winner[1].split(',')):
            prize_counts["2등"] += 1
            rank = "2등"
        elif matched_numbers == 5:
            prize_counts["3등"] += 1
            rank = "3등"
        elif matched_numbers == 4:
            prize_counts["4등"] += 1
            rank = "4등"
        elif matched_numbers == 3:
            prize_counts["5등"] += 1
            rank = "5등"
        else:
            continue  # 당첨되지 않은 경우

        # DM 전송
        prize_amount = 0
        if rank == "1등":
            prize_amount = 3000000000
        elif rank == "2등":
            prize_amount = 1500000000
        elif rank == "3등":
            prize_amount = 100000000
        elif rank == "4등":
            prize_amount = 10000000
        elif rank == "5등":
            prize_amount = 1000000
        
        if prize_amount > 0:
            user = await bot.fetch_user(user_id)
            if user:
                embed = disnake.Embed(title="🎉 축하합니다!", description=f"당신의 로또 번호가 당첨되었습니다!", color=0x00ff00)
                embed.add_field(name="등수", value=rank, inline=False)  # 올바른 등수 표시
                embed.add_field(name="상금", value=f"{prize_amount:,}원", inline=False)
                await user.send(embed=embed)

    # 등수별 당첨자 수 추가
    embed.add_field(name="당첨자 수", value=f"1등: {prize_counts['1등']}명\n2등: {prize_counts['2등']}명\n3등: {prize_counts['3등']}명\n4등: {prize_counts['4등']}명\n5등: {prize_counts['5등']}명", inline=False)

    # 특정 채널에 결과 전송
    channel = bot.get_channel(int(sec.lotto_ch_id))
    if channel:
        await channel.send(embed=embed)

    # 로또 데이터 삭제
    async with aiosqlite.connect(db_path) as db:
        await db.execute('DELETE FROM lottery')
        await db.commit()

    await ctx.send("추첨 결과가 지정된 채널에 전송되었으며, 로또 데이터가 삭제되었습니다.")

@bot.slash_command(name="돈관리", description="유저의 돈을 관리합니다. [개발자전용]")
async def money_edit(ctx, member_id: str = commands.Param(name="유저"), choice: str = commands.Param(name="선택", choices=["차감", "추가"]), money: int = commands.Param(name="돈")):
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "돈관리", f"{member_id}, {choice}, {money}")
    
    if ctx.author.id in developer:
        # 멘션 또는 ID에서 사용자 ID 추출
        user = ctx.author if member_id is None else await bot.fetch_user(member_id)
        if user is None:
            await ctx.followup.send("유효하지 않은 유저 ID입니다.", ephemeral=True)
            return

        user_data = await fetch_user_data(user.id)
        if user_data is None:
            await ctx.followup.send(f"{user.mention}, 가입되지 않은 유저입니다.", ephemeral=True)
            return

        tos_data = await fetch_tos_status(user.id)
        tos = tos_data[0] if tos_data else None

        if tos is None:
            await ctx.followup.send(f"{user.mention}, TOS 정보가 없습니다.", ephemeral=True)
            return
        if tos == 1:
            await ctx.followup.send(f"{user.mention}, 이용제한된 유저입니다.", ephemeral=True)
            return

        # 돈 차감 또는 추가
        if choice == "차감":
            if not await removemoney(user.id, money):
                return await ctx.send("그 사용자의 포인트를 마이너스로 줄 수 없어요!")
            embed = disnake.Embed(title="잔액 차감", color=embedsuccess)
            embed.add_field(name="차감 금액", value=f"{money:,}원")
            embed.add_field(name="대상", value=f"{user.mention}")
            await ctx.send(embed=embed)
        elif choice == "추가":
            await addmoney(user.id, money)
            embed = disnake.Embed(title="잔액 추가", color=embedsuccess)
            embed.add_field(name="추가 금액", value=f"{money:,}원")
            embed.add_field(name="대상", value=f"{user.mention}")
            await ctx.send(embed=embed)
        else:
            embed = disnake.Embed(color=embederrorcolor)
            embed.add_field(name="❌ 오류", value="차감 또는 추가 중 선택해주세요.")
            await ctx.send(embed=embed, ephemeral=True)
    else:
        embed = disnake.Embed(color=embederrorcolor)
        embed.add_field(name="❌ 오류", value="개발자만 실행 가능한 명령어입니다.")
        await ctx.send(embed=embed, ephemeral=True)

@bot.slash_command(name="이용제한", description="봇 이용을 제한합니다. [개발자전용]")
async def use_limit(ctx, user_id: str = commands.Param(name="아이디"), reason: str = commands.Param(name="사유", default=None)):
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "이용제한", f"{user_id}, {reason}")
    if ctx.author.id in developer:
        if reason is None:
            reason = "없음"
        db_path = os.path.join('system_database', 'economy.db')
        economy_aiodb = await aiosqlite.connect(db_path)
        aiocursor = await economy_aiodb.execute("SELECT tos FROM user WHERE id=?", (user_id,))
        dbdata = await aiocursor.fetchone()
        await aiocursor.close()
        if dbdata is not None:
            if int(dbdata[0]) == 1:
                embed=disnake.Embed(color=embederrorcolor)
                embed.add_field(name="❌ 오류", value=f"{user_id}는 이미 제한된 유저입니다.")
                await ctx.send(embed=embed)
            else:
                embed=disnake.Embed(title="✅ 이용제한", color=embederrorcolor)
                embed.add_field(name="대상", value=f"{user_id}")
                embed.add_field(name="사유", value=f"{reason}")
                await ctx.send(embed=embed)
                aiocursor = await economy_aiodb.execute("UPDATE user SET tos=? WHERE id=?", (1, user_id))
                await economy_aiodb.commit()
                await aiocursor.close()
                try:
                    user = await bot.fetch_user(user_id)
                    embed=disnake.Embed(title="이용제한", description="봇 사용이 제한되었습니다.", color=embederrorcolor)
                    embed.add_field(name="대상", value=f"{user_id}", inline=False)
                    embed.add_field(name="사유", value=f"{reason}")
                    await user.send(embed=embed)
                except disnake.Forbidden:
                    print(f"사용자 {user_id}에게 DM을 보낼 수 없습니다.")
        else:
            # user 테이블에 새로운 유저 추가
            aiocursor = await economy_aiodb.execute("INSERT INTO user (id, money, tos, level, exp, lose_money, dm_on_off, checkin) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (user_id, 0, 1, 0, 0, 0, 0, 0))
            await economy_aiodb.commit()
            await aiocursor.close()

            embed = disnake.Embed(color=embederrorcolor)
            embed.add_field(name="✅ 이용제한", value=f"{user_id}\n가입되지 않은 유저였으므로 새로 추가되었습니다.")
            await ctx.send(embed=embed)
            try:
                user = await bot.fetch_user(user_id)
                await user.send(f"이용제한: {reason}")
            except disnake.Forbidden:
                print(f"사용자 {user_id}에게 DM을 보낼 수 없습니다.")
    else:
        embed=disnake.Embed(color=embederrorcolor)
        embed.add_field(name="❌ 오류", value="개발자만 실행가능한 명령어입니다.")
        await ctx.send(embed=embed, ephemeral=True)

@bot.slash_command(name="제한해제", description="봇 이용제한을 해제합니다. [개발자전용]")
async def use_limit_release(ctx, user_id: str = commands.Param(name="아이디")):
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "제한해제", f"{user_id}")
    if ctx.author.id in developer:
        db_path = os.path.join('system_database', 'economy.db')
        economy_aiodb = await aiosqlite.connect(db_path)
        aiocursor = await economy_aiodb.execute("SELECT tos FROM user WHERE id=?", (user_id,))
        dbdata = await aiocursor.fetchone()
        await aiocursor.close()
        if dbdata is not None:
            if int(dbdata[0]) == 1:
                embed=disnake.Embed(color=embederrorcolor)
                embed.add_field(name="제한해제", value=f"{user_id} 차단이 해제되었습니다.")
                await ctx.send(embed=embed)
                aiocursor = await economy_aiodb.execute("UPDATE user SET tos=? WHERE id=?", (0, user_id))
                await economy_aiodb.commit()
                await aiocursor.close()
                try:
                    user = await bot.fetch_user(user_id)
                    embed=disnake.Embed(title="이용제한 해제", description="봇 사용 제한이 해제되었습니다.", color=embedsuccess)
                    embed.add_field(name="대상", value=f"{user_id}")
                    await user.send(embed=embed)
                except disnake.Forbidden:
                    print(f"사용자 {user_id}에게 DM을 보낼 수 없습니다.")
            else:
                embed=disnake.Embed(color=embederrorcolor)
                embed.add_field(name="❌ 오류", value=f"{user_id} 제한되지 않은 유저입니다.")
                await ctx.send(embed=embed)
        else:
            embed=disnake.Embed(color=embederrorcolor)
            embed.add_field(name="❌ 오류", value=f"{ctx.author.mention}\n가입되지 않은 유저입니다.")
            await ctx.send(embed=embed, ephemeral=True)
    else:
        embed=disnake.Embed(color=embederrorcolor)
        embed.add_field(name="❌ 오류", value="개발자만 실행가능한 명령어입니다.")
        await ctx.send(embed=embed, ephemeral=True)

@bot.slash_command(name="아이템관리", description="아이템을 추가하거나 삭제할 수 있습니다. [개발자전용]")
async def item_management(ctx, item_name: str, choice: str = commands.Param(name="선택", choices=["추가", "삭제"]), 
                          item_price: float = commands.Param(name="가격", default=None), 
                          item_damage: int = commands.Param(name="데미지", default=None), 
                          item_exp: int = commands.Param(name="경험치", default=None)):
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "아이템관리", f"{item_name}, {item_price}, {item_damage}, {item_exp}")
    if ctx.author.id in developer:
        if choice == "추가":
            await add_item(item_name, item_price, item_damage, item_exp)
            embed = disnake.Embed(color=embedsuccess)
            embed.add_field(name="✅ 성공", value=f"{item_name} 아이템을 추가하였습니다.\n가격: {item_price:,} 원\n데미지: {item_damage}\n경험치: {item_exp}")
            await ctx.send(embed=embed)
        elif choice == "삭제":
            await remove_item(item_name)
            embed = disnake.Embed(color=embederrorcolor)
            embed.add_field(name="🗑️ 삭제", value=f"{item_name} 아이템을 삭제하였습니다.")
            await ctx.send(embed=embed)
    else:
        embed = disnake.Embed(color=embederrorcolor)
        embed.add_field(name="❌ 오류", value="개발자만 실행 가능한 명령어입니다.")
        await ctx.send(embed=embed, ephemeral=True)

@bot.slash_command(name="가상화폐관리", description="가상화폐를 추가하거나 삭제할 수 있습니다. [개발자전용]")
async def coin_management(ctx, _name: str, choice: str = commands.Param(name="선택", choices=["추가", "삭제"]), 
                          _price: float = commands.Param(name="가격", default=None)):
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "가상화폐관리", f"{_name}, {_price}")
    
    if ctx.author.id in developer:
        try:
            if choice == "추가":
                await addcoin(_name, _price)
                embed = disnake.Embed(color=embedsuccess)
                embed.add_field(name="✅ 성공", value=f"{_name} 가상화폐를 {_price:,} 가격으로 추가하였습니다.")
                await ctx.response.send_message(embed=embed)
            elif choice == "삭제":
                await removecoin(_name)
                embed = disnake.Embed(color=embederrorcolor)
                embed.add_field(name="🗑️ 삭제", value=f"{_name} 가상화폐를 삭제하였습니다.")
                await ctx.response.send_message(embed=embed)
        except Exception as e:
            embed = disnake.Embed(color=embederrorcolor)
            embed.add_field(name="❌ 오류", value=f"오류가 발생했습니다: {str(e)}")
            await ctx.response.send_message(embed=embed, ephemeral=True)
    else:
        embed = disnake.Embed(color=embederrorcolor)
        embed.add_field(name="❌ 오류", value="개발자만 실행 가능한 명령어입니다.")
        await ctx.response.send_message(embed=embed, ephemeral=True)

@bot.slash_command(name="주식관리", description="주식을 추가하거나 삭제할 수 있습니다. [개발자전용]")
async def stock_management(ctx, _name: str, choice: str = commands.Param(name="선택", choices=["추가", "삭제"]), 
                           _price: float = commands.Param(name="가격", default=None)):
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "주식관리", f"{_name}, {_price}")
    if ctx.author.id in developer:
        if choice == "추가":
            await addstock(_name, _price)
            price = int(_price)
            embed = disnake.Embed(color=embedsuccess)
            embed.add_field(name="✅ 성공", value=f"{_name} 주식을 {price:,} 가격으로 추가하였습니다.")
            await ctx.send(embed=embed)
        elif choice == "삭제":
            await removestock(_name)
            embed = disnake.Embed(color=embederrorcolor)
            embed.add_field(name="🗑️ 삭제", value=f"{_name} 주식을 삭제하였습니다.")
            await ctx.send(embed=embed)
    else:
        embed = disnake.Embed(color=embederrorcolor)
        embed.add_field(name="❌ 오류", value="개발자만 실행가능한 명령어입니다.")
        await ctx.send(embed=embed, ephemeral=True)

@bot.slash_command(name="개발자_공지", description="모든서버에게 공지를 전송합니다. [개발자전용]")
async def developer_notification(ctx, content: str = commands.Param(name="내용")):
    if not await check_permissions(ctx):
        return
    await command_use_log(ctx, "개발자_공지", f"{content}")
    if ctx.author.id in developer:
        for guild in bot.guilds:
            server_remove_date = datetime.now()
            embed1 = disnake.Embed(title="개발자 공지", description=f"```{content}```", color=embedcolor)
            embed1.set_footer(text=f'To. {sec.developer_company}({ctx.author.name})\n{server_remove_date.strftime("전송시간 %Y년 %m월 %d일 %p %I:%M").replace("AM", "오전").replace("PM", "오후")}')
            
            chan = None  # 채널 변수를 초기화합니다.
            for channel in guild.text_channels:
                try:
                    if channel.topic and sec.notification_topic in channel.topic:  # topic이 None이 아닐 때 확인
                        chan = channel
                        break  # 첫 번째 채널을 찾으면 루프를 종료합니다.
                except:
                    pass
            
            try:
                if chan and chan.permissions_for(guild.me).send_messages:
                    await chan.send(embed=embed1)
                else:
                    raise ValueError("채널이 없거나 메시지 전송 권한이 없습니다.")
            except:
                for channel in guild.text_channels:
                    if channel.permissions_for(guild.me).send_messages:
                        embed1.set_footer(text=f'To. CodeStone({ctx.author.name})\n{server_remove_date.strftime("전송시간 %Y년 %m월 %d일 %p %I:%M").replace("AM", "오전").replace("PM", "오후")}')
                        try:
                            await channel.send(embed=embed1)
                        except Exception as e:
                            print(f"Error sending message to {channel.name}: {e}")  # 예외 로그 추가
                        break

        embed = disnake.Embed(title="공지 업로드 완료!", color=embedsuccess)
        await ctx.send(embed=embed)
    else:
        embed = disnake.Embed(color=embederrorcolor)
        embed.add_field(name="❌ 오류", value="개발자만 실행가능한 명령어입니다.")
        await ctx.send(embed=embed, ephemeral=True)

@bot.slash_command(name="문의답장", description="유저에게 답변을 보냅니다. [개발자전용]")
async def inquire_answer(ctx, member: str, message: str):
    if not await check_permissions(ctx):
        return

    await command_use_log(ctx, "문의답장", f"{member}, {message}")
    await ctx.response.defer()  # 응답 지연

    # 멘션 형식이나 ID에서 ID 추출
    try:
        if member.startswith('<@') and member.endswith('>'):
            member_id = int(member[2:-1])  # '<@!'와 '>' 제거
        else:
            member_id = int(member)  # ID 형식일 경우

    except ValueError:
        embed = disnake.Embed(color=embederrorcolor)
        embed.add_field(name="❌ 오류", value="올바른 멘션 형식이나 ID가 아닙니다.")
        await ctx.edit_original_response(embed=embed)
        return

    # 개발자 ID 확인
    if ctx.author.id not in developer:
        embed = disnake.Embed(color=embederrorcolor)
        embed.add_field(name="❌ 오류", value="이 명령어는 개발자만 사용할 수 있습니다.")
        await ctx.edit_original_response(embed=embed)
        return
    
    # User 객체 생성
    try:
        user = await bot.fetch_user(member_id)  # 유저 정보 가져오기
        await user.send(f"{ctx.author.mention} : {message}")  # DM 전송

        embed = disnake.Embed(title="✅ 전송완료", color=embedcolor)
        embed.add_field(name="대상자", value=f"{user.mention}")
        embed.add_field(name="답장 내용", value=f"{message}")
        await ctx.edit_original_response(embed=embed)

    except disnake.Forbidden:
        embed = disnake.Embed(color=embederrorcolor)
        embed.add_field(name="❌ 오류", value=f"{user.mention}님에게 메시지를 보낼 수 없습니다. DM을 허용하지 않았습니다.")
        await ctx.edit_original_response(embed=embed)
    except disnake.HTTPException:
        embed = disnake.Embed(color=embederrorcolor)
        embed.add_field(name="❌ 오류", value="메시지 전송 중 오류가 발생했습니다.")
        await ctx.edit_original_response(embed=embed)
    except Exception as e:
        embed = disnake.Embed(color=embederrorcolor)
        embed.add_field(name="❌ 오류", value=f"오류: {str(e)}")
        await ctx.edit_original_response(embed=embed)
##################################################################################################
# 처리된 멤버를 추적하기 위한 집합
processed_members = set()

@bot.event
async def on_member_join(member):
    # 이미 처리된 멤버인지 확인
    if member.id in processed_members:
        return  # 이미 처리된 멤버는 무시

    # 처리된 멤버 목록에 추가
    processed_members.add(member.id)

    # 데이터베이스 연결 및 비동기 커서 생성
    await database_create(member)
    db_path = os.path.join(os.getcwd(), "database", f"{member.guild.id}.db")
    aiodb = await aiosqlite.connect(db_path)
    aiocursor = await aiodb.cursor()  # 비동기 커서 생성
    try:
        # 설정 테이블에서 입장 로그 채널 아이디 가져오기
        await aiocursor.execute("SELECT 입장로그 FROM 설정")
        result = await aiocursor.fetchone()
        if result is not None:
            channel_id = result[0]
            # 채널 아이디에 해당하는 채널에 입장 로그 보내기
            channel = bot.get_channel(channel_id)
            if channel is not None:
                embedcolor = 0x00FF00  # 임베드 색상 설정
                embed = disnake.Embed(title="입장로그", color=embedcolor)
                embed.add_field(name="유저", value=f"{member.mention} ({member.name})")
                embed.set_thumbnail(url=member.display_avatar.url)
                server_join_date = datetime.now()  # datetime 클래스를 직접 사용
                account_creation_date = member.created_at
                embed.add_field(name="서버입장일", value=server_join_date.strftime("%Y년 %m월 %d일 %p %I:%M").replace("AM", "오전").replace("PM", "오후"), inline=False)
                embed.add_field(name="계정생성일", value=account_creation_date.strftime("%Y년 %m월 %d일 %p %I:%M").replace("AM", "오전").replace("PM", "오후"), inline=False)
                await channel.send(embed=embed)
    except Exception as e:
        print(f"오류가 발생했습니다: {e}")
    finally:
        # 데이터베이스 연결 종료
        await aiocursor.close()
        await aiodb.close()

@bot.event
async def on_member_remove(member):
    # 데이터베이스 연결 및 비동기 커서 생성
    await database_create(member)
    db_path = os.path.join(os.getcwd(), "database", f"{member.guild.id}.db")
    aiodb = await aiosqlite.connect(db_path)
    aiocursor = await aiodb.cursor()  # 비동기 커서 생성
    try:
        await aiocursor.execute("SELECT 퇴장로그 FROM 설정")
        result = await aiocursor.fetchone()
        if result is not None:
            channel_id = result[0]
            channel = bot.get_channel(channel_id)
            if channel is not None:
                embedcolor = 0x00FF00
                embed = disnake.Embed(title="퇴장로그", color=embedcolor)
                embed.add_field(name="유저", value=f"{member.mention} ({member.name})")
                server_remove_date = datetime.now()
                embed.add_field(name="서버퇴장일", value=server_remove_date.strftime("%Y년 %m월 %d일 %p %I:%M").replace("AM", "오전").replace("PM", "오후"), inline=False)
                await channel.send(embed=embed)
    finally:
        # 데이터베이스 연결 종료
        await aiocursor.close()
        await aiodb.close()
        
class inquiry_Modal(disnake.ui.Modal):
    def __init__(self):
        components = [
            disnake.ui.TextInput(
                label=f"유저",
                placeholder="아이디를 입력해주세요.",
                custom_id="text1",
                style=TextInputStyle.short
            ),
            disnake.ui.TextInput(
                label=f"답장 내용",
                placeholder="내용을 입력해주세요.",
                custom_id="text2",
                style=TextInputStyle.short
            )
        ]
        super().__init__(title="문의 답장", components=components)

    async def callback(self, ctx: disnake.ModalInteraction):
        global key, key1

        key = ctx.text_values['text1']
        key1 = ctx.text_values['text2']
        
        # 개발자 ID 확인
        if ctx.author.id not in developer:
            embed = disnake.Embed(color=embederrorcolor)
            embed.add_field(name="❌ 오류", value="이 명령어는 개발자만 사용할 수 있습니다.")
            await ctx.edit_original_response(embed=embed)
            return
        
        # User 객체 생성
        try:
            user = await bot.fetch_user(key)  # 유저 정보 가져오기
            await user.send(f"{ctx.author.mention} : {key1}")  # DM 전송

            embed = disnake.Embed(title="답장내용", color=embedsuccess)
            embed.add_field(name="관리자", value=f"{ctx.author.mention}")
            embed.add_field(name="내용", value=f"{key1}")
            await ctx.send(embed=embed)

        except disnake.Forbidden:
            embed = disnake.Embed(color=embederrorcolor)
            embed.add_field(name="❌ 오류", value=f"{user.mention}님에게 메시지를 보낼 수 없습니다. DM을 허용하지 않았습니다.")
            await ctx.edit_original_response(embed=embed)
        except disnake.HTTPException:
            embed = disnake.Embed(color=embederrorcolor)
            embed.add_field(name="❌ 오류", value="메시지 전송 중 오류가 발생했습니다.")
            await ctx.edit_original_response(embed=embed)
        except Exception as e:
            embed = disnake.Embed(color=embederrorcolor)
            embed.add_field(name="❌ 오류", value=f"오류: {str(e)}")
            await ctx.edit_original_response(embed=embed)

# 봇이 메시지를 받을 때 실행되는 이벤트
@bot.event
async def on_message(message):
    # 봇이 보낸 메시지는 무시
    if message.author == bot.user or message.author.bot:
        return

    user_id = message.author.id

    await add_exp(user_id, 5)

    # DM 채널에서의 처리
    if isinstance(message.channel, disnake.DMChannel):
        await handle_dm_message(message)

async def handle_dm_message(message):
    user = f"{message.author.display_name}({message.author.name})"
    avatar_url = message.author.avatar.url if message.author.avatar else None

    await message.add_reaction("✅")
    print("문의가 접수되었습니다.")
    await send_webhook_message("문의가 접수되었습니다.")

    # 첨부 파일 처리
    await handle_attachments(message)

    # 임베드 메시지 생성
    dm_embed = disnake.Embed(title="새로운 문의", color=embedcolor)
    dm_embed.add_field(name="사용자", value=user, inline=False)
    dm_embed.add_field(name="아이디", value=message.author.id, inline=False)
    dm_embed.add_field(name="내용", value=str(message.content), inline=False)
    if avatar_url:
        dm_embed.set_thumbnail(url=avatar_url)

    # 문의에 답장할 수 있는 버튼 생성
    reply_button = Button(label="답장하기", style=disnake.ButtonStyle.green)

    async def reply_button_callback(interaction):
        await interaction.response.send_modal(modal=inquiry_Modal())

    reply_button.callback = reply_button_callback

    # 버튼을 포함하는 뷰 생성
    view = View(timeout=None)
    view.add_item(reply_button)

    # 특정 채널로 전송
    await send_to_support_channel(dm_embed, view)

async def send_to_support_channel(embed=None, view=None, file=None):
    channel_id = int(sec.support_ch_id)
    channel = bot.get_channel(channel_id)

    if channel is None:
        print(f"채널 ID {channel_id}을(를) 찾을 수 없습니다.")
        return
    try:
        if file:
            await channel.send(file=file)
        else:
            await channel.send(embed=embed, view=view)
        print(f"메시지가 채널 ID {channel_id}로 전송되었습니다.")
    except Exception as e:
        print(f"메시지를 채널로 전송하는 중 오류 발생: {e}")

async def handle_attachments(message):
    if message.attachments:
        for attachment in message.attachments:
            try:
                # 파일 다운로드 및 전송
                file = await attachment.to_file()
                await send_to_support_channel(file=file, view=None)  # 파일도 채널로 전송
                print(f"파일 {attachment.filename}이(가) 채널 ID {sec.support_ch_id}로 전송되었습니다.")
            except Exception as e:
                print(f"파일을 채널로 전송하는 중 오류 발생: {e}")

def get_uptime():
    """업타임을 계산하는 함수."""
    now = datetime.now()
    uptime = now - start_time
    hours, remainder = divmod(int(uptime.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}시간 {minutes}분 {seconds}초"

@bot.event
async def on_ready():
    print("\n봇 온라인!")
    print(f'봇 : {bot.user.name}')
    print(f'샤드 : {bot.shard_count}')
    print(f'서버 수 : {len(bot.guilds)}')
    change_status.start()
    koreabots.start()
    await send_webhook_message("봇이 온라인 상태입니다.")

@bot.event
async def on_shard_ready(shard_id):
    print(f"{shard_id} 샤드가 준비되었습니다.")
    await send_webhook_message(f"{shard_id} 샤드가 준비되었습니다.")

@bot.event
async def on_shard_connect(shard_id):
    print(f"{shard_id} 샤드가 연결되었습니다.")
    await send_webhook_message(f"{shard_id} 샤드가 연결되었습니다.")

@bot.event
async def on_shard_disconnect(shard_id):
    print(f"{shard_id} 샤드의 연결이 끊어졌습니다.")
    await send_webhook_message(f"{shard_id} 샤드의 연결이 끊어졌습니다.")

@bot.event
async def on_shard_resumed(shard_id):
    print(f"{shard_id} 샤드가 다시 연결되었습니다.")
    await send_webhook_message(f"{shard_id} 샤드가 다시 연결되었습니다.")

async def update_server_count(update_type):
    db_path = os.path.join('system_database', 'system.db')
    async with aiosqlite.connect(db_path) as conn:
        if update_type == "new":
            await conn.execute("UPDATE info SET new_server = new_server + 1")
        elif update_type == "lose":
            await conn.execute("UPDATE info SET lose_server = lose_server + 1")
        await conn.commit()

@bot.event
async def on_guild_join(guild):
    await database_create_server_join(guild.id)
    print(f'새로운 서버에 입장했습니다: {guild.name} (ID: {guild.id})')
    await send_webhook_message(f"새로운 서버에 입장했습니다: {guild.name} (ID: {guild.id})")
    await update_server_count("new")

@bot.event
async def on_guild_remove(guild):
    await delete_server_database(guild.id)
    print(f'서버에서 퇴장했습니다: {guild.name} (ID: {guild.id})')
    await send_webhook_message(f"서버에서 퇴장했습니다: {guild.name} (ID: {guild.id})")
    await update_server_count("lose")

@tasks.loop(seconds=3)
async def change_status():
    guild_len = len(bot.guilds)
    statuses = [f'음악 재생', '편리한 기능을 제공', f'{guild_len}개의 서버를 관리']
    for status in statuses:
        await bot.change_presence(status=disnake.Status.online, activity=disnake.Game(status))
        await asyncio.sleep(3)

@tasks.loop(seconds=10)
async def koreabots():
    url = f"https://koreanbots.dev/api/v2/bots/{bot.user.id}/stats"
    headers = {
        "Authorization": sec.koreanbots_api_key,
        "Content-Type": "application/json"
    }
    body = {
        "servers": len(bot.guilds),
        "shards": len(bot.shards),
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url=url, json=body, headers=headers) as response:
            if response.status == 200:
                data = await response.json()

async def log_price_history(asset_type, asset_name, price):
    db_path = os.path.join('system_database', 'log.db')
    economy_aiodb = await aiosqlite.connect(db_path)
    aiocursor = await economy_aiodb.cursor()
    await aiocursor.execute(
        "INSERT INTO price_history (asset_type, asset_name, price, date) VALUES (?, ?, ?, ?)",
        (asset_type, asset_name, price, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    )
    await economy_aiodb.commit()
    await aiocursor.close()
    await economy_aiodb.close()

async def update_coin_prices():
    db_path = os.path.join('system_database', 'economy.db')
    economy_aiodb = await aiosqlite.connect(db_path)
    aiocursor = await economy_aiodb.cursor()
    await aiocursor.execute("SELECT coin_name, price FROM coin")
    coins = await aiocursor.fetchall()

    for coin in coins:
        name, price = coin
        new_price = round(price * random.uniform(0.85, 1.15), -1)  # ±15% 범위로 변경
        new_price = min(new_price, 300000000)  # 가상화폐 가격 상한가
        new_price = max(new_price, 3000000)  # 가상화폐 가격 하한가
        new_price = int(new_price)
        
        await aiocursor.execute("UPDATE coin SET price = ? WHERE coin_name = ?", (new_price, name))
        await log_price_history('coin', name, new_price)  # 가격 기록 추가
        await economy_aiodb.commit()
    
    await aiocursor.close()
    await economy_aiodb.close()

async def update_stock_prices():
    db_path = os.path.join('system_database', 'economy.db')
    economy_aiodb = await aiosqlite.connect(db_path)
    aiocursor = await economy_aiodb.cursor()
    await aiocursor.execute("SELECT stock_name, price FROM stock")
    stocks = await aiocursor.fetchall()

    for stock in stocks:
        name, price = stock
        new_price = round(price * random.uniform(0.85, 1.15), -1)  # ±15% 범위로 변경
        new_price = min(new_price, 5000000)  # 주식 가격 상한가
        new_price = max(new_price, 5000)  # 주식 가격 하한가
        new_price = int(new_price)
        
        await aiocursor.execute("UPDATE stock SET price = ? WHERE stock_name = ?", (new_price, name))
        await log_price_history('stock', name, new_price)  # 가격 기록 추가
        await economy_aiodb.commit()

    await aiocursor.close()
    await economy_aiodb.close()
    
@tasks.loop()
async def periodic_price_update():
    while True:
        await asyncio.sleep(60)
        now = datetime.now(pytz.timezone('Asia/Seoul'))
        if 6 <= now.hour < 22:
            await update_stock_prices()
            print("주가 변동")
            await send_webhook_message("주가 변동")
        await update_coin_prices()
        print("코인 변동")
        await send_webhook_message("코인 변동")

periodic_price_update.start()

@tasks.loop(seconds=1)  # 1초마다 실행
async def reset_database():
    now = datetime.now(pytz.timezone('Asia/Seoul'))  # KST로 현재 시각 가져오기
    if now.hour == 0 and now.minute == 0 and now.second == 0:
        db_path_economy = os.path.join('system_database', 'economy.db')
        db_path_system = os.path.join('system_database', 'system.db')

        async with aiosqlite.connect(db_path_economy) as conn: # 일일 체크인 초기화
            await conn.execute("UPDATE user SET checkin = 0")
            await conn.commit()

        async with aiosqlite.connect(db_path_system) as conn: # 일일 서버수 초기화
            await conn.execute("UPDATE info SET new_server = 0, lose_server = 0")
            await conn.commit()
        
        print("모든 사용자의 체크인 상태가 초기화되었습니다.")
        await send_webhook_message("모든 사용자의 체크인 상태가 초기화되었습니다.")

reset_database.start()

db_path = os.path.join('system_database', 'lotto.db')

@tasks.loop(seconds=1)  # 매 1초마다 체크
async def lottery_draw():
    now = datetime.now(pytz.timezone('Asia/Seoul'))  # 현재 KST 시간 가져오기
    if now.weekday() == 6 and now.hour == 11 and now.minute == 55 and now.second == 0:  # 매주 토요일 21시 0분 0초
        await draw_lottery()

lottery_draw.start()

async def draw_lottery():
    async with aiosqlite.connect(db_path) as db:
        # 당첨 번호 생성
        winning_numbers = random.sample(range(1, 46), 6)
        bonus_number = random.choice([num for num in range(1, 46) if num not in winning_numbers])  # 보너스 번호
        winning_numbers_str = ','.join(map(str, sorted(winning_numbers)))
        
        # 당첨자 확인
        async with db.execute('SELECT user_id, numbers FROM lottery') as cursor:
            winners = await cursor.fetchall()

        # 등수별 당첨자 수 초기화
        prize_counts = {
            "1등": 0,
            "2등": 0,
            "3등": 0,
            "4등": 0,
            "5등": 0,
        }

        # 현재 시간을 KST로 가져오기
        kst_now = datetime.now(pytz.timezone('Asia/Seoul'))
        month = kst_now.month
        week_of_month = (kst_now.day - 1) // 7 + 1

        # 임베드 메시지 생성
        embed = disnake.Embed(title=f"로또 추첨 결과 ({month}/{week_of_month}주)", color=0x00ff00)
        embed.add_field(name="당첨 번호", value=f"{winning_numbers_str} (보너스: {bonus_number})", inline=False)
        
        if winners:
            for winner in winners:
                user_id = winner[0]
                matched_numbers = len(set(winning_numbers) & set(map(int, winner[1].split(','))))
                prize_amount = 0

                # 당첨금 지급
                if matched_numbers == 6:
                    prize_amount = 3000000000
                    prize_counts["1등"] += 1
                elif matched_numbers == 5 and bonus_number in map(int, winner[1].split(',')):
                    prize_amount = 1500000000
                    prize_counts["2등"] += 1
                elif matched_numbers == 5:
                    prize_amount = 100000000
                    prize_counts["3등"] += 1
                elif matched_numbers == 4:
                    prize_amount = 10000000
                    prize_counts["4등"] += 1
                elif matched_numbers == 3:
                    prize_amount = 1000000
                    prize_counts["5등"] += 1

                if prize_amount > 0:
                    await addmoney(user_id, prize_amount)

                    # 당첨자에게 DM 전송
                    try:
                        user = await bot.fetch_user(user_id)
                        if user:
                            await user.send(f"축하합니다! 당신의 로또 번호가 당첨되었습니다!\n당첨 금액: {prize_amount}원")
                    except disnake.errors.NotFound:
                        print(f"사용자를 찾을 수 없습니다: {user_id}")
                    except disnake.errors.HTTPException as e:
                        print(f"DM을 보낼 수 없습니다: {e}")

            # 등수별 당첨자 수 추가
            embed.add_field(name="당첨자 수", value=f"1등: {prize_counts['1등']}명\n2등: {prize_counts['2등']}명\n3등: {prize_counts['3등']}명\n4등: {prize_counts['4등']}명\n5등: {prize_counts['5등']}명", inline=False)
        else:
            embed.add_field(name="결과", value="당첨자 없음.", inline=False)

        # 특정 채널에 결과 전송
        channel = bot.get_channel(int(sec.lotto_ch_id))
        if channel:
            await channel.send(embed=embed)

        # 로또 데이터 삭제 (테이블 구조 유지)
        await db.execute('DELETE FROM lottery')
        await db.commit()
        print("로또 데이터가 삭제되었습니다.")
        await send_webhook_message("로또 추첨이 완료되었습니다.")

# 설정
limit_level = 1000  # 최대 레벨

@tasks.loop(hours=12)
async def check_expired_members():
    db_path = os.path.join('system_database', 'membership.db')
    async with aiosqlite.connect(db_path) as economy_aiodb:
        current_date = datetime.now().strftime('%Y/%m/%d')
        # 만료된 회원을 비회원으로 변경
        await economy_aiodb.execute("UPDATE user SET class = 0 WHERE class = 1 AND expiration_date < ?", (current_date,))
        await economy_aiodb.commit()

check_expired_members.start()

def calculate_experience_for_level(current_level):
    if current_level is None:
        current_level = 1  # 기본값 설정

    E_0 = 100  # 기본 경험치
    r = 1.5    # 경험치 증가 비율
    k = 50     # 추가 경험치

    return math.floor(E_0 * (r ** (current_level - 1)) + k)

@tasks.loop(seconds=20)  # 20초마다 실행
async def check_experience():
    db_path = os.path.join('system_database', 'economy.db')
    async with aiosqlite.connect(db_path) as conn:
        async with conn.cursor() as c:
            await c.execute('SELECT id, exp, level, money FROM user')
            rows = await c.fetchall()
            
            updates = []
            messages = []

            for user_id, current_experience, current_level, current_balance in rows:
                current_experience = current_experience or 0
                current_level = current_level or 1
                current_balance = current_balance or 0

                new_level = current_level
                required_experience = calculate_experience_for_level(new_level)

                while current_experience >= required_experience and new_level < limit_level:
                    new_level += 1
                    required_experience = calculate_experience_for_level(new_level)

                adjusted_level = new_level - 1

                if adjusted_level > current_level:
                    updates.append((adjusted_level, user_id))
                    if adjusted_level < limit_level:
                        messages.append((user_id, adjusted_level))
                        reward = adjusted_level * 10000
                        new_balance = current_balance + reward
                        await c.execute('UPDATE user SET money = ? WHERE id = ?', (new_balance, user_id))

            if updates:
                await c.executemany('UPDATE user SET level = ? WHERE id = ?', updates)
            await conn.commit()

    for user_id, adjusted_level in messages:
        try:
            user = await bot.fetch_user(user_id)
            dm_setting = await dm_on_off(user)  # DM 설정을 가져옴
            if dm_setting != 1:  # DM 수신이 비활성화된 경우 메시지를 보내지 않음
                channel = await user.create_dm()
                reward = adjusted_level * 10000
                embed = disnake.Embed(
                    title="레벨 업! 🎉",
                    description=f'축하합니다! 레벨이 **{adjusted_level}**로 올랐습니다! 보상으로 **{reward}원**이 지급되었습니다.',
                    color=0x00ff00
                )
                await channel.send(embed=embed)
        except disnake.errors.NotFound:
            print(f"사용자를 찾을 수 없습니다: {user_id}")
        except disnake.errors.HTTPException as e:
            print(f"DM을 보낼 수 없습니다: {e}")

check_experience.start()

# 크레딧 부여 스케줄러
scheduled_credits = {}

async def get_user_class(user_id):
    async with connect_db() as conn:
        async with conn.execute("SELECT class FROM user WHERE user_id = ?", (user_id,)) as cursor:
            result = await cursor.fetchone()
    return result[0] if result else None  # 클래스 값 반환

def calculate_credit(user_class):
    credits = [30, 300, 600, 900, 1200]
    return credits[user_class] if 0 <= user_class < len(credits) else 0  # 기본값

@tasks.loop(seconds=60)  # 1분마다 실행
async def grant_scheduled_credits():
    now = datetime.now(pytz.timezone('Asia/Seoul'))
    if now.hour == 21 and now.minute == 0:  # 21시 00분에 크레딧 부여
        for user_id in list(scheduled_credits.keys()):
            user_class = await get_user_class(user_id)
            if user_class is not None:
                amount = calculate_credit(user_class)
                await add_user_credit(user_id, amount)
                print(f"{amount} 크레딧이 {user_id}에게 부여되었습니다.")
                await send_webhook_message(f"{amount} 크레딧이 {user_id}에게 부여되었습니다.")
                scheduled_credits[user_id] = (amount)  # 유지

grant_scheduled_credits.start()

# 데이터베이스가 있는 디렉토리
db_directory = './database'

async def startup():
    await bot.start(token, reconnect=True)
    global aiodb
    aiodb = {}
    for guild in bot.guilds:
        db_path = os.path.join(os.getcwd(), "database", f"{guild.id}.db")
        aiodb[guild.id] = await aiosqlite.connect(db_path)
    global economy_aiodb
    if economy_aiodb is None:
        db_path = os.path.join('system_database', 'economy.db')
        economy_aiodb = await aiosqlite.connect(db_path)

async def shutdown():
    global aiodb
    for aiodb_instance in aiodb.values():
        await aiodb_instance.close()
    await economy_aiodb.close()

try:
    asyncio.get_event_loop().run_until_complete(startup())
except KeyboardInterrupt:
    asyncio.get_event_loop().run_until_complete(shutdown())