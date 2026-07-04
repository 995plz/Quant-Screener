import sys
import os
import traceback

try:
    print("正在檢查環境並載入套件...")
    from tradingview_screener import Query
    import pandas as pd
    import datetime

    print("連線至 TradingView 抓取美股成交值前 200 名資料...")

    columns = [
        'name', 'close', 'change', 'Perf.W', 'volume', 
        'Value.Traded', 'relative_volume_10d_calc', 'ADR', 'market_cap_basic', 'sector'
    ]

    query = (Query().set_markets('america').select(*columns).order_by('Value.Traded', ascending=False).limit(200))
    df = query.get_scanner_data()[1]

    df['ADR'] = (df['ADR'] / df['close']) * 100
    df = df.rename(columns={
        'name': 'Symbol', 'close': 'Price', 'change': 'Chg %',
        'Perf.W': 'Perf % 1W', 'volume': 'Vol', 'Value.Traded': 'Price x vol',
        'relative_volume_10d_calc': 'Rel vol', 'ADR': 'ADR %',
        'market_cap_basic': 'Mkt cap', 'sector': 'Sector'
    })
    
    # 拔除 ticker，確保沒有超連結
    if 'ticker' in df.columns:
        df = df.drop(columns=['ticker'])

    df.index = range(1, len(df) + 1)
    df.index.name = '排名'

    # 區塊 2：當日漲幅最強 Top 20
    top20_daily_df = df.nlargest(20, 'Chg %')
    top20_daily_df = top20_daily_df.sort_values(by='Price x vol', ascending=False)
    top20_daily_df.index = range(1, 21)
    top20_daily_df.index.name = '當日強勢'

    # 區塊 3：一周表現最強 Top 20
    top20_perf_df = df.nlargest(20, 'Perf % 1W')
    top20_perf_df = top20_perf_df.sort_values(by='Price x vol', ascending=False)
    top20_perf_df.index = range(1, 21)
    top20_perf_df.index.name = '一周強勢'

    def color_pct(val):
        if pd.isna(val): return ""
        try:
            v = float(val)
            color = "#089981" if v > 0 else "#f23645" if v < 0 else "#d1d4dc"
            sign = "+" if v > 0 else ""
            return f'<span style="color: {color};">{sign}{v:.2f}%</span>'
        except: return val

    def format_large_num(val):
        if pd.isna(val): return ""
        try:
            v = float(val)
            if v >= 1e9: return f"{v/1e9:.2f}B"
            if v >= 1e6: return f"{v/1e6:.2f}M"
            return f"{v:,.0f}"
        except: return val

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
    top20_daily_html_df = format_df_for_html(top20_daily_df) 
    top20_html_df = format_df_for_html(top20_perf_df)

    time_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    date_display = datetime.datetime.now().strftime("%Y-%m-%d")
    
    html_content = f"""<!DOCTYPE html><html lang="zh-TW"><head><meta charset="UTF-8"><title>US Top 200 Screener</title><style>body {{ background-color: #131722; color: #d1d4dc; font-family: -apple-system, sans-serif; padding: 30px; margin: 0; }} .header-title {{ color: #ffffff; margin-bottom: 20px; font-size: 24px; font-weight: bold; border-left: 4px solid #2962ff; padding-left: 10px; }} .sub-title {{ color: #ffffff; margin-bottom: 20px; font-size: 20px; font-weight: bold; border-left: 4px solid #f23645; padding-left: 10px; }} .section-divider {{ margin: 50px 0; border-top: 2px dashed #2a2e39; }} table {{ width: 100%; border-collapse: collapse; font-size: 13px; }} th {{ background-color: #1e222d; color: #868993; font-weight: normal; padding: 12px 10px; text-align: right; border-bottom: 1px solid #2a2e39; border-top: 1px solid #2a2e39; white-space: nowrap; }} th:nth-child(1), th:nth-child(2), th:last-child, td:nth-child(1), td:nth-child(2), td:last-child {{ text-align: left; }} td {{ padding: 10px; border-bottom: 1px solid #2a2e39; text-align: right; }} tr:hover {{ background-color: #2a2e39; }}</style></head><body><div class="header-title">美股成交值 Top 200 篩選報告 ({date_display})</div>{main_html_df.to_html(escape=False)}<div class="section-divider"></div><div class="sub-title">🚀 當日漲幅最強 Top 20 (按成交值排序)</div>{top20_daily_html_df.to_html(escape=False)}<div class="section-divider"></div><div class="sub-title">🔥 一周表現最強 Top 20 (按成交值排序)</div>{top20_html_df.to_html(escape=False)}</body></html>"""

    script_dir = os.path.dirname(os.path.abspath(__file__))
    history_dir = os.path.join(script_dir, "history")
    os.makedirs(history_dir, exist_ok=True) 

    excel_path = os.path.join(history_dir, f"{time_str}_US_Top200.xlsx")
    with pd.ExcelWriter(excel_path) as writer:
        df.to_excel(writer, sheet_name='Top 200 成交值')
        top20_daily_df.to_excel(writer, sheet_name='當日強勢 Top 20') 
        top20_perf_df.to_excel(writer, sheet_name='一周強勢 Top 20')
        
    history_html_path = os.path.join(history_dir, f"{time_str}_US_Top200.html")
    with open(history_html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    html_path = os.path.join(script_dir, "us_latest.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    history_files = os.listdir(history_dir)
    html_files = sorted([f for f in history_files if f.endswith('.html')], reverse=True)
    history_links = ""
    for file in html_files:
        display_name = file.replace(".html", "")
        icon = "🇺🇸" if "US" in display_name else "🇹🇼"
        history_links += f'''<div class="history-item"><div class="title">{icon} {display_name}</div><div class="actions"><a href="history/{file}" target="_blank" class="btn view-btn">👁️ 觀看報表</a><a href="history/{file.replace('.html', '.xlsx')}" class="btn dl-btn">💾 下載 Excel</a></div></div>'''

    history_list_html = f"""<!DOCTYPE html><html lang="zh-TW"><head><meta charset="UTF-8"><style>body {{ background-color: #131722; color: #d1d4dc; font-family: sans-serif; padding: 30px; }} h2 {{ color: #ffffff; border-left: 4px solid #2962ff; padding-left: 10px; margin-bottom: 30px; }} .history-item {{ display: flex; justify-content: space-between; align-items: center; background: #1e222d; margin-bottom: 15px; padding: 15px 20px; border-radius: 8px; border: 1px solid #2a2e39; }} .history-item:hover {{ background: #2a2e39; }} .title {{ font-size: 16px; font-weight: bold; }} .btn {{ padding: 8px 15px; border-radius: 4px; text-decoration: none; font-size: 14px; font-weight: bold; transition: 0.2s; }} .view-btn {{ background: #2962ff; color: white; margin-right: 10px; }} .view-btn:hover {{ background: #1e4bd8; }} .dl-btn {{ background: #089981; color: white; }} .dl-btn:hover {{ background: #067a67; }}</style></head><body><h2>📂 雲端歷史報表庫</h2>{history_links}</body></html>"""
    with open(os.path.join(script_dir, "history_list.html"), "w", encoding="utf-8") as f:
        f.write(history_list_html)

    print("✅ 美股資料與歷史目錄更新完成！")
except Exception as e:
    print("❌ 程式執行失敗，詳細錯誤訊息如下：")
    traceback.print_exc()
