#!/usr/bin/env python3
"""
FishMya Game - Auto Scan + Exploit Bot (Thread-Safe Fixed)
Author: GHOST
Version: 18.4 - Single Thread WS + Slow Rate
"""

import asyncio
import aiohttp
import json
import time
import sys
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging
import msgpack
import ssl
import websocket
import threading

# ==================== CONFIGURATION ====================
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
GAME_ACCESS_TOKEN = os.environ.get("GAME_ACCESS_TOKEN", "")
WS_URL = "wss://api-fishmcloud.ugame.vn:2083"

WS_HEADERS = [
    "User-Agent: Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Origin: https://fishmya.ugame.vn",
    "Accept-Language: my-MM,my;q=0.9,en-US;q=0.8,en;q=0.7",
    "X-Requested-With: com.mytel.myid"
]

# Rate control — server ကို မဖိအားပေးအောင်
REQUESTS_PER_CYCLE = 3       # တစ်ခါ ၃ ခုပဲ ပို့
SLEEP_BETWEEN_CYCLES = 0.05  # 50ms စောင့်
PING_INTERVAL = 5            # 5 စက္ကန့်တစ်ခါ ping

# ==================== LOGGING ====================
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# ==================== TELEGRAM API ====================
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
last_update_id = 0
owner_chat_id = None

# ==================== SCAN ROUTES ====================
SCAN_ROUTES = [
    {"route": "claimItemOnline", "data": {"package": 1}, "desc": "Pkg 1"},
    {"route": "claimItemOnline", "data": {"package": 2}, "desc": "Pkg 2"},
    {"route": "claimItemOnline", "data": {"package": 3}, "desc": "Pkg 3"},
    {"route": "claimItemOnline", "data": {"package": 4}, "desc": "Pkg 4"},
    {"route": "claimItemOnline", "data": {"package": 5}, "desc": "Pkg 5"},
    {"route": "claimItemOnline", "data": {"package": 6}, "desc": "Pkg 6"},
    {"route": "claimItemOnline", "data": {"package": 7}, "desc": "Pkg 7"},
    {"route": "claimItemOnline", "data": {"package": 8}, "desc": "Pkg 8"},
    {"route": "claimItemOnline", "data": {"package": 9}, "desc": "Pkg 9"},
    {"route": "claimItemOnline", "data": {"package": 10}, "desc": "Pkg 10"},
    {"route": "claimDaily", "data": {}, "desc": "Daily"},
    {"route": "claimDailyReward", "data": {}, "desc": "Daily Reward"},
    {"route": "dailyClaim", "data": {}, "desc": "Daily Claim"},
    {"route": "claimLogin", "data": {}, "desc": "Login"},
    {"route": "loginReward", "data": {}, "desc": "Login Reward"},
    {"route": "dailyBonus", "data": {}, "desc": "Daily Bonus"},
    {"route": "checkin", "data": {}, "desc": "Check-in"},
    {"route": "dailyCheckin", "data": {}, "desc": "Daily Check-in"},
    {"route": "claimGift", "data": {}, "desc": "Gift"},
    {"route": "openGift", "data": {}, "desc": "Open Gift"},
    {"route": "receiveGift", "data": {}, "desc": "Receive Gift"},
    {"route": "giftBox", "data": {}, "desc": "Gift Box"},
    {"route": "openBox", "data": {}, "desc": "Open Box"},
    {"route": "claimBox", "data": {}, "desc": "Claim Box"},
    {"route": "claimReward", "data": {}, "desc": "Claim Reward"},
    {"route": "getReward", "data": {}, "desc": "Get Reward"},
    {"route": "receiveReward", "data": {}, "desc": "Receive Reward"},
    {"route": "claimBonus", "data": {}, "desc": "Claim Bonus"},
    {"route": "getBonus", "data": {}, "desc": "Get Bonus"},
    {"route": "bonusReward", "data": {}, "desc": "Bonus Reward"},
    {"route": "claimItem", "data": {}, "desc": "Claim Item"},
    {"route": "useItem", "data": {"type": 1}, "desc": "Use Item 1"},
    {"route": "useItem", "data": {"type": 2}, "desc": "Use Item 2"},
    {"route": "useItem", "data": {"type": 3}, "desc": "Use Item 3"},
    {"route": "useItem", "data": {"type": 4}, "desc": "Use Item 4"},
    {"route": "useItem", "data": {"type": 5}, "desc": "Use Item 5"},
    {"route": "useItem", "data": {"type": 6}, "desc": "Use Item 6"},
    {"route": "claimMission", "data": {}, "desc": "Mission"},
    {"route": "missionReward", "data": {}, "desc": "Mission Reward"},
    {"route": "completeMission", "data": {}, "desc": "Complete Mission"},
    {"route": "taskReward", "data": {}, "desc": "Task Reward"},
    {"route": "claimTask", "data": {}, "desc": "Claim Task"},
    {"route": "questReward", "data": {}, "desc": "Quest Reward"},
    {"route": "levelReward", "data": {}, "desc": "Level Reward"},
    {"route": "levelUpReward", "data": {}, "desc": "Level Up"},
    {"route": "claimLevel", "data": {}, "desc": "Claim Level"},
    {"route": "eventReward", "data": {}, "desc": "Event Reward"},
    {"route": "claimEvent", "data": {}, "desc": "Claim Event"},
    {"route": "eventBonus", "data": {}, "desc": "Event Bonus"},
    {"route": "onlineReward", "data": {}, "desc": "Online Reward"},
    {"route": "onlineBonus", "data": {}, "desc": "Online Bonus"},
    {"route": "timeReward", "data": {}, "desc": "Time Reward"},
    {"route": "hourlyReward", "data": {}, "desc": "Hourly Reward"},
    {"route": "catchFish", "data": {}, "desc": "Catch Fish"},
    {"route": "fishReward", "data": {}, "desc": "Fish Reward"},
    {"route": "claimFish", "data": {}, "desc": "Claim Fish"},
    {"route": "exchange", "data": {}, "desc": "Exchange"},
    {"route": "exchangeItem", "data": {}, "desc": "Exchange Item"},
    {"route": "convert", "data": {}, "desc": "Convert"},
    {"route": "getBalance", "data": {}, "desc": "Get Balance"},
    {"route": "refreshCash", "data": {}, "desc": "Refresh Cash"},
    {"route": "syncCash", "data": {}, "desc": "Sync Cash"},
    {"route": "updateCash", "data": {}, "desc": "Update Cash"},
    {"route": "reloadCash", "data": {}, "desc": "Reload Cash"},
]

# ==================== STATE ====================
bot_state = {
    'scanning': False,
    'exploiting': False,
    'is_running': False,
    'found_routes': [],
    'total_claimed': 0,
    'current_balance': 0,
    'start_balance': 0,
    'claims_done': 0,
    'total_claims': 0,
    'errors': 0,
    'last_error': 'None',
    'login_ok': False,
    'connected': False,
    'route_stats': {},
    'last_coin_time': None,
    'auto_restart_count': 0,
    'start_time': None,
    'scan_results': {},
    'best_route': None,
    'best_route_coins': 0,
    'total_coins_all': 0,
    'coins_per_second': 0,
    'max_requests_per_second': 0,
    'current_requests_per_second': 0,
    'rps_test_result': {},
}

state_lock = threading.Lock()

# ==================== UTILS ====================
def extract_coins(decoded: Dict) -> int:
    if not decoded:
        return 0
    coin_keys = ['cash', 'coin', 'coins', 'gold', 'reward', 'amount',
                 'changeCash', 'newCash', 'balance', 'bonus', 'gift',
                 'point', 'points', 'money', 'diamond', 'gem', 'totalCash']
    def search(obj, depth=0):
        if depth > 10:
            return 0
        if isinstance(obj, dict):
            for key, value in obj.items():
                key_lower = key.lower()
                if any(k in key_lower for k in coin_keys):
                    if isinstance(value, (int, float)) and value > 0:
                        return int(value)
                    elif isinstance(value, str) and value.isdigit() and int(value) > 0:
                        return int(value)
                result = search(value, depth + 1)
                if result > 0:
                    return result
        elif isinstance(obj, list):
            for item in obj:
                result = search(item, depth + 1)
                if result > 0:
                    return result
        return 0
    return search(decoded)

async def send_telegram(chat_id: str, text: str, keyboard=None):
    url = f"{TELEGRAM_API}/sendMessage"
    payload = {'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'}
    if keyboard:
        payload['reply_markup'] = keyboard
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=15) as response:
                if response.status == 200:
                    return True
                else:
                    logger.error(f"Telegram failed: {response.status}")
                    return False
    except Exception as e:
        logger.error(f"Telegram error: {e}")
        return False

async def get_updates(offset: int = 0) -> List[Dict]:
    url = f"{TELEGRAM_API}/getUpdates"
    params = {'timeout': 30, 'offset': offset}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=35) as response:
                data = await response.json()
                if data.get('ok'):
                    return data.get('result', [])
    except:
        pass
    return []

def get_main_keyboard():
    return json.dumps({
        "inline_keyboard": [
            [{"text": "🛑 Stop", "callback_data": "stop"},
             {"text": "📊 Status", "callback_data": "status"}],
            [{"text": "💰 Balance", "callback_data": "balance"},
             {"text": "📈 Stats", "callback_data": "stats"}]
        ]
    })

# ==================== CONNECT & LOGIN (FIXED) ====================
def connect_and_login():
    try:
        ws = websocket.create_connection(
            WS_URL,
            header=WS_HEADERS,
            sslopt={"cert_reqs": ssl.CERT_NONE},
            timeout=30
        )
        ws.send(msgpack.packb({
            "route": "mytelLogin",
            "data": {"accessToken": GAME_ACCESS_TOKEN, "language": "my"},
            "msgId": 1
        }, use_bin_type=True), opcode=websocket.ABNF.OPCODE_BINARY)

        ws.settimeout(15)
        for _ in range(30):
            try:
                m = ws.recv()
                d = msgpack.unpackb(m, raw=False)
                inner = d.get("data", {})
                if not isinstance(inner, dict):
                    inner = {}
                if d.get("msgId") == 1 or d.get("route") == "mytelLogin":
                    if inner.get("ok"):
                        return ws, inner
                    else:
                        logger.error(f"Login rejected: {inner}")
                        try:
                            ws.close()
                        except:
                            pass
                        return None, None
            except websocket.WebSocketTimeoutException:
                continue
            except Exception as e:
                logger.error(f"Login recv error: {e}")
                break
        try:
            ws.close()
        except:
            pass
        return None, None
    except Exception as e:
        logger.error(f"Connection error: {e}")
        return None, None

# ==================== TEST BEST ROUTE ====================
def test_best_route_performance(ws, best_route):
    if not ws or not ws.connected or not best_route:
        return None
    logger.info(f"🧪 Testing best route: {best_route['desc']} with 50 requests...")
    route_name = best_route['route']
    route_data = best_route['data']
    desc = best_route['desc']
    total_coins = 0
    successful_requests = 0
    start_time = time.time()
    msg_id = 10000
    for i in range(50):
        try:
            ws.send(msgpack.packb({
                "route": route_name,
                "data": route_data,
                "msgId": msg_id
            }, use_bin_type=True), opcode=websocket.ABNF.OPCODE_BINARY)
            msg_id += 1
        except:
            break
        time.sleep(0.02)
    ws.settimeout(0.5)
    response_end_time = time.time() + 3
    while time.time() < response_end_time:
        try:
            m = ws.recv()
            d = msgpack.unpackb(m, raw=False)
            coins = extract_coins(d)
            if coins > 0:
                total_coins += coins
                successful_requests += 1
        except websocket.WebSocketTimeoutException:
            continue
        except:
            break
    elapsed_time = time.time() - start_time
    if elapsed_time == 0:
        elapsed_time = 0.1
    coins_per_second = int(total_coins / elapsed_time) if total_coins > 0 else 0
    requests_per_second = int(successful_requests / elapsed_time) if successful_requests > 0 else 0
    result = {
        'route': desc,
        'total_requests': 50,
        'successful': successful_requests,
        'total_coins': total_coins,
        'elapsed_time': round(elapsed_time, 2),
        'coins_per_second': coins_per_second,
        'requests_per_second': requests_per_second,
        'avg_coins_per_request': int(total_coins / successful_requests) if successful_requests > 0 else 0
    }
    bot_state['rps_test_result'] = result
    logger.info(f"📊 Test Result: {desc} → {total_coins} coins, {coins_per_second} coins/s, {requests_per_second} rps")
    return result

# ==================== SCAN (UNCHANGED) ====================
def scan_routes():
    global bot_state
    bot_state['scanning'] = True
    bot_state['found_routes'] = []
    bot_state['scan_results'] = {}
    bot_state['best_route'] = None
    bot_state['best_route_coins'] = 0
    bot_state['total_coins_all'] = 0

    ws, login_data = connect_and_login()
    if not ws or not login_data:
        bot_state['scanning'] = False
        return False

    bot_state['login_ok'] = True
    bot_state['current_balance'] = login_data.get("cash", 0)
    bot_state['start_balance'] = login_data.get("cash", 0)

    ws.send(msgpack.packb({
        "route": "play",
        "data": {"roomId": 1},
        "msgId": 2
    }, use_bin_type=True), opcode=websocket.ABNF.OPCODE_BINARY)
    time.sleep(1)

    msg_id = 1000
    found = []
    scan_stats = {}

    logger.info("🔍 Scanning individual routes...")
    for route_info in SCAN_ROUTES:
        route_name = route_info['route']
        route_data = route_info['data']
        desc = route_info['desc']

        ws.send(msgpack.packb({
            "route": route_name,
            "data": route_data,
            "msgId": msg_id
        }, use_bin_type=True), opcode=websocket.ABNF.OPCODE_BINARY)

        ws.settimeout(0.5)
        coins_found = 0
        try:
            while True:
                m = ws.recv()
                d = msgpack.unpackb(m, raw=False)
                if d.get("route") == "reloadCash":
                    change = d.get("data", {}).get("changeCash", 0)
                    if change > 0:
                        coins_found = change
                        break
                if d.get("msgId") == msg_id:
                    coins_found = extract_coins(d)
                    if coins_found > 0:
                        break
        except websocket.WebSocketTimeoutException:
            pass
        except:
            pass
        msg_id += 1

        repeatable = False
        if coins_found > 0:
            ws.send(msgpack.packb({
                "route": route_name,
                "data": route_data,
                "msgId": msg_id
            }, use_bin_type=True), opcode=websocket.ABNF.OPCODE_BINARY)
            ws.settimeout(0.5)
            repeat_coins = 0
            try:
                while True:
                    m = ws.recv()
                    d = msgpack.unpackb(m, raw=False)
                    if d.get("route") == "reloadCash":
                        change = d.get("data", {}).get("changeCash", 0)
                        if change > 0:
                            repeat_coins = change
                            break
                    if d.get("msgId") == msg_id:
                        repeat_coins = extract_coins(d)
                        if repeat_coins > 0:
                            break
            except websocket.WebSocketTimeoutException:
                pass
            except:
                pass
            msg_id += 1
            repeatable = repeat_coins > 0

        scan_stats[desc] = {
            'coins': coins_found,
            'repeatable': repeatable,
            'route': route_name,
            'data': route_data
        }

        if coins_found > 0:
            logger.info(f"📊 {desc}: {coins_found} coins (Repeat: {repeatable})")
            if repeatable:
                found.append({'route': route_name, 'data': route_data, 'desc': desc,
                              'coins': coins_found, 'repeatable': True})

        time.sleep(0.05)

    best_route = max(found, key=lambda x: x['coins']) if found else None
    test_result = None
    if best_route:
        bot_state['best_route'] = best_route
        bot_state['best_route_coins'] = best_route['coins']
        logger.info(f"🏆 Best route: {best_route['desc']} - {best_route['coins']} coins")
        test_result = test_best_route_performance(ws, best_route)
        if test_result:
            bot_state['max_requests_per_second'] = test_result['requests_per_second']
            bot_state['coins_per_second'] = test_result['coins_per_second']

    total_all = sum(r['coins'] for r in found)
    bot_state['total_coins_all'] = total_all
    logger.info(f"📊 Total coins all routes: {total_all}")

    try:
        ws.close()
    except:
        pass
    bot_state['found_routes'] = [r for r in found if r['repeatable']]
    bot_state['scan_results'] = scan_stats
    bot_state['scanning'] = False

    if owner_chat_id:
        summary = f"🔍 *Scan Complete!*\n\n"
        summary += f"🏆 Best Route: {best_route['desc'] if best_route else 'None'} - {bot_state['best_route_coins']} coins\n"
        summary += f"📊 Total All Routes: {total_all} coins\n"
        summary += f"📦 Found Routes: {len(bot_state['found_routes'])}\n\n"
        if test_result:
            summary += f"🧪 *Test with 50 Requests:*\n"
            summary += f"  • Coins/s: {test_result['coins_per_second']:,}\n"
            summary += f"  • Requests/s: {test_result['requests_per_second']}\n"
            summary += f"  • Time: {test_result['elapsed_time']}s\n"
            summary += f"  • Total Coins: {test_result['total_coins']:,}\n"
        asyncio.run(send_telegram(owner_chat_id, summary))

    return len(bot_state['found_routes']) > 0

# ==================== EXPLOIT (SINGLE-THREAD + SLOW RATE) ====================
def exploit_loop():
    global bot_state
    if not bot_state['found_routes']:
        return

    bot_state['exploiting'] = True
    bot_state['is_running'] = True
    bot_state['total_claimed'] = 0
    bot_state['claims_done'] = 0
    bot_state['errors'] = 0
    bot_state['auto_restart_count'] = 0
    bot_state['start_time'] = datetime.now()
    bot_state['route_stats'] = {}

    for r in bot_state['found_routes']:
        bot_state['route_stats'][r['desc']] = {'sent': 0, 'received': 0, 'coins': 0}

    best_route = bot_state['best_route']

    if owner_chat_id:
        exploit_msg = (
            f"⚡ *Exploit Started!*\n\n"
            f"🏆 Best Route: {best_route['desc'] if best_route else 'None'} ({bot_state['best_route_coins']} coins)\n"
            f"📦 Using: {len(bot_state['found_routes'])} routes\n"
            f"⏱️ Rate: {REQUESTS_PER_CYCLE} req / {int(SLEEP_BETWEEN_CYCLES*1000)}ms\n\n"
            f"💡 Use *Status* button to check progress."
        )
        asyncio.run(send_telegram(owner_chat_id, exploit_msg, get_main_keyboard()))

    retry_delay = 5
    while bot_state['is_running']:
        ws, login_data = connect_and_login()
        if not ws or not login_data:
            bot_state['errors'] += 1
            bot_state['last_error'] = "Login failed"
            bot_state['connected'] = False
            logger.error(f"Login failed, retrying in {retry_delay}s...")
            time.sleep(retry_delay)
            retry_delay = min(retry_delay + 5, 30)
            continue
        else:
            retry_delay = 5

        bot_state['login_ok'] = True
        bot_state['connected'] = True
        bot_state['current_balance'] = login_data.get("cash", bot_state['current_balance'])

        # enter room
        try:
            ws.send(msgpack.packb({
                "route": "play",
                "data": {"roomId": 1},
                "msgId": 2
            }, use_bin_type=True), opcode=websocket.ABNF.OPCODE_BINARY)
        except:
            pass
        time.sleep(1)

        msg_id = 5000
        last_coin_time = time.time()
        coins_in_interval = 0
        interval_start = time.time()
        request_count = 0
        connection_broken = False
        last_ping_time = time.time()

        try:
            while bot_state['is_running'] and not connection_broken:
                # ---- Ping in main loop (no separate thread) ----
                if time.time() - last_ping_time >= PING_INTERVAL:
                    try:
                        ws.send(msgpack.packb({
                            "route": "ping",
                            "data": {},
                            "msgId": 0
                        }, use_bin_type=True), opcode=websocket.ABNF.OPCODE_BINARY)
                        last_ping_time = time.time()
                    except:
                        pass

                # ---- Send small batch ----
                for _ in range(REQUESTS_PER_CYCLE):
                    if not bot_state['is_running']:
                        break
                    if best_route:
                        try:
                            ws.send(msgpack.packb({
                                "route": best_route['route'],
                                "data": best_route['data'],
                                "msgId": msg_id
                            }, use_bin_type=True), opcode=websocket.ABNF.OPCODE_BINARY)
                        except Exception as e:
                            logger.error(f"Send error: {e}")
                            connection_broken = True
                            break
                        request_count += 1
                        msg_id += 1
                        with state_lock:
                            bot_state['route_stats'][best_route['desc']]['sent'] += 1
                            bot_state['claims_done'] += 1

                if connection_broken:
                    break

                # ---- Receive window ----
                ws.settimeout(0.15)
                recv_end = time.time() + 0.15
                while time.time() < recv_end:
                    try:
                        m = ws.recv()
                        if not m:
                            continue
                        d = msgpack.unpackb(m, raw=False)
                        route = d.get("route", "")
                        inner = d.get("data", {})
                        if route == "reloadCash":
                            change = inner.get("changeCash", 0)
                            if change > 0:
                                with state_lock:
                                    bot_state['total_claimed'] += change
                                    bot_state['current_balance'] = inner.get("newCash", bot_state['current_balance'])
                                    coins_in_interval += change
                                    last_coin_time = time.time()
                                for ri in bot_state['found_routes']:
                                    if abs(change - ri['coins']) <= 50:
                                        with state_lock:
                                            bot_state['route_stats'][ri['desc']]['received'] += 1
                                            bot_state['route_stats'][ri['desc']]['coins'] += change
                                        break
                    except websocket.WebSocketTimeoutException:
                        break
                    except ssl.SSLError as e:
                        logger.error(f"SSL error: {e}")
                        connection_broken = True
                        break
                    except Exception as e:
                        logger.error(f"Recv error: {e}")
                        connection_broken = True
                        break

                if connection_broken:
                    break

                # ---- CPS every 1s ----
                if time.time() - interval_start >= 1.0:
                    cps = coins_in_interval / (time.time() - interval_start)
                    with state_lock:
                        bot_state['coins_per_second'] = cps
                        bot_state['current_requests_per_second'] = request_count / (time.time() - interval_start)
                    coins_in_interval = 0
                    interval_start = time.time()
                    request_count = 0

                # ---- Coins stopped 60s ----
                if time.time() - last_coin_time > 60:
                    logger.warning("⚠️ Coins stopped 60s! Reconnecting...")
                    bot_state['auto_restart_count'] += 1
                    connection_broken = True
                    break

                time.sleep(SLEEP_BETWEEN_CYCLES)

        except Exception as e:
            logger.error(f"Exploit error: {e}")
            bot_state['errors'] += 1
            bot_state['last_error'] = str(e)
            bot_state['auto_restart_count'] += 1
        finally:
            try:
                ws.close()
            except Exception:
                pass
            bot_state['connected'] = False

        if bot_state['is_running']:
            logger.info(f"🔄 Auto restart #{bot_state['auto_restart_count']}...")
            time.sleep(8)

    bot_state['exploiting'] = False

# ==================== AUTO MAIN LOOP ====================
def auto_main_loop():
    while True:
        try:
            logger.info("🔄 Starting scan...")
            success = scan_routes()
            if success:
                logger.info("✅ Scan found routes. Cooling down 5s before exploit...")
                time.sleep(5)
                logger.info("⚡ Starting exploit...")
                exploit_loop()
            else:
                logger.warning("❌ Scan found no routes, restarting in 10s...")
                time.sleep(10)
        except Exception as e:
            logger.error(f"Auto loop error: {e}")
            time.sleep(5)

# ==================== TELEGRAM HANDLERS ====================
async def process_command(chat_id: str, text: str):
    global owner_chat_id
    text = text.strip()
    if text.startswith('/start'):
        if owner_chat_id is None:
            owner_chat_id = chat_id
        best = bot_state.get('best_route')
        best_desc = best.get('desc') if isinstance(best, dict) else 'None'
        status_text = (
            "🤖 *Auto FishMya Bot*\n\n"
            f"🏆 Best Route: {best_desc}\n"
            f"💰 Balance: {bot_state.get('current_balance', 0):,}\n"
            f"📈 Gained: +{bot_state.get('total_claimed', 0):,}\n"
            f"📊 CPS: {int(bot_state.get('coins_per_second', 0)):,}\n"
            f"🚀 RPS: {int(bot_state.get('current_requests_per_second', 0))}\n\n"
            "Use buttons to control."
        )
        await send_telegram(chat_id, status_text, get_main_keyboard())
    elif text in ['/stop']:
        bot_state['is_running'] = False
        await send_telegram(chat_id, "🛑 *Stopped by user.*")
    elif text in ['/status']:
        status = "🟢 Running" if bot_state['is_running'] else "🔴 Stopped"
        elapsed = (datetime.now() - bot_state['start_time']).seconds if bot_state['start_time'] else 0
        text_msg = (
            f"📊 *Status*\n\n"
            f"State: {status}\n"
            f"Routes: {len(bot_state['found_routes'])}\n"
            f"Claims: {bot_state['claims_done']:,}\n"
            f"💰 Balance: {bot_state['current_balance']:,}\n"
            f"📈 Gained: +{bot_state['total_claimed']:,}\n"
            f"📈 CPS: {int(bot_state.get('coins_per_second', 0)):,}\n"
            f"🚀 RPS: {int(bot_state.get('current_requests_per_second', 0))}\n"
            f"🔄 Restarts: {bot_state['auto_restart_count']}\n"
            f"⏱️ Elapsed: {elapsed}s"
        )
        await send_telegram(chat_id, text_msg, get_main_keyboard())
    elif text in ['/balance']:
        await send_telegram(chat_id, f"💰 Balance: {bot_state['current_balance']:,}\n📈 Gained: +{bot_state['total_claimed']:,}")
    elif text in ['/stats']:
        best = bot_state.get('best_route')
        best_desc = best.get('desc') if isinstance(best, dict) else 'None'
        stats_text = "📊 *Detailed Stats*\n\n"
        stats_text += f"🏆 Best Route: {best_desc} - {bot_state.get('best_route_coins', 0)} coins\n"
        stats_text += f"📊 Total All Routes: {bot_state.get('total_coins_all', 0)} coins\n"
        stats_text += f"🚀 Max RPS: {bot_state.get('max_requests_per_second', 0)}\n"
        stats_text += f"📈 Current CPS: {int(bot_state.get('coins_per_second', 0)):,}\n"
        test_result = bot_state.get('rps_test_result', {}) or {}
        if test_result:
            stats_text += "\n🧪 *Test Result:*\n"
            stats_text += f"  • Coins/s: {test_result.get('coins_per_second', 0):,}\n"
            stats_text += f"  • Requests/s: {test_result.get('requests_per_second', 0)}\n"
            stats_text += f"  • Time: {test_result.get('elapsed_time', 0)}s\n"
            stats_text += f"  • Total Coins: {test_result.get('total_coins', 0):,}\n"
        stats_text += "\n📊 Route Stats:\n"
        for desc, s in (bot_state.get('route_stats', {}) or {}).items():
            stats_text += f"  • {desc}: {s.get('coins', 0)} coins\n"
        await send_telegram(chat_id, stats_text, get_main_keyboard())

async def handle_callback(chat_id: str, data: str):
    if data == "stop":
        bot_state['is_running'] = False
        await send_telegram(chat_id, "🛑 *Stopped.*")
    elif data == "status":
        await process_command(chat_id, "/status")
    elif data == "balance":
        await process_command(chat_id, "/balance")
    elif data == "stats":
        await process_command(chat_id, "/stats")

# ==================== MAIN ====================
async def main():
    global last_update_id, owner_chat_id
    print("Starting auto FishMya bot...")
    threading.Thread(target=auto_main_loop, daemon=True).start()
    while True:
        try:
            updates = await get_updates(last_update_id + 1)
            for update in updates:
                if not isinstance(update, dict):
                    continue
                update_id = update.get('update_id', 0)
                if update_id > last_update_id:
                    last_update_id = update_id

                cb = update.get('callback_query')
                if isinstance(cb, dict):
                    msg = cb.get('message') or {}
                    chat = msg.get('chat') or {}
                    chat_id = str(chat.get('id', ''))
                    data = cb.get('data', '')
                    if chat_id and data:
                        await handle_callback(chat_id, data)
                    continue

                msg = update.get('message')
                if isinstance(msg, dict):
                    chat = msg.get('chat') or {}
                    chat_id = str(chat.get('id', ''))
                    text = msg.get('text', '')
                    if chat_id and text:
                        if owner_chat_id is None:
                            owner_chat_id = chat_id
                        await process_command(chat_id, text)
            await asyncio.sleep(2)
        except KeyboardInterrupt:
            bot_state['is_running'] = False
            break
        except Exception as e:
            logger.error(f"Main loop error: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
