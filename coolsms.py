import sys
import security as sec
from sdk.api.message import Message
from sdk.exceptions import CoolsmsException

def send_sms(to, text, type):
    api_key = sec.coolsms_api_key # API KEY
    api_secret = sec.coolsms_api_secret # API 보안키
    from_ = sec.send_number # 보내는 번호
    type = type  # 'sms', 'lms', 'mms', 'ata' 중 선택 | 메시지 타입

    params = {
        'type': type,  # 메시지 타입 (sms, lms, mms, ata)
        'to': to,  # 받는 사람 번호 (여러 번호로 보낼 경우 콤마로 구분)
        'from': from_,  # 보내는 사람 번호
        'text': text  # 메시지 내용
    }

    cool = Message(api_key, api_secret)
    try:
        response = cool.send(params)
        print("Success Count : %s" % response['success_count'])
        print("Error Count : %s" % response['error_count'])
        print("Group ID : %s" % response['group_id'])

        if "error_list" in response:
            print("Error List : %s" % response['error_list'])

    except CoolsmsException as e:
        print("Error Code : %s" % e.code)
        print("Error Message : %s" % e.msg)