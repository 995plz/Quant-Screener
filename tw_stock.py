import sys
import os
import requests
import traceback
import re  # 🔥 確保載入正則表達式，用來精準抓取 4 位數股號

try:
    print("正在檢查環境並載入套件...")
    from tradingview_screener import Query
    import pandas as pd
    import datetime

    print("正在同步最新中文股名與交易所資訊...")
    name_dict = {}
    exchange_dict = {}  # 🔥 新增：專門記錄每支股票是 TWSE 還是 TPEX
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }

    # 1. 官方 API (上市 TWSE)
    try:
        res_twse = requests.get("https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL", headers=headers, timeout=15)
        if res_twse.status_code == 200:
            for item in res_twse.json():
                code = str(item['Code']).strip()
                name_dict[code] = str(item['Name']).strip()
                exchange_dict[code] = "TWSE"
    except: pass

    # 2. 官方 API (上櫃 TPEX)
    try:
        res_tpex = requests.get("https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes", headers=headers, timeout=15)
        if res_tpex.status_code == 200:
            for item in res_tpex.json():
                code = str(item['SecuritiesCompanyCode']).strip()
                name_dict[code] = str(item['CompanyName']).strip()
                exchange_dict[code] = "TPEX"
    except: pass

    # 3. FinMind 備援
    try:
        res_fm = requests.get("https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockInfo", timeout=15)
        if res_fm.status_code == 200:
            for item in res_fm.json().get('data', []):
                code = str(item.get('stock_id')).strip()
                name_dict[code] = str(item.get('stock_name')).strip()
    except: pass

    # 4. 手動校正 (防止 API 阻擋時連錯交易所)
    name_dict.update({
        '4958': '臻頂', '6182': '合晶', '6274': '台燿', '8299': '群聯', '3293': '鈊象', '3105': '穩懋',
        '5483': '中美晶', '6488': '環球晶', '8069': '元太', '3529': '力旺', '5347': '世界', '5274': '信驊',
        '5371': '中光電', '6409': '旭隼', '3026': '禾伸堂', '8261': '富鼎', '4989': '榮科', '5328': '華容',
        '3055': '蔚華科', '8033': '雷虎', '1718': '中纖', '5314': '世紀', '8182': '加高', '7795': '長廣'
    })
    exchange_dict.update({
        '6182': 'TPEX', '6274': 'TPEX', '8299': 'TPEX', '3293': 'TPEX', '3105': 'TPEX',
        '5483': 'TPEX', '6488': 'TPEX', '8069': 'TPEX', '3529': 'TPEX', '5347': 'TPEX',
        '
