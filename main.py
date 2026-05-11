import pandas as pd
import numpy as np
import akshare as ak
import efinance as ef
from datetime import datetime, timedelta
import os, random, time

def fetch_valid_data_engine():
    """
    三级数据审计引擎：确保在休盘、午休、开盘均能拦截有效数据
    """
    # 尝试优先级 1：东财实时流 (覆盖盘中及午间定格)
    try:
        df = ak.stock_zh_a_spot_em()
        if df is not None and df['成交额'].sum() > 0:
            return df, "REALTIME_ACTIVE"
    except: pass

    # 尝试优先级 2：腾讯/新浪备份源 (应对东财接口临时维护或封锁)
    try:
        df = ef.stock.get_realtime_quotes()
        if df is not None and df['成交额'].sum() > 0:
            return df, "BACKUP_ACTIVE"
    except: pass

    # 尝试优先级 3：历史镜像回溯 (应对隔夜、周末、早盘空窗期)
    try:
        # efinance 在休盘期会自动返回最近一个交易日的最终结算快照
        df = ef.stock.get_realtime_quotes()
        if df is not None:
            return df, "HISTORY_MIRROR"
    except:
        return None, None

def bot_v10_integrated_engine():
    output_file = "index.xlsx"
    if os.path.exists(output_file): os.remove(output_file)
    
    bj_now = (datetime.utcnow() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')

    # 1. 启动三级审计引擎
    df_raw, source_type = fetch_valid_data_engine()
    
    if df_raw is None or df_raw.empty:
        pd.DataFrame({"FATAL_ERROR": ["物理源封锁或数据断流"], "TIME": [bj_now]}).to_excel(output_file)
        return

    # 2. 字段强制映射 (确保不同源下的策略一致性)
    df = df_raw.copy()
    mapping = {
        '代码':'code', '股票代码':'code', '名称':'name', '股票名称':'name',
        '最新价':'price', '涨跌幅':'zf', '成交额':'amount', '量比':'lb', 
        '换手率':'hs', '总市值':'mkt_cap'
    }
    df = df.rename(columns=mapping)

    # 3. 物理清洗：将所有策略字段数值化
    for col in ['zf', 'amount', 'lb', 'hs', 'price', 'mkt_cap']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # 4. 【首席策略 10.0】筛选策略硬核植入
    # 因子 A：市值拦截 (50亿 <= 市值 <= 200亿)
    df['mkt_cap_calc'] = df['mkt_cap'] / 1e8 if df['mkt_cap'].max() > 10000 else df['mkt_cap']
    
    # 因子 B：物理空间拦截 (1.5% <= 涨幅 <= 4.8% & 1.5亿 <= 成交额 <= 8.0亿)
    # 因子 C：超短动能拦截 (换手 5%-10% & 量比 > 1.0)
    strategy_mask = (df['zf'] >= 1.5) & (df['zf'] <= 4.8) & \
                    (df['amount'] >= 150_000_000) & (df['amount'] <= 800_000_000) & \
                    (df['mkt_cap_calc'] >= 50) & (df['mkt_cap_calc'] <= 200) & \
                    (df['hs'] >= 5.0) & (df['hs'] <= 10.0) & \
                    (df['lb'] > 1.0)
    
    res = df[strategy_mask].copy()

    # 5. 【首席策略 10.0】综合评分矩阵计算
    if not res.empty:
        # 能效比计算 (Ratio)
        res['Ratio'] = res['amount'] / (res['zf'] + 0.00001)
        
        # 基础分计算：Score = 50 + (lb * 15) + (hs * 5)
        res['Score'] = 50 + (res['lb'] * 15) + (res['hs'] * 5)
        
        # 补偿项 1：黄金堆积 (+25分) -> D0转D1核心判定
        # 条件：量比 1.2-2.8 且 换手 3.0%-7.5%
        res.loc[(res['lb'] >= 1.2) & (res['lb'] <= 2.8) & (res['hs'] >= 3.0) & (res['hs'] <= 7.5), 'Score'] += 25
        
        # 补偿项 2：高度控盘 (+15分) -> 箭在弦上判定
        # 条件：Ratio < 65,000,000
        res.loc[res['Ratio'] < 65_000_000, 'Score'] += 15

        # 结果分级与决策定义
        res['Signal_Level'] = res['Score'].apply(lambda x: "🚀 潜伏种子 (D0级)" if x > 105 else "🔥 异动拦截" if x > 85 else "🧊 观察")
        res['Buy_Anchor'] = res['price'] * 0.995 # 回踩因子
        res['Risk_Line'] = res['price'] * 0.98   # D3逃生因子
        res['SOURCE'] = source_type
        res['UPDATE_TIME'] = bj_now
        
        # 强制 Random_Hash 触发 Git 更新
        res['Fingerprint'] = [random.random() for _ in range(len(res))]

        # 最终价值筛选：只输出 Score > 85 的高能标的
        final_report = res[res['Score'] >= 85].sort_values(by='Score', ascending=False)
        
        if final_report.empty:
            # 如果矩阵无标的，生成当前涨幅前20作为背景参考，确保 Excel 有内容
            df.sort_values(by='zf', ascending=False).head(20).to_excel(output_file, index=False)
        else:
            final_report.to_excel(output_file, index=False)
    else:
        # 如果策略池为空，输出全市场活跃度前20，防止由于拦截过严导致 Excel 报错
        df.sort_values(by='zf', ascending=False).head(20).to_excel(output_file, index=False)

if __name__ == "__main__":
    bot_v10_integrated_engine()
