import sys
import os
import requests

try:
    print("正在檢查環境並載入套件...")
    from tradingview_screener import Query
    import pandas as pd
    import datetime

    # --- 強化版中文名稱抓取 ---
    print("正在同步最新中文股名...")
    name_dict = {}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        res_fm = requests.get("https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockInfo", timeout=10)
        if res_fm.status_code == 200:
            for item in res_fm.json().get('data', []):
                name_dict[str(item.get('stock_id')).strip()] = str(item.get('stock_name')).strip()
    except:
        pass

    try:
        res_twse = requests.get("https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL", headers=headers, timeout=10)
        if res_twse.status_code == 200:
            for item in res_twse.json():
                name_dict[str(item['Code']).strip()] = str(item['Name']).strip()
                
        res_tpex = requests.get("https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes", headers=headers, timeout=10)
        if res_tpex.status_code == 200:
            for item in res_tpex.json():
                name_dict[str(item['SecuritiesCompanyCode']).strip()] = str(item['CompanyName']).strip()
    except:
        pass

    name_dict.update({
        '4958': '臻頂'
    })

    # --- 抓取 TradingView 數據 ---
    print("連線至 TradingView 抓取台股成交值前 200 名資料...")

    columns = [
        'name',                      
        'description',               
        'close',                     
        'change',                    
        'Perf.W',                    
        'volume',                    
        'Value.Traded',              
        'relative_volume_10d_calc',  
        'ADR',                       
        'market_cap_basic'           
    ]

    query = (Query()
        .set_markets('taiwan')
        .select(*columns)
        .order_by('Value.Traded', ascending=False)
        .limit(200)
    )

    df = query.get_scanner_data()[1]
    df['ADR'] = (df['ADR'] / df['close']) * 100
    df = df.rename(columns={
        'name': 'Symbol',
        'description': 'TV_Name',
        'close': 'Price',
        'change': 'Chg %',
        'Perf.W': 'Perf % 1W',
        'volume': 'Vol',
        'Value.Traded': 'Price x vol',
        'relative_volume_10d_calc': 'Rel vol',
        'ADR': 'ADR %',
        'market_cap_basic': 'Mkt cap'
    })

    # 移除不需要的 ticker 欄位 (不再需要超連結)
    if 'ticker' in df.columns:
        df = df.drop(columns=['ticker'])

    # 翻譯與合併股名
    df['ChineseName'] = df['Symbol'].astype(str).map(name_dict).fillna(df['TV_Name'])
    df['Symbol'] = df['Symbol'].astype(str) + " " + df['ChineseName']
    df = df.drop(columns=['TV_Name', 'ChineseName'])

    df.index = range(1, len(df) + 1)
    df.index.name = '排名'

    # 取出一週表現前 20 名
    top20_perf_df = df.nlargest(20, 'Perf % 1W')
    top20_perf_df = top20_perf_df.sort_values(by='Price x vol', ascending=False)
    top20_perf_df.index = range(1, 21)
    top20_perf_df.index.name = '強勢排名'

    # --- 數據格式化與上色 ---
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
    top20_html_df = format_df_for_html(top20_perf_df
