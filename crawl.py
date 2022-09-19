from bs4 import BeautifulSoup
import requests
import re
import time
import json

session = requests.Session()

GALL_NAME = "umamusu"
HEAD_ID = "160"

HEADERS = {
    "Accept-Language": "en",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Linux; Android 12; SM-F711N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Mobile Safari/537.36",
    "sec-ch-ua": '" Not A;Brand";v="99", "Chromium";v="100", "Google Chrome";v="100"',
    "sec-ch-ua-mobile": "?1",
    "sec-ch-ua-platform": '"Android"',
}

resp = session.get("https://m.dcinside.com/board/{}?headid={}".format(GALL_NAME, HEAD_ID), headers={
    **HEADERS,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "Referer": "https://gall.dcinside.com/",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-site",
})
soup = BeautifulSoup(resp.content, 'html.parser')
csrf_token = soup.find("meta", attrs={"name": "csrf-token"})['content']

res = {}
page = 0
last_page = 1000

while page < last_page:
    resp = session.post("https://m.dcinside.com/ajax/response-list", data={
        "id": "umamusu",
        "page": str(page + 1),
        "headid": "160",
    }, headers={
        **HEADERS,
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Referer": "https://m.dcinside.com/board/{}?headid={}&page={}".format(GALL_NAME, HEAD_ID, page),
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "X-CSRF-TOKEN": csrf_token,
        "X-Requested-With": "XMLHttpRequest",
    })
    result = resp.json()
    last_page = result['gall_list']['last_page']
    data = result['gall_list']['data']
    if len(data) > 0:
        for d in data:
            res[d['no']] = {
                'name': d['name_ori'],
                'subject': d['subject'],
            }
    else:
        print(result)
    page += 1

processed = []
total_sum = 0
for d in res:
    # mask name
    name = res[d]['name']
    if name != "ㅇㅇ":
        l = len(name)
        if l < 3:
            name = (l-1)*"*" + name[-1]
        else:
            name = name[0] + (l-2)*"*" + name[-1]

    subject = res[d]['subject']
    orig_sub = subject

    # 100'000
    subject = re.sub(r"[']", "", subject)

    # 구글 578,130 / 포인트 567 pt
    subject = re.sub(r"[,\d]*\d\s*pt", "", subject)

    # 구글/ 1,540,000~1,575,500 추정
    # 구글 91.96$
    subject = re.sub(r"\d[\d.,]*[~\$]", "", subject)

    # 애플 / NZD $153 = 한화 126700
    # 구글 71900 + $112.11(현재환율로 150900)
    subject = re.sub(r"\$\d[\d.,]*", "", subject)

    # 구글 / 121200 (2계정)
    # 구글 / 2,753,700원 (이백칠십오만삼천칠백 원)
    # 구글 / 2,119,600 (포인트 제외 2,016,600)
    # 3,198,700 (환불 받은 금액 396.000 포함)
    # 애플 353,9000 (원화 126,000₩, 파운드화 £1609.77)
    # 구글 302000 ( 52000 환불됨 )
    # 구글 71900 + $112.11(현재환율로 150900)
    # 구글 3,800,000원 (대충380만원) 환불 왜 근데 여기에 씀?
    # 구글 1777100(170만원)
    # FP: 환불 참여합니다 (구글 953,700)
    subject = re.sub(r"\(.*\)", "", subject)

    # 구글/ 대략 60만원
    # 구글 / 560만
    # 구글 / 142만 6600원
    # 구글/ 746만8840원
    # 애플 132.1만
    subject = re.sub(
        r"(\d[\d.]*)만", lambda match: str(int(float(match.group(1))*10000)) + " ", subject)

    # 구글 57만 2천원
    # 24만6천원/구글
    subject = re.sub(r"(?<=\d)천원", "000 ", subject)

    # 구글 101,359.20 애플 281,037.75
    subject = re.sub(r"\.\d{2}(?!\d)", "", subject)

    if subject != orig_sub:
        print("{} [변환] {} -> {}".format(d, orig_sub, subject))

    match = re.findall(r"\d[\d.,]*", subject)
    amounts = []
    for v in match:
        amount = int(re.sub(r"[.,]", "", v))

        # 키타산3천장2돌
        # 구글플레이 22건
        # "1억"
        # FP: 15
        if amount < 100:
            print("{} [제외 {} < 100]: {}".format(d, amount, orig_sub))
            continue

        # 구글 120
        if amount < 1000:
            amount *= 10000
            print("{} [가정 {}]: {}".format(d, amount, orig_sub))

        # implausible
        if amount > 60000000:
            print("{} [제외 {} > 60000000] {}".format(d, amount, orig_sub))
            continue

        amounts.append(amount)

    # 구글 259,000  25.9만
    # 구글 383,640 애플 48,200 총액 431,840원
    if (len(amounts) == 2 and amounts[0] == amounts[1]) or (len(amounts) == 3 and amounts[0] + amounts[1] == amounts[2]):
        print("{} [중복] {}".format(d, orig_sub))
        amounts.pop()

    # 총액 xx 구글 yy 애플 zz
    if len(amounts) == 3 and amounts[1] + amounts[2] == amounts[0]:
        print("{} [중복] {}".format(d, orig_sub))
        amounts.pop(0)

    sum_ = sum(amounts)
    # 구글 애플 163.8
    if sum_ < 3000:
        print("{} [실패] {}".format(d, orig_sub))
        continue

    total_sum += sum_
    processed.append({
        'id': d,
        'name': name,
        'amount': sum_,
    })

res = {'data': processed, 'total_sum': total_sum, 'updated': int(time.time())}
with open('processed.json', 'w') as f:
    json.dump(res, f, ensure_ascii=False)
