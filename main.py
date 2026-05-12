import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os, random, time

def bot_v10_yahoo_full_strategy():
    output_file = "index.xlsx"
    # 物理删除旧文件，确保刷新
    if os.path.exists(output_file): os.remove(output_file)
    
    bj_now_obj = datetime.utcnow() + timedelta(hours=8)
    bj_now = bj_now_obj.strftime('%Y-%m-%d %H:%M:%S')

    # --- 深度思考：构建核心代码池 ---
    # 雅虎不支持全市场扫描，建议在此处填入你需要监控的 100-300 只活跃标的
    # 格式：沪市 .SS，深市 .SZ
    ticker_list = ["600519.SS", "000001.SZ", "300750.SZ", "601318.SS", "600030.SS", "000756.SZ", "600418.SS"] 

    results = []
    print(f"[{bj_now}] 启动雅虎穿透链路，执行 10.0 全因子筛选...")

    for t in ticker_list:
        try:
            # 抓取最近 10 天的数据，确保有足够的样本计算均量
            tk = yf.Ticker(t)
            hist = tk.history(period="10d")
            info = tk.info # 用于获取股本和市值
            
            if len(hist) < 6: continue
            
            # --- 1. 基础数据提取 ---
            latest = hist.iloc[-1]
            prev = hist.iloc[-2]
            
            price = latest['Close']
            zf = ((price - prev['Close']) / prev['Close']) * 100
            volume = latest['Volume']
            amount = price * volume
            
            # --- 2. 核心因子计算 (手动对齐 10.0 矩阵) ---
            # A. 总市值 (mkt_cap) - 转换为亿元
            mkt_cap = info.get('marketCap', 0) / 1e8
            
            # B. 量比 (lb) - 今日量 / 过去 5 日均量
            avg_vol_5d = hist['Volume'].iloc[-6:-1].mean()
            lb = volume / avg_vol_5d if avg_vol_5d > 0 else 1.0
            
            # C. 换手率 (hs) - 今日成交量 / 总股本 (估算)
            shares_outstanding = info.get('sharesOutstanding', 1)
            hs = (volume / shares_outstanding) * 100 if shares_outstanding > 1 else 0

            # --- 3. 【首席策略 10.0】筛选逻辑硬核植入 ---
            # 因子拦截：1.5%<=zf<=4.8% | 1.5亿<=amount<=8.0亿 | 50亿<=市值<=200亿 | 5%<=换手<=10% | 量比>1
            if (zf >= 1.5 and zf <= 4.8) and \
               (amount >= 150_000_000 and amount <= 800_000_000) and \
               (mkt_cap >= 50 and mkt_cap <= 200) and \
               (hs >= 5.0 and hs <= 10.0) and \
               (lb > 1.0):

                # --- 4. 筹码博弈运算 ---
                # 能效比 Ratio
                ratio = amount / (zf + 0.0001)
                
                # 评分矩阵 Score = 50 + (lb * 15) + (hs * 5)
                score = 50 + (lb * 15) + (hs * 5)
                
                # 补偿 1：黄金堆积 (+25) -> lb 1.2-2.8 且 hs 3.0-7.5
                if (1.2 <= lb <= 2.8) and (3.0 <= hs <= 7.5):
                    score += 25
                
                # 补偿 2：高度控盘 (+15) -> Ratio < 65,000,000
                if ratio < 65_000_000:
                    score += 15

                results.append({
                    "代码": t,
                    "Signal": "🚀潜伏种子" if score > 105 else "🔥异动拦截",
                    "Score": round(score, 2),
                    "Price": round(price, 2),
                    "zf%": round(zf, 2),
                    "Amount": round(amount / 1e8, 2), # 亿元显示
                    "lb": round(lb, 2),
                    "hs%": round(hs, 2),
                    "Ratio": round(ratio, 0),
                    "Buy_Anchor": round(price * 0.995, 2),
                    "UPDATE_TIME": bj_now
                })

        except Exception as e:
            print(f"标的 {t} 抓取异常: {e}")
            continue

    # --- 5. 结果输出 ---
    if results:
        final_df = pd.DataFrame(results).sort_values(by='Score', ascending=False)
        final_df.to_excel(output_file, index=False)
        print(f"筛选完成，拦截符合 10.0 矩阵标的：{len(results)} 只")
    else:
        # 即使为空也生成报告，带上随机哈希，强制推送
        pd.DataFrame({
            "STATUS": ["10.0矩阵拦截过严或池内暂无信号"], 
            "TIME": [bj_now],
            "HASH": [random.random()]
        }).to_excel(output_file, index=False)

if __name__ == "__main__":
    bot_v10_yahoo_full_strategy()
