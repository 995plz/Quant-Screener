import sys
import os
import requests

try:
    print("正在檢查環境並載入套件...")
    from tradingview_screener import Query
    import pandas as pd
    import datetime

    # ---------------------------------------------------------
    # 向證交所與櫃買中心同步最新中文股名
    # ---------------------------------------------------------
    print("正在向證交所與櫃買中心同步最新中文股名...")
    name_dict = {}
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        res_twse = requests.get("https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL", headers=headers, timeout=10)
        if res_twse.status_code == 200:
            for item in res_twse.json():
                name_dict[str(item['Code']).strip()] = str(item['Name']).strip()
                
        res_tpex = requests.get("https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes", headers=headers, timeout=10)
        if res_tpex.status_code == 200:
            for item in res_tpex.json():
                name_dict[str(item['SecuritiesCompanyCode']).strip()] = str(item['CompanyName']).strip()
    except Exception as e:
        print(f"⚠️ 中文名稱同步發生部分錯誤，將自動使用備用名稱。({e})")

    # 手動校正清單
    name_dict.update({
        '4958': '臻頂'
    })

    # ---------------------------------------------------------
    # 抓取 TradingView 數據
    # ---------------------------------------------------------
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

    # 數值運算與欄位重命名
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

    if 'ticker' in df.columns:
        df = df.drop(columns=['ticker'])

    # 翻譯與合併股名
    df['ChineseName'] = df['Symbol'].astype(str).map(name_dict).fillna(df['TV_Name'])
    df['Symbol'] = df['Symbol'].astype(str) + " " + df['ChineseName']
    df = df.drop(columns=['TV_Name', 'ChineseName'])

    # 主表：維持前 200 名的排名
    df.index = range(1, len(df) + 1)
    df.index.name = '排名'

    # ---------------------------------------------------------
    # 🔥 新增：擷取一週表現前 20 名，並按成交值降冪排序
    # ---------------------------------------------------------
    # 1. 取出一週表現 (Perf % 1W) 最大的 20 檔
    top20_perf_df = df.nlargest(20, 'Perf % 1W')
    
    # 2. 將這 20 檔依照成交值 (Price x vol) 重新降冪排序
    top20_perf_df = top20_perf_df.sort_values(by='Price x vol', ascending=False)
    
    # 3. 重新賦予這 20 檔 1~20 的獨立排名標籤
    top20_perf_df.index = range(1, 21)
    top20_perf_df.index.name = '強勢排名'

    # ---------------------------------------------------------
    # 數據格式化與上色函數 (套用於 HTML)
    # ---------------------------------------------------------
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

    # 建立一個統一的格式化工具，讓主表跟附表都能用
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

    # 將兩個資料表各自格式化
    main_html_df = format_df_for_html(df)
    top20_html_df = format_df_for_html(top20_perf_df)

    # ---------------------------------------------------------
    # 建立 TradingView 風格的 HTML 模板
    # ---------------------------------------------------------
    time_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    date_display = datetime.datetime.now().strftime("%Y-%m-%d")
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <title>TW Top 200 Screener</title>
        <style>
            body {{
                background-color: #131722;
                color: #d1d4dc;
                font-family: -apple-system, BlinkMacSystemFont, 'Trebuchet MS', Roboto, Ubuntu, sans-serif;
                padding: 30px;
                margin: 0;
            }}
            .header-title {{ color: #ffffff; margin-bottom: 20px; font-size: 24px; font-weight: bold; border-left: 4px solid #2962ff; padding-left: 10px; }}
            .sub-title {{ color: #ffffff; margin-bottom: 20px; font-size: 20px; font-weight: bold; border-left: 4px solid #f23645; padding-left: 10px; }}
            .section-divider {{ margin: 50px 0; border-top: 2px dashed #2a2e39; }}
            
            table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
            th {{
                background-color: #1e222d;
                color: #868993;
                font-weight: normal;
                padding: 12px 10px;
                text-align: right;
                border-bottom: 1px solid #2a2e39;
                border-top: 1px solid #2a2e39;
                white-space: nowrap;
            }}
            th:nth-child(1), th:nth-child(2),
            td:nth-child(1), td:nth-child(2) {{ text-align: left; }}
            td {{ padding: 10px; border-bottom: 1px solid #2a2e39; text-align: right; }}
            tr:hover {{ background-color: #2a2e39; }}
            @media print {{
                body {{ background-color: #131722; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
                @page {{ size: A4 landscape; margin: 10mm; }}
            }}
        </style>
    </head>
    <body>
        <div class="header-title">台股成交值 Top 200 篩選報告 ({date_display})</div>
        {main_html_df.to_html(escape=False)}

        <div class="section-divider"></div>

        <div class="sub-title">🔥 一周表現最強 Top 20 (按成交值排序)</div>
        {top20_html_df.to_html(escape=False)}
    </body>
    </html>
    """

    # ---------------------------------------------------------
 # --- 存檔作業 (雲端加強版) ---
    script_dir = os.path.dirname(os.path.abspath(__file__))
    history_dir = os.path.join(script_dir, "history")
    os.makedirs(history_dir, exist_ok=True) 

    # 1. 儲存 Excel 與 HTML 歷史紀錄
    excel_path = os.path.join(history_dir, f"{time_str}_TW_Top200.xlsx")
    with pd.ExcelWriter(excel_path) as writer:
        df.to_excel(writer, sheet_name='Top 200 成交值')
        top20_perf_df.to_excel(writer, sheet_name='強勢 Top 20')
        
    history_html_path = os.path.join(history_dir, f"{time_str}_TW_Top200.html")
    with open(history_html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    # 2. 儲存最新 HTML (供首頁讀取)
    html_path = os.path.join(script_dir, "tw_latest.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    # 3. 自動掃描並生成「歷史目錄網頁 (history_list.html)」
    history_files = os.listdir(history_dir)
    html_files = sorted([f for f in history_files if f.endswith('.html')], reverse=True)
    
    history_links = ""
    for file in html_files:
        display_name = file.replace(".html", "")
        icon = "🇺🇸" if "US" in display_name else "🇹🇼"
        
        history_links += f'''
        <div class="history-item">
            <div class="title">{icon} {display_name}</div>
            <div class="actions">
                <a href="history/{file}" target="_blank" class="btn view-btn">👁️ 觀看報表</a>
                <a href="history/{file.replace('.html', '.xlsx')}" class="btn dl-btn">💾 下載 Excel</a>
            </div>
        </div>
        '''

    history_list_html = f"""
    <!DOCTYPE html><html lang="zh-TW"><head><meta charset="UTF-8">
    <style>
        body {{ background-color: #131722; color: #d1d4dc; font-family: sans-serif; padding: 30px; }}
        h2 {{ color: #ffffff; border-left: 4px solid #2962ff; padding-left: 10px; margin-bottom: 30px; }}
        .history-item {{ display: flex; justify-content: space-between; align-items: center; background: #1e222d; margin-bottom: 15px; padding: 15px 20px; border-radius: 8px; border: 1px solid #2a2e39; }}
        .history-item:hover {{ background: #2a2e39; }}
        .title {{ font-size: 16px; font-weight: bold; }}
        .btn {{ padding: 8px 15px; border-radius: 4px; text-decoration: none; font-size: 14px; font-weight: bold; transition: 0.2s; }}
        .view-btn {{ background: #2962ff; color: white; margin-right: 10px; }}
        .view-btn:hover {{ background: #1e4bd8; }}
        .dl-btn {{ background: #089981; color: white; }}
        .dl-btn:hover {{ background: #067a67; }}
    </style></head><body>
        <h2>📂 雲端歷史報表庫</h2>
        {history_links}
    </body></html>
    """
    with open(os.path.join(script_dir, "history_list.html"), "w", encoding="utf-8") as f:
        f.write(history_list_html)

    print("✅ 台股資料與歷史目錄更新完成！")
