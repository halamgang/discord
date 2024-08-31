import discord
import requests
import xml.etree.ElementTree as ET
from discord.ext import tasks, commands
from datetime import datetime
import pytz
import os  # os 모듈 추가

# 디스코드 클라이언트 설정
intents = discord.Intents.default()
client = commands.Bot(command_prefix='!', intents=intents)

# API URL 및 서비스 키
url = 'http://apis.data.go.kr/6280000/busArrivalService/getAllRouteBusArrivalList'
service_key = 'tYbxIh0QI2oIghZriDWwj6mjBQ+ZbLb9Mrz9D6n1KSRDFxeBdmVapVIAUv49HPoiL/p3A4qOE2YfwgYwYdE/Dg=='

# 특정 채널 ID
channel_id = 1275961893542035471  # 예: 123456789012345678

@client.event
async def on_ready():
    print(f'로그인한 사용자: {client.user}')
    await client.change_presence(activity=discord.Game(name="버스타는 중"))
    send_bus_info.start()  # 작업 시작

@tasks.loop(minutes=1)
async def send_bus_info():
    now = datetime.now(pytz.timezone('Asia/Seoul'))

    # 5시 5분, 8분, 10분에 메세지 전송
    if now.hour == 2 and now.minute in [10, 12, 14]:
        channel = client.get_channel(channel_id)
        if channel:
            await send_bus_data(channel)
            print(f"{now.hour}:{now.minute}: 메세지를 보냈습니다.")

async def send_bus_data(channel):
    # 요청 파라미터 설정
    params = {
        'serviceKey': service_key,
        'pageNo': '1',
        'numOfRows': '10',
        'bstopId': '163000043'  # 수정된 정류소 ID
    }

    # API 요청
    response = requests.get(url, params=params)

    if response.status_code == 200:
        root = ET.fromstring(response.content)
        result_code = root.find('.//resultCode')

        if result_code is not None:
            result_code = result_code.text
            result_msg = root.find('.//resultMsg').text

            if result_code == '0':  # 정상 처리
                item_list = root.findall('.//itemList')

                if item_list:
                    # 가장 먼저 도착하는 버스의 예상 도착 시간 계산
                    first_bus = min(item_list, key=lambda item: int(item.find('ARRIVALESTIMATETIME').text))
                    arrival_estimate_time = int(first_bus.find('ARRIVALESTIMATETIME').text)

                    # 분과 초로 변환
                    minutes = arrival_estimate_time // 60
                    seconds = arrival_estimate_time % 60
                    time_formatted = f"{minutes}분 {seconds}초"

                    # 임베드 제목을 가장 먼저 도착하는 버스의 예상 도착 시간으로 설정
                    embed = discord.Embed(title=f"가장 먼저 도착하는 버스: {time_formatted}", color=0x00ff00)
                    embed.add_field(name="버스 ID | 최근 정류소 명 | 남은 정류장 수", value="", inline=False)

                    for item in item_list:
                        bus_id = item.find('BUSID').text
                        latest_stop_name = item.find('LATEST_STOP_NAME').text
                        rest_stop_count = item.find('REST_STOP_COUNT').text

                        embed.add_field(name="", value=f"{bus_id} | {latest_stop_name} | {rest_stop_count}", inline=False)

                    # Footer에 경과일 수 추가
                    start_date = datetime(2024, 6, 2)
                    days_passed = (datetime.now() - start_date).days
                    embed.set_footer(text=f"❤ | Today + {days_passed}일")

                    await channel.send(embed=embed)
                else:
                    await channel.send("버스 정보가 없습니다.")
            else:
                await channel.send(f"오류 발생: {result_code} - {result_msg}")
        else:
            await channel.send("결과 코드가 없습니다. 응답 내용을 확인하세요.")
    else:
        await channel.send(f"API 요청 실패: {response.status_code}")

@client.command()
async def 버스(ctx):
    channel = client.get_channel(channel_id)
    if channel:
        await send_bus_data(channel)

# 여기에 본인의 디스코드 봇 토큰을 환경변수에서 가져오기
client.run(os.getenv('DISCORD_TOKEN'))  # 환경변수에서 토큰 가져오기
