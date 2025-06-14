 
# -*- coding: UTF-8 -*-
import requests
import time
import pandas as pd
import math
import random
 
user_agent_list = [
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/45.0.2454.85 Safari/537.36 115Browser/6.0.3',
    'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_8; en-us) AppleWebKit/534.50 (KHTML, like Gecko) Version/5.1 Safari/534.50',
    'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-us) AppleWebKit/534.50 (KHTML, like Gecko) Version/5.1 Safari/534.50',
    'Mozilla/5.0 (Windows NT 6.1; rv:2.0.1) Gecko/20100101 Firefox/4.0.1',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_0) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.56 Safari/535.11',
    'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0',
    'Mozilla/5.0 (Windows NT 6.1; rv:2.0.1) Gecko/20100101 Firefox/4.0.1',
    "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.75 Mobile Safari/537.36",
]
 
# 目标url
url = "https://mp.weixin.qq.com/cgi-bin/appmsg"
cookie = "pac_uid=0_ds9msiEpx9Qem; _qimei_uuid42=18b090b302f100adf68ecdeb72fe653eb7b30947cd; _qimei_fingerprint=28e27f13e024b4e72ed41740c05847af; _qimei_h38=2db80759f68ecdeb72fe653e02000001818b09; eas_sid=61n7U3Q1g9e1Z7l2O3p7K8z0h4; pgv_pvid=5270360774; RK=rHvUSUVjuv; ptcz=bd7828ddcd45df84e5a0f6f7f7327c633599c7871d8e261a031548c0334e14c9; LW_uid=11e7Q3B659b0N6j3K1G4k5G2Y4; qq_domain_video_guid_verify=93258a7c15ae699d; livelink_pvid=646047744; LW_sid=Y1D74411c0F9Z9K211A3j9E2U7; _qimei_q32=594eb0e2de16e2b0603b01603901ae35; _qimei_q36=ba41dac0d2ab33aee13b619730001cf17719; omgid=0_ds9msiEpx9Qem; yyb_muid=05C0BCA5673C67010E4CA988665A6673; ua_id=21xW3djbf0CP7RV0AAAAABfzeQ8hTyfuJ1_VNlfcRos=; _clck=gxrllu|1|fwr|0; wxuin=49881336752533; mm_lang=zh_CN; cert=6yJ4Ig7fhJDLFA6uPZUFAqbC8PvzkeSa; uuid=23d68be89ac2c2da2279373a7eadd784; rand_info=CAESIFGcS/iOtw4bmLDKfsO6q7JvSA4IVPm4LY8wjkdklla9; slave_bizuin=3940462310; data_bizuin=3940462310; bizuin=3940462310; data_ticket=nZrY2IM4tPaOVH+55ffh5Pgnrqs4haZi84TeoO0+u1EVrNz5ssPA7uNFY7TjyBfT; slave_sid=b1daRGxsdGdpOEdVaGZQbFN4QUpFZ2cxMVUzbEEyXzh0Q1V2QTk2dkVfeE9JVFVUVUNBZWh3UTdDSEVTUGZ0Vkp3YXp1MGh0aDNFQWxyV0o5M2poSk5KWTdFRkFtTGg5YmdqWE1YTklFRHNOYnhTNUJ5WEkyTHJ6aFhPTjNhNG9EcDRXS3NNRTJzYkszT0to; slave_user=gh_ec9a9a7639a9; xid=bd21558650aa4984725bb6f888ee8f9c; _clsk=q2lc1e|1749881577361|3|1|mp.weixin.qq.com/weheat-agent/payload/record"
 
# 使用Cookie，跳过登陆操作
 
data = {
    "token": "1482316469",
    "lang": "zh_CN",
    "f": "json",
    "ajax": "1",
    "action": "list_ex",
    "begin": "0",
    "count": "5",
    "query": "",
    "fakeid": "MjM5OTgwOTQ2NQ==",
    "type": "9",
}
headers = {
        "Cookie": cookie,
        "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.75 Mobile Safari/537.36",
 
    }
content_json = requests.get(url, headers=headers, params=data).json()
count = int(content_json["app_msg_cnt"])
print(count)
page = int(math.ceil(count / 5))
print(page)
content_list = []
# 功能：爬取IP存入ip_list列表
 
for i in range(page):
    data["begin"] = i * 5
    user_agent = random.choice(user_agent_list)
    headers = {
        "Cookie": cookie,
        "User-Agent": user_agent,
 
    }
    ip_headers = {
        'User-Agent': user_agent
    }
    # 使用get方法进行提交
    content_json = requests.get(url, headers=headers, params=data).json()
    # 返回了一个json，里面是每一页的数据
    for item in content_json["app_msg_list"]:
        # 提取每页文章的标题及对应的url
        items = []
        items.append(item["title"])
        items.append(item["link"])
        t = time.localtime(item["create_time"])
        items.append(time.strftime("%Y-%m-%d %H:%M:%S", t))
        content_list.append(items)
    print(i)
    if (i > 0) and (i % 10 == 0):
        name = ['title', 'link', 'create_time']
        test = pd.DataFrame(columns=name, data=content_list)
        test.to_csv("url.csv", mode='a', encoding='utf-8')
        print("第" + str(i) + "次保存成功")
        content_list = []
        time.sleep(random.randint(60,90))
    else:
        time.sleep(random.randint(15,25))
 
name = ['title', 'link', 'create_time']
test = pd.DataFrame(columns=name, data=content_list)
test.to_csv("url.csv", mode='a', encoding='utf-8')
print("最后一次保存成功")