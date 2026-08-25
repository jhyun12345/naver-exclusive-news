import requests
import re
import html
import os
import json
import time

CLIENT_ID = os.environ.get("NAVER_CLIENT_ID")
CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET")
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

NAVER_URL = "https://naverapihub.apigw.ntruss.com/search/v1/news"
TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

STATE_FILE = "sent_links.json"

headers = {
    "X-NCP-APIGW-API-KEY-ID": CLIENT_ID,
    "X-NCP-APIGW-API-KEY": CLIENT_SECRET
}


def get_exclusive_news():
    exclusive_news = []

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

            # [단독], [단독 인터뷰], [단독입수] 등
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

    response = requests.post(
        TELEGRAM_URL,
        data={
            "chat_id": CHAT_ID,
            "text": message
        },
        timeout=30
    )

    if response.status_code == 200:
        print("전송 성공:", news["title"])
        return True

    print("텔레그램 오류:", response.status_code)
    print(response.text)
    return False


def load_sent_links():
    if not os.path.exists(STATE_FILE):
        return None

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return set(json.load(f))


def save_sent_links(sent_links):
    # 파일이 지나치게 커지지 않도록 최근 3000개만 보관
    links = list(sent_links)[-3000:]

    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(links, f, ensure_ascii=False, indent=2)


print("단독기사 확인 시작")

news_list = get_exclusive_news()

sent_links = load_sent_links()

# 처음 실행할 때는 현재 기사들을 기준점으로만 저장
# 과거 기사 수십 건을 텔레그램에 보내지 않음
if sent_links is None:
    sent_links = {news["link"] for news in news_list}
    save_sent_links(sent_links)

    print("첫 실행입니다.")
    print("현재 단독기사", len(sent_links), "건을 기준점으로 저장했습니다.")
    print("기존 기사는 전송하지 않습니다.")

else:
    new_articles = []

    for news in news_list:
        if news["link"] not in sent_links:
            new_articles.append(news)

    # 오래된 기사부터 순서대로 전송
    for news in reversed(new_articles):
        if send_telegram(news):
            sent_links.add(news["link"])
            time.sleep(1)

    save_sent_links(sent_links)

    if new_articles:
        print("새 단독기사", len(new_articles), "건 확인")
    else:
        print("새 단독기사 없음")

print("작업 종료")
