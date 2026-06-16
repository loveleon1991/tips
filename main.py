import time
import json
import requests
import os
from datetime import datetime, timezone, timedelta

# ==========================
# 配置（GitHub Secrets 注入，读取后清除首尾空白）
# ==========================
APP_TOKEN = os.environ["APP_TOKEN"].strip()
TABLE_ID = os.environ["TABLE_ID"].strip()
RECEIVE_ID = os.environ["RECEIVE_ID"].strip()
APP_ID = os.environ["APP_ID"].strip()
APP_SECRET = os.environ["APP_SECRET"].strip()

# 统一清空系统代理，避免GitHub Actions网络异常
NO_PROXY = {"http": None, "https": None}

# ==========================
# 1️⃣ 获取 tenant_access_token（稳定 + 重试）
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
                # 打印token前10位用于对比本地/线上差异
                print(f"✅ 获取token成功，token前10位：{token[:10]}******", flush=True)
                return token

            time.sleep(2)
        except Exception as e:
            print(f"[token 第{i+1}次请求异常] {repr(e)}", flush=True)
            time.sleep(2)

    raise Exception(f"3次获取token全部失败，最后返回：{res}")

# ==========================
# 2️⃣ 读取多维表格
# ==========================
def get_bitable_records(token):
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records"
    token_clean = token.strip()
    headers = {
        "Authorization": f"Bearer {token_clean}"
    }

    print("===== 多维表格请求调试信息 =====", flush=True)
    print(f"请求URL：{url}", flush=True)
    print(f"鉴权头前缀：Bearer {token_clean[:10]}******", flush=True)
    print("================================", flush=True)

    resp = requests.get(
        url,
        headers=headers,
        timeout=10,
        proxies=NO_PROXY
    )

    print(f"接口状态码：{resp.status_code}", flush=True)
    print(f"原始响应片段：{resp.text[:500]}", flush=True)

    try:
        res = resp.json()
    except Exception as e:
        raise Exception(f"多维表格返回非JSON数据，异常：{repr(e)}，完整返回：{resp.text}")

    if res.get("code") != 0:
        raise Exception(f"多维表格接口报错：{res}")

    return res["data"]["items"]

# ==========================
# 3️⃣ 筛选今日数据（东八区）
# ==========================
def get_today_record(items):
    china_tz = timezone(timedelta(hours=8))
    today_str = datetime.now(china_tz).strftime("%Y-%m-%d")
    print(f"当前东八区日期：{today_str}", flush=True)

    for item in items:
        fields = item.get("fields", {})
        if "日期" not in fields:
            continue

        timestamp_ms = fields["日期"]
        record_date = datetime.fromtimestamp(timestamp_ms / 1000, tz=china_tz).strftime("%Y-%m-%d")
        if record_date == today_str:
            return fields
    return None

# ==========================
# 4️⃣ 组装推送文本消息
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
# 5️⃣ 飞书私信推送
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
# 6️⃣ 主执行流程 + 全局异常捕获
# ==========================
def main():
    try:
        print("===== 脚本开始执行 =====", flush=True)
        token = get_tenant_token()
        print("✅ Token获取完成，开始读取多维表格", flush=True)

        records = get_bitable_records(token)
        print(f"✅ 读取表格成功，共{len(records)}条数据", flush=True)

        today_data = get_today_record(records)
        if not today_data:
            print("⚠️ 今日无打卡数据，脚本结束", flush=True)
            return

        push_text = build_message(today_data)
        print(f"待推送消息：\n{push_text}", flush=True)
        send_message(token, push_text)
        print("🎉 脚本全部执行完成", flush=True)

    except Exception as err:
        print(f"❌ 脚本执行失败：{repr(err)}", flush=True)
        raise err

if __name__ == "__main__":
    main()
