import time
import requests
import json
from datetime import datetime, timezone, timedelta
import os

# ==========================
# 配置（GitHub Secrets 推荐）
# ==========================
APP_TOKEN = os.environ["APP_TOKEN"]
TABLE_ID = os.environ["TABLE_ID"]
RECEIVE_ID = os.environ["RECEIVE_ID"]
APP_ID = os.environ["APP_ID"]
APP_SECRET = os.environ["APP_SECRET"]


# ==========================
# 1️⃣ 获取 tenant_access_token（无缓存版：GitHub最佳实践）
# ==========================
def get_tenant_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"

    payload = {
        "app_id": APP_ID.strip(),
        "app_secret": APP_SECRET.strip()
    }

    for i in range(3):
        res = requests.post(url, json=payload).json()
        print(f"[token try {i}] ->", res)

        if res.get("code") == 0:
            return res["tenant_access_token"]

        time.sleep(2)

    raise Exception(f"获取token失败: {res}")


# ==========================
# 2️⃣ 读取多维表格
# ==========================
def get_bitable_records(token):
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records"

    headers = {
        "Authorization": f"Bearer {token}"
    }

    res = requests.get(url, headers=headers).json()
    print("bitable:", res)

    if res.get("code") != 0:
        raise Exception(res)

    return res["data"]["items"]


# ==========================
# 3️⃣ 找今天数据
# ==========================
def get_today_record(items):
    china_tz = timezone(timedelta(hours=8))
    today = datetime.now(china_tz).strftime("%Y-%m-%d")

    for item in items:
        f = item["fields"]

        if "日期" not in f:
            continue

        ts = f["日期"]
        date_str = datetime.fromtimestamp(ts / 1000, tz=china_tz).strftime("%Y-%m-%d")

        if date_str == today:
            return f

    return None


# ==========================
# 4️⃣ 生成消息
# ==========================
def build_message(fields):
    china_tz = timezone(timedelta(hours=8))

    msg = "🐱 今日打卡\n\n"

    for k, v in fields.items():
        if k == "日期" and isinstance(v, int):
            v = datetime.fromtimestamp(v / 1000, tz=china_tz).strftime("%Y-%m-%d")
        msg += f"{k}: {v}\n"

    return msg


# ==========================
# 5️⃣ 推送飞书消息
# ==========================
def send_message(token, text):
    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"

    payload = {
        "receive_id": RECEIVE_ID,
        "msg_type": "text",
        "content": json.dumps({"text": text})
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    res = requests.post(url, json=payload, headers=headers).json()
    print("push result:", res)

    return res


# ==========================
# 6️⃣ 主流程
# ==========================
def main():
    token = get_tenant_token()
    print("✅ token ok")

    items = get_bitable_records(token)

    today = get_today_record(items)

    if not today:
        print("⚠️ today no data")
        return

    msg = build_message(today)

    print("message:\n", msg)

    send_message(token, msg)


if __name__ == "__main__":
    main()
