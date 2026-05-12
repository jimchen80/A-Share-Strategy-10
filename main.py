import pandas as pd
import requests
from datetime import datetime, timedelta
import os, random

def fetch_all_market_data():
    """
    深入思考：利用腾讯金融网关，实现全市场 5000 只股票一次性穿透抓取
    这是避开 GitHub 海外 IP 封锁最稳定、最全量的通道
    """
    # 沪深全量 A 股请求地址
    urls = [
        "http://81.push2.eastmoney.com/api/qt/clist/get?pn=1&pz=5000&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:1,m:1+t:3&fields=f12,f14,f2,f3,f6,f22,f21,f20"
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "http://quote.eastmoney.com/"
    }

    try:
        resp = requests.get(urls[0], headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()['data']['diff']
            df = pd.DataFrame(data)
            # 字段映射：f12:代码, f14:名称, f2:现价, f3:涨幅, f6:额, f22:量比, f21:换手, f20:市值
            df.columns = ['price', 'amount', 'code', 'name', 'mkt_cap', 'hs', 'lb', 'zf']
            return df
    except:
        return None

def bot_v10_real_strategy():
    output_file = "index.xlsx"
    bj_now = (datetime.utcnow() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')

    # 1. 抓取全市场 (5000+) 数据
    df = fetch_all_market_data()
    
    if df is None or df.empty:
        pd.DataFrame({"STATUS": ["全网链路物理熔断"], "TIME": [bj_now]}).to_excel(output_file)
        return

    # 2. 物理清洗：将所有字段转换为数值，确保 10.0 矩阵计算不报错
    for col in ['price', 'zf', 'amount', 'lb', 'hs', 'mkt_cap']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # 3. 【首席策略 10.0】硬核筛选矩阵 - 真正有意义的拦截
    # 因子 A: 市值拦截 (50亿-200亿)
    df['mkt_cap_calc'] = df['mkt_cap'] / 1e8
    
    # 因子 B: 物理空间 (1.5% <= 涨幅 <= 4.8%)
    # 因子 C: 动能拦截 (1.5亿 <= 成交额 <= 8.0亿)
    # 因子 D: 活跃拦截 (换手率 >= 5% & 量比 > 1.0)
    strategy_mask = (df['zf'] >= 1.5) & (df['zf'] <= 4.8) & \
                    (df['amount'] >= 150000000) & (df['amount'] <= 800000000) & \
                    (df['mkt_cap_calc'] >= 50) & (df['mkt_cap_calc'] <= 200) & \
                    (df['hs'] >= 5.0) & (df['lb'] > 1.0)
    
    res = df[strategy_mask].copy()

    # 4. 深度博弈算法：计算 Score 和 Ratio
    if not res.empty:
        # 能效比 Ratio: 每一份涨幅消耗的资金，越低越好（说明主力控盘高）
        res['Ratio'] = res['amount'] / (res['zf'] + 0.0001)
        
        # 基础分：Score = 50 + (量比 * 15) + (换手 * 5)
        res['Score'] = 50 + (res['lb'] * 15) + (res['hs'] * 5)
        
        # 补偿矩阵
        # 黄金堆积 (+25): 量比 1.2-2.8 且 换手 3.0-7.5%
        res.loc[(res['lb'] >= 1.2) & (res['lb'] <= 2.8) & (res['hs'] >= 3.0) & (res['hs'] <= 7.5), 'Score'] += 25
        # 高度控盘 (+15): Ratio < 6500万
        res.loc[res['Ratio'] < 65000000, 'Score'] += 15

        res['Signal'] = res['Score'].apply(lambda x: "🚀潜伏种子" if x > 105 else "🔥异动拦截")
        res['UPDATE_TIME'] = bj_now
        
        # 只输出真正有博弈价值的内容
        final = res[res['Score'] >= 85].sort_values(by='Score', ascending=False)
        
        if final.empty:
            pd.DataFrame({"STATUS": ["全市场逻辑未闭环(无信号)"], "TIME": [bj_now]}).to_excel(output_file)
        else:
            final.to_excel(output_file, index=False)
    else:
        # 如果 10.0 矩阵没有票，说明当前市场环境极差或没有符合博弈逻辑的个股
        pd.DataFrame({"STATUS": ["矩阵拦截过严(5000只扫描完毕)"], "TIME": [bj_now]}).to_excel(output_file)

if __name__ == "__main__":
    bot_v10_real_strategy()
