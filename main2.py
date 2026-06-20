import time
import json
import requests
import os
from datetime import datetime, timezone, timedelta

# ==========================
# 配置（GitHub Secrets 注入）
# ==========================
RECEIVE_ID = os.environ["RECEIVE_ID"].strip()
APP_ID = os.environ["APP_ID"].strip()
APP_SECRET = os.environ["APP_SECRET"].strip()

# 清空系统代理，避免Actions网络异常
NO_PROXY = {"http": None, "https": None}

# ==========================
# 1️⃣ 获取 tenant_access_token（保留，自建应用私信必须鉴权）
# ==========================
def get_tenant_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {
        "app_id": APP_ID,
        "app_secret": APP_SECRET
    }

    for i in range(3):
        try:
            res_raw = requests.post(
                url,
                json=payload,
                timeout=10,
                proxies=NO_PROXY
            )
            res = res_raw.json()
            print(f"[token 第{i+1}次请求返回] => {res}", flush=True)

            if res.get("code") == 0:
                token = res["tenant_access_token"].strip()
                print(f"✅ 获取token成功，token前10位：{token[:10]}******", flush=True)
                return token

            time.sleep(2)
        except Exception as e:
            print(f"[token 第{i+1}次请求异常] {repr(e)}", flush=True)
            time.sleep(2)

    raise Exception(f"3次获取token全部失败，最后返回：{res}")

# ==========================
# 2️⃣ 生成分时段+随机语录消息（替换原多维表格构建逻辑）
# ==========================
def build_message():
    china_tz = timezone(timedelta(hours=8))
    now = datetime.now(china_tz)
    TODAY = now.strftime("%Y-%m-%d")
    HOUR = int(now.strftime("%H"))

    # 随机语录池，和你GitHub Action文案完全一致
    messages = [
        "今天不用做到满分，能开始就很好。",
        "别小看每天20分钟，它会慢慢改变很多东西。",
        "保持好奇心，比保持动力更容易坚持。",
        "允许自己慢一点，但不要停下来。",
        "如果今天只能完成一件事，请选那个半年后还值得庆祝的。 ",
        "困的时候休息也是任务的一部分。",
        "不要把80%的精力，花在研究怎么做事情，先把事情做了。",
        "如果一直追逐即时反馈，就永远拿不到长期奖励。 ",
        "允许今天只有60分，因为连续的60分比偶尔100分更厉害。",
        "允许自己普通，但不要停止前进。 ",
        "灵感不会消失，它只是需要一点睡眠和咖啡。 ",
        "今天请先完成一件『三个月后的自己会感谢你』的事情。剩下的时间，再去追逐即时快乐。  "
    ]
    import random
    random_text = random.choice(messages)

    # 按时段区分标题与正文
    if 7 <= HOUR < 11:
        title = "🌅 开机成功！"
        content = f"""### 今日启动
今天最重要的一件事：
- [ ] __________

随机掉落一句话：
{random_text}

📅 {TODAY}"""
    elif 11 <= HOUR < 18:
        title = "☀️喵😸"
        content = f"""### 上午小提醒
祝今天充满阳光和活力

随机掉落一句话：
{random_text}

📅 {TODAY}"""
    else:
        title = "🌙 今天过得怎么样"
        content = f"""### 今日复盘
- [ ] 学习
- [ ] 运动
- [ ] 推进一个小项目

今天最满意的一件小事：
- __________

随机掉落一句话：
{random_text}

📅 {TODAY}"""
    # 拼接完整推送文本
    full_msg = f"{title}\n\n{content}"
    return full_msg

# ==========================
# 3️⃣ 飞书自建应用私信推送（保留不变）
# ==========================
def send_message(token, text):
    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "receive_id": RECEIVE_ID,
        "msg_type": "text",
        "content": json.dumps({"text": text})
    }

    res = requests.post(
        url,
        json=payload,
        headers=headers,
        timeout=10,
        proxies=NO_PROXY
    ).json()
    print(f"消息推送结果：{res}", flush=True)
    return res

# ==========================
# 4️⃣ 主执行流程（删除多维表格读取逻辑）
# ==========================
def main():
    try:
        print("===== 脚本开始执行 =====", flush=True)
        token = get_tenant_token()
        print("✅ Token获取完成，生成推送文案", flush=True)

        push_text = build_message()
        print(f"待推送消息：\n{push_text}", flush=True)
        send_message(token, push_text)
        print("🎉 脚本全部执行完成", flush=True)

    except Exception as err:
        print(f"❌ 脚本执行失败：{repr(err)}", flush=True)
        raise err

if __name__ == "__main__":
    main()
