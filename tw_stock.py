import sys
import os
import requests
import traceback

try:
    print("正在檢查環境並載入套件...")
    from tradingview_screener import Query
    import pandas as pd
    import datetime

    print("正在同步最新中文股名...")
    name_dict = {}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }

    try:
        res_fm = requests.get("https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockInfo", timeout=15)
        if res_fm.status_code == 200:
            for item in res_fm.json().get('data', []):
                name_dict[str(item.get('stock_id')).strip()] = str(item.get('stock_name')).strip()
    except:
        pass

    try:
        res_twse = requests.get("https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL", headers=headers, timeout=15)
        if res_twse.status_code == 200:
            for item in res_twse.json():
                name_dict[str(item['Code']).strip()] = str(item['Name']).strip()
                
        res_tpex = requests.get("https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes", headers=headers, timeout=15)
        if res_tpex.status_code == 200:
            for item in res_tpex.json():
                name_dict[str(item['SecuritiesCompanyCode']).strip()] = str(item['CompanyName']).strip()
    except:
        pass

    name_dict.update({
        '4958': '臻頂', '6182': '合晶', '6274': '台燿', '8299': '群聯', '3293': '鈊象', '3105': '穩懋',
        '5483': '中美晶', '6488': '環球晶', '8069': '元太', '3529': '力旺', '5347': '世界', '5274': '信驊',
        '5371': '中光電', '6409': '旭隼', '3026': '禾伸堂', '8261': '富鼎', '4989': '榮科', '5328': '華容',
        '3055': '蔚華科', '8033': '雷虎', '1718': '中纖', '5314': '世紀', '8182': '加高', '7795': '長廣'
    })

    print("連線至 TradingView 抓取台股成交值前 200 名資料...")

    columns = [
        'name', 'description', 'close', 'change', 'Perf.W', 'volume', 
        'Value.Traded', 'relative_volume_10d_calc', 'ADR', 'market_cap_basic'
    ]

    query = (Query().set_markets('taiwan').select(*columns).order_by('Value.Traded', ascending=False).limit(200))
    df = query.get_scanner_data()[1]
    
    # 🔥 關鍵修復：完全不動原本的 ticker 欄位，保留 API 給的最精準代碼 (TWSE/TPEX)

    df['ADR'] = (df['ADR'] / df['close']) * 100
    df = df.rename(columns={
        'name': 'Symbol', 'description': 'TV_Name', 'close': 'Price',
        'change': 'Chg %', 'Perf.W': 'Perf % 1W', 'volume': 'Vol',
        'Value.Traded': 'Price x vol', 'relative_volume_10d_calc': 'Rel vol',
        'ADR': 'ADR %', 'market_cap_basic': 'Mkt cap'
    })

    df['ChineseName'] = df['Symbol'].astype(str).map(name_dict).fillna(df['TV_Name'])
    df['Symbol'] = df['Symbol'].astype(str) + " " + df['ChineseName']
    df = df.drop(columns=['TV_Name', 'ChineseName'])

    df.index = range(1, len(df) + 1)
    df.index.name = '排名'

    top20_perf_df = df.nlargest(20, 'Perf % 1W')
    top20_perf_df = top20_perf_df.sort_values(by='Price x vol', ascending=False)
    top20_perf_df.index = range(1, 21)
    top20_perf_df.index.name = '強勢排名'

    def color_pct(val):
        if pd.isna(val): return ""
        try:
            v = float(val)
            color = "#089981" if v > 0 else "#f23645" if v < 0 else "#d1d4dc"
            sign = "+" if v > 0 else ""
            return f'<span style="color: {color};">{sign}{v:.2f}%</span>'
        except:
            return val

    def format_large_num(val):
        if pd.isna(val): return ""
        try:
            v = float(val)
            if v >= 1e9: return f"{v/1e9:.2f}B"
            if v >= 1e6: return f"{v/1e6:.2f}M"
            return f"{v:,.0f}"
        except:
            return val

    def format_df_for_html(input_df):
        out_df = input_df.copy()
        
        # 轉換為藍色超連結
        if 'ticker' in out_df.columns:
            out_df['Symbol'] = out_df.apply(
                lambda row: f'<a href="https://www.tradingview.com/chart/?symbol={row["ticker"]}" target="_blank" class="symbol-link">{row["Symbol"]}</a>', axis=1
            )
            out_df = out_df.drop(columns=['ticker'])
        
        out_df['Price'] = out_df['Price'].apply(lambda x: f"${x:,.2f}" if pd.notnull(x) else "")
        out_df['Chg %'] = out_df['Chg %'].apply(color_pct)
        out_df['Perf % 1W'] = out_df['Perf % 1W'].apply(color_pct)
        out_df['Vol'] = out_df['Vol'].apply(format_large_num)
        out_df['Price x vol'] = out_df['Price x vol'].apply(format_large_num)
        out_df['Mkt cap'] = out_df['Mkt cap'].apply(format_large_num)
        out_df['Rel vol'] = out_df['Rel vol'].apply(lambda x: f"{x:.2f}" if pd.notnull(x) else "")
        out_df['ADR %'] = out_df['ADR %'].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else "")
        return out_df

    main_html_df = format_df_for_html(df)
    top20_html_df = format_df_for_html(top20_perf_df)

    time_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    date_display = datetime.datetime.now().strftime("%Y-%m-%d")
    
    html_content = f"""<!DOCTYPE html><html lang="zh-TW"><head><meta charset="UTF-8"><title>TW Top 200 Screener</title><style>body {{ background-color: #131722; color: #d1d4dc; font-family: -apple-system, sans-serif; padding: 30px; margin: 0; }} .header-title {{ color: #ffffff; margin-bottom: 20px; font-size: 24px; font-weight: bold; border-left: 4px solid #2962ff; padding-left: 10px; }} .sub-title {{ color: #ffffff; margin-bottom: 20px; font-size: 20px; font-weight: bold; border-left: 4px solid #f23645; padding-left: 10px; }} .section-divider {{ margin: 50px 0; border-top: 2px dashed #2a2e39; }} table {{ width: 100%; border-collapse: collapse; font-size: 13px; }} th {{ background-color: #1e222d; color: #868993; font-weight: normal; padding: 12px 10px; text-align: right; border-bottom: 1px solid #2a2e39; border-top: 1px solid #2a2e39; white-space: nowrap; }} th:nth-child(1), th:nth-child(2), td:nth-child(1), td:nth-child(2) {{ text-align: left; }} td {{ padding: 10px; border-bottom: 1px solid #2a2e39; text-align: right; }} tr:hover {{ background-color: #2a2e39; }} .symbol-link {{ color: #2962ff; text-decoration: none; font-weight: bold; }} .symbol-link:hover {{ text-decoration: underline; color: #739aff; }}</style></head><body><div class="header-title">台股成交值 Top 200 篩選報告 ({date_display})</div>{main_html_df.to_html(escape=False)}<div class="section-divider"></div><div class="sub-title">🔥 一周表現最強 Top 20 (按成交值排序)</div>{top20_html_df.to_html(escape=False)}</body></html>"""

    script_dir = os.path.dirname(os.path.abspath(__file__))
    history_dir = os.path.join(script_dir, "history")
    os.makedirs(history_dir, exist_ok=True) 

    excel_df =
