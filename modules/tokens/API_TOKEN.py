import requests

API_KEY = "E3YJqrvvOwJdr0WKZje1DYne"
SECRET_KEY = "3Bps5tv2SRIpuJHJFYkoNU9HKLPVnoHZ"

def get_access_token():
    """
    使用 AK，SK 生成鉴权签名（Access Token）
    :return: access_token，或是None(如果错误)
    """
    url = "https://aip.baidubce.com/oauth/2.0/token"
    params = {"grant_type": "client_credentials", "client_id": API_KEY, "client_secret": SECRET_KEY}
    return str(requests.post(url, params=params).json().get("access_token"))

