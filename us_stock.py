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
    
    # 🔥【關鍵】：TradingView API 預設的 index 就是帶有交易所前綴的完整代碼 (如 NASDAQ:NVDA, NYSE:TSM)
    # 我們在重設排名(1~200)之前，先把這個最精準的代碼備份到 ticker 欄位中
    df['ticker'] = df.index.values

    df['ADR'] = (df['ADR'] / df['close']) * 100
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
        
        # 🔥 把 Symbol 轉換成超連結，並套用我們設計的藍色樣式
        if 'ticker' in out_df.columns:
            out_df['Symbol'] = out_df.apply(
                lambda row: f'<a href="https://www.tradingview.com/chart/?symbol={row["ticker"]}" target="_blank" class="symbol-link">{row["Symbol"]}</a>', axis=1
            )
            # 網頁版不需要顯示 ticker 原始欄位，刪除保持乾淨
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
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <title>US Top 200 Screener</title>
        <style>
            body {{ background-color: #131722; color: #d1d4dc; font-family: -apple-system, sans-serif; padding: 30px; margin: 0; }}
            .header-title {{ color: #ffffff; margin-bottom: 20px; font-size: 24px; font-weight: bold; border-left: 4px solid #2962ff; padding-left: 10px; }}
            .sub-title {{ color: #ffffff; margin-bottom: 20px; font-size: 20px; font-weight: bold; border-left: 4px solid #f23645; padding-left: 10px; }}
            .section-divider {{ margin: 50px 0; border-top: 2px dashed
