import pandas as pd
import numpy as np
import akshare as ak
import efinance as ef
from datetime import datetime, timedelta
import os, random

def fetch_data_logic_audit():
    """三级审计：确保全时态数据可用"""
    try:
        df = ak.stock_zh_a_spot_em()
        if df is not None and df['成交额'].sum() > 0:
            return df, "REALTIME"
    except: pass
    try:
        df = ef.stock.get_realtime_quotes()
        return df, "MIRROR_SETTLE"
    except:
        return None, None

def bot_v10_final():
    output_file = "index.xlsx"
    bj_now = (datetime.utcnow() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')

    df_raw, source_type = fetch_data_logic_audit()
    if df_raw is None or df_raw.empty: return

    # 字段映射与清洗
    df = df_raw.copy()
    mapping = {'代码':'code','股票代码':'code','名称':'name','最新价':'price','涨跌幅':'zf','成交额':'amount','量比':'lb','换手率':'hs','总市值':'mkt_cap'}
    df = df.rename(columns=mapping)
    for c in ['zf', 'amount', 'lb', 'hs', 'price', 'mkt_cap']:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

    # --- 首席策略 10.0 矩阵逻辑植入 ---
    df['mkt_cap_calc'] = df['mkt_cap'] / 1e8 if df['mkt_cap'].max() > 10000 else df['mkt_cap']
    
    # 策略拦截：1.5<=zf<=4.8, 1.5亿<=amount<=8亿, 市值50-200亿, 换手5-10%, 量比>1
    mask = (df['zf'] >= 1.5) & (df['zf'] <= 4.8) & \
           (df['amount'] >= 150_000_000) & (df['amount'] <= 800_000_000) & \
           (df['mkt_cap_calc'] >= 50) & (df['mkt_cap_calc'] <= 200) & \
           (df['hs'] >= 5.0) & (df['hs'] <= 10.0) & \
           (df['lb'] > 1.0)
    
    res = df[mask].copy()

    if not res.empty:
        res['Ratio'] = res['amount'] / (res['zf'] + 0.0001)
        res['Score'] = 50 + (res['lb'] * 15) + (res['hs'] * 5)
        # 补偿矩阵：黄金堆积+25, 高度控盘+15
        res.loc[(res['lb']>=1.2)&(res['lb']<=2.8)&(res['hs']>=3.0)&(res['hs']<=7.5), 'Score'] += 25
        res.loc[res['Ratio'] < 65000000, 'Score'] += 15
        
        res['Signal'] = res['Score'].apply(lambda x: "🚀潜伏种子" if x > 105 else "🔥异动拦截" if x > 85 else "🧊观察")
        res['UPDATE_TIME'] = bj_now
        res['SOURCE'] = source_type
        res.sort_values(by='Score', ascending=False).to_excel(output_file, index=False)
    else:
        # 兜底：若无信号则显示全市场涨幅前20
        df.sort_values(by='zf', ascending=False).head(20).to_excel(output_file, index=False)

if __name__ == "__main__":
    bot_v10_final()
