import requests
import re
import html
import time
import os
from datetime import datetime

# ==========================================
# 비밀번호는 코드에 적지 않고
# Render에서 가져옵니다.
# ==========================================

CLIENT_ID = os.environ.get("NAVER_CLIENT_ID")
CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET")
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

NAVER_URL = "https://naverapihub.apigw.ntruss.com/search/v1/news"
TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

headers = {
    "X-NCP-APIGW-API-KEY-ID": CLIENT_ID,
    "X-NCP-APIGW-API-KEY": CLIENT_SECRET
}


def get_exclusive_news():

    exclusive_news = []

    # 최신 검색 결과 300건 확인
    for start in [1, 101, 201]:

        params = {
            "query": "단독",
            "display": 100,
            "start": start,
            "sort": "date",
            "format": "json"
        }

        response = requests.get(
            NAVER_URL,
            headers=headers,
            params=params,
            timeout=30
        )

        if response.status_code != 200:
            print("네이버 오류:", response.status_code)
            print(response.text)
            continue

        data = response.json()

        for item in data.get("items", []):

            title = re.sub("<.*?>", "", item["title"])
            title = html.unescape(title).strip()

            # [단독], [단독 인터뷰], [단독입수] 등만 통과
            if re.match(r"^\[\s*단독[^\]]*\]", title):

                exclusive_news.append({
                    "title": title,
                    "link": item["link"]
                })

        time.sleep(0.3)

    return exclusive_news


def send_telegram(news):

    message = f"""🚨 {news['title']}

🔗 {news['link']}"""

    result = requests.post(
        TELEGRAM_URL,
        data={
            "chat_id": CHAT_ID,
            "text": message
        },
        timeout=30
    )

    if result.status_code == 200:
        print("전송 성공:", news["title"])
    else:
        print("텔레그램 오류:", result.status_code)
        print(result.text)


# ==========================================
# 프로그램 시작
# ==========================================

print("================================")
print("단독뉴스 봇 시작")
print("================================")

# 시작 당시 기사들은 기존 기사로 처리
initial_news = get_exclusive_news()

sent_links = set()

for news in initial_news:
    sent_links.add(news["link"])

print("기준 기사:", len(sent_links), "건")
print("이제부터 새로 발견되는 기사만 전송합니다.")


# ==========================================
# 5분마다 계속 확인
# ==========================================

while True:

    try:

        print()
        print(
            "뉴스 확인:",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        news_list = get_exclusive_news()

        new_articles = []

        for news in news_list:

            if news["link"] not in sent_links:

                new_articles.append(news)
                sent_links.add(news["link"])

        # 오래된 것부터 순서대로 전송
        for news in reversed(new_articles):

            send_telegram(news)
            time.sleep(1)

        if len(new_articles) == 0:
            print("새 단독기사 없음")
        else:
            print(
                "새 단독기사",
                len(new_articles),
                "건 전송 완료"
            )

        print("5분 후 다시 확인합니다.")

        time.sleep(300)

    except Exception as e:

        print("오류 발생:", e)
        print("1분 후 다시 시도합니다.")

        time.sleep(60)
