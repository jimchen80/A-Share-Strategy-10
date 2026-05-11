import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os, random

def bot_v10_yahoo_edition():
    output_file = "index.xlsx"
    bj_time = (datetime.utcnow() + timedelta(hours=8))
    
    # --- 1. 构建物理拦截代码池 ---
    # 由于雅虎不支持全市场扫描，我们要精准打击（例如沪深300或活跃个股）
    # 这里需要你在 D 盘或本地准备一份代码列表，或者直接抓取一个高频池
    tickers = ["600519.SS", "000001.SZ", "300750.SZ", "601318.SS"] # 需扩展至全量或核心池

    try:
        # --- 2. 深度抓取：不仅要实时，还要 5 日历史用于计算量比 ---
        print("启动雅虎海外中继链路...")
        # 抓取最近 7 天数据，确保能算出 5 日均量
        data = yf.download(tickers, period="7d", interval="1d", group_by='ticker', threads=True)
        
        results = []
        for ticker in tickers:
            df_t = data[ticker].dropna()
            if len(df_t) < 2: continue
            
            # --- A. 基础因子提取 ---
            latest = df_t.iloc[-1]
            prev = df_t.iloc[-2]
            
            price = latest['Close']
            zf = ((price - prev['Close']) / prev['Close']) * 100
            volume = latest['Volume']
            amount = price * volume
            
            # --- B. 10.0 矩阵核心因子推算 ---
            # 量比 (lb)：今日成交量 / 过去 5 日均量
            avg_vol_5d = df_t['Volume'].iloc[-6:-1].mean()
            lb = volume / avg_vol_5d if avg_vol_5d > 0 else 1.0
            
            # 换手率 (hs)：由于雅虎不给股本，这里需要预设或通过估算市值反推
            # 假设一个平均值用于演示，实战需配合股本数据
            hs = (volume / 100000000) * 100 # 示意逻辑
            
            # --- C. 物理空间拦截模块 ---
            # 1.5% <= zf <= 4.8% & 1.5亿 <= amount <= 8.0亿
            if (zf >= 1.5 and zf <= 4.8) and (amount >= 150_000_000 and amount <= 800_000_000):
                
                # --- D. 筹码博弈模块 (Ratio) ---
                ratio = amount / (zf + 0.0001)
                
                # --- E. 综合评分矩阵 (Score) ---
                # Score = 50 + (lb * 15) + (hs * 5)
                score = 50 + (lb * 15) + (hs * 5)
                
                # 黄金堆积补偿 (+25)
                if 1.2 <= lb <= 2.8 and 3.0 <= hs <= 7.5:
                    score += 25
                # 高度控盘补偿 (+15)
                if ratio < 65_000_000:
                    score += 15
                
                results.append({
                    "代码": ticker,
                    "Signal": "🚀潜伏种子" if score > 105 else "🔥异动拦截" if score > 85 else "🧊观察",
                    "Score": score,
                    "Price": round(price, 2),
                    "zf": round(zf, 2),
                    "Ratio": round(ratio, 0),
                    "Buy_Anchor": round(price * 0.995, 2),
                    "UPDATE_TIME": bj_time.strftime('%Y-%m-%d %H:%M:%S')
                })

        # --- 3. 结果输出与物理指纹 ---
        if results:
            final_df = pd.DataFrame(results).sort_values(by="Score", ascending=False)
            final_df.to_excel(output_file, index=False)
        else:
            pd.DataFrame({"STATUS": ["全市场逻辑未闭环"], "TIME": [bj_time]}).to_excel(output_file)

    except Exception as e:
        pd.DataFrame({"FATAL": [str(e)]}).to_excel(output_file)

if __name__ == "__main__":
    bot_v10_yahoo_edition()
