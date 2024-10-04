import requests, uuid, platform
import time, datetime, hmac, hashlib
import security as sec

# API 관련 설정
protocol = 'https'
domain = 'api.coolsms.co.kr'
prefix = ''

def unique_id():
    """고유한 UUID를 생성합니다."""
    return str(uuid.uuid1().hex)

def get_iso_datetime():
    """현재 UTC 시간을 ISO 8601 형식으로 반환합니다."""
    utc_offset_sec = time.altzone if time.localtime().tm_isdst else time.timezone
    utc_offset = datetime.timedelta(seconds=-utc_offset_sec)
    return datetime.datetime.now().replace(tzinfo=datetime.timezone(offset=utc_offset)).isoformat()

def get_signature(key, msg):
    """주어진 메시지에 대한 HMAC-SHA256 서명을 생성합니다."""
    return hmac.new(key.encode(), msg.encode(), hashlib.sha256).hexdigest()

def get_headers(api_key, api_secret):
    """API 요청 헤더를 생성합니다."""
    date = get_iso_datetime()
    salt = unique_id()
    combined_string = date + salt

    return {
        'Authorization': f'HMAC-SHA256 ApiKey={api_key}, Date={date}, salt={salt}, signature={get_signature(api_secret, combined_string)}',
        'Content-Type': 'application/json; charset=utf-8'
    }

def get_url(path):
    """주어진 경로에 대한 완전한 URL을 반환합니다."""
    url = f'{protocol}://{domain}'
    if prefix:
        url += prefix
    return url + path

def send_many(parameter):
    """여러 메시지를 전송하는 API 요청을 보냅니다."""
    api_key = sec.coolsms_api_key  # API 키
    api_secret = sec.coolsms_api_secret  # API 비밀 키

    parameter['agent'] = {
        'sdkVersion': 'python/4.2.0',
        'osPlatform': f"{platform.platform()} | {platform.python_version()}"
    }

    try:
        response = requests.post(get_url('/messages/v4/send-many'), headers=get_headers(api_key, api_secret), json=parameter)
        response.raise_for_status()  # HTTP 오류가 발생하면 예외 발생
        return response
    except requests.exceptions.RequestException as e:
        print(f"요청 오류: {e}")
        return None

def send_kakao(data):
    """KakaoTalk 메시지를 전송합니다."""
    result = send_many(data)
    
    if result is not None:
        response = result.json()
        if response.get("status") == "SENDING":
            print(f"[알림톡] {data['messages'][0]['to']}: {response['log'][-1]['message']}")
            return True
        else:
            print(f"[알림톡] {data['messages'][0]['to']}: {response['status']}")
    else:
        print("[알림톡] 메시지 전송 실패.")
    
    return False