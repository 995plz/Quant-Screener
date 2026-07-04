import sys
import os

try:
    print("正在檢查環境並載入套件...")
    from tradingview_screener import Query
    import pandas as pd
    import datetime

    print("連線至 TradingView 抓取美股成交值前 200 名資料...")

    columns = [
        'name',                      
        'close',                     
        'change',                    
        'Perf.W',                    
        'volume',                    
        'Value.Traded',              
        'relative_volume_10d_calc',  
        'ADR',                       
        'market_cap_basic',          
        'sector'                     
    ]

    query = (Query()
        .set_markets('america')
        .select(*columns)
        .order_by('Value.Traded', ascending=False)
        .limit(200)
    )

    df = query.get_scanner_data()[1]

    # 將 ADR 的絕對金額換算成百分比
    df['ADR'] = (df['ADR'] / df['close']) * 100

    # 欄位重新命名
    df = df.rename(columns={
        'name': 'Symbol',
        'close': 'Price',
        'change': 'Chg %',
        'Perf.W': 'Perf % 1W',
        'volume': 'Vol',
        'Value.Traded': 'Price x vol',
        'relative_volume_10d_calc': 'Rel vol',
        'ADR': 'ADR %',
        'market_cap_basic': 'Mkt cap',
        'sector': 'Sector'
    })

    if 'ticker' in df.columns:
        df = df.drop(columns=['ticker'])

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
        <title>US Top 200 Screener</title>
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
            /* 讓美股的 Sector (最後一欄) 也保持靠左對齊 */
            th:nth-child(1), th:nth-child(2), th:last-child,
            td:nth-child(1), td:nth-child(2), td:last-child {{ text-align: left; }}
            td {{ padding: 10px; border-bottom: 1px solid #2a2e39; text-align: right; }}
            tr:hover {{ background-color: #2a2e39; }}
            @media print {{
                body {{ background-color: #131722; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
                @page {{ size: A4 landscape; margin: 10mm; }}
            }}
        </style>
    </head>
    <body>
        <div class="header-title">美股成交值 Top 200 篩選報告 ({date_display})</div>
        {main_html_df.to_html(escape=False)}

        <div class="section-divider"></div>

        <div class="sub-title">🔥 一周表現最強 Top 20 (按成交值排序)</div>
        {top20_html_df.to_html(escape=False)}
    </body>
    </html>
    """

    # ---------------------------------------------------------
    # --- 存檔作業 (雲端版) ---
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 建立 history 資料夾來存放歷史 Excel
    history_dir = os.path.join(script_dir, "history")
    os.makedirs(history_dir, exist_ok=True) 

    # 1. 儲存 Excel 歷史紀錄 (檔名帶有日期時間)
    excel_path = os.path.join(history_dir, f"{time_str}_US_Top200.xlsx")
    with pd.ExcelWriter(excel_path) as writer:
        df.to_excel(writer, sheet_name='Top 200 成交值')
        top20_perf_df.to_excel(writer, sheet_name='強勢 Top 20')
    
    # 2. 儲存最新 HTML (檔名固定，讓 index.html 永遠讀取這份)
    html_path = os.path.join(script_dir, "us_latest.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print("✅ 美股資料更新完成！")

except Exception as e:
    print(f"\n❌ 程式執行失敗，詳細錯誤訊息如下：\n{e}")
