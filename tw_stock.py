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
except Exception as e:
    print(f"❌ 程式執行失敗，詳細錯誤訊息如下：\n{e}")
