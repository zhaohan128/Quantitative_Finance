# -*- coding: utf-8 -*-
#佳庆指标CHAIKIN （Chaikin Oscillator），是由Marc Chaikin所发展的一种新成交量指标。
#他汲取JosephGranville和Larry Williams两位教授的理论精华，将A/D VOLUME指标加以改良，衍生出佳庆指标。
#相关资料：http://www.cftsc.com/qushizhibiao/606.html
#本文件：主要对CHO进行回测，需要数据包含收盘价['close']、开盘价['open']、最高价['high']、最低价['low']、成交量['volume']、波动率['pct_chg']
#测试时间：20220309
"""
佳庆指标用法
1.趋势类-CHO 曲线产生急促的「凸起」时，代表行情可能出现向上或向下反转；
2.股价>90 天平均线，CHO由负转正时，买进参考；
3.股价<90 天平均线，CHO由正转负时，卖出参考；
4.本指标也可设参考线，自定超买超卖的界限值；
5.本指标须配合OBOS、ENVELOPE同时使用。
"""

#加载库
import numpy as np
import pandas as pd
import datetime

from bokeh.plotting import figure, show, output_notebook
from bokeh.layouts import column, row, gridplot, layout
from bokeh.models import Span

#计算CHO指标
def calc_CHO(mkt_data, n1=10, n2=20, m1=6, m2=90):
    """
    构造CHO/MACHO指标，MID:=SUM(VOL*(2*CLOSE-HIGH-LOW)/(HIGH+LOW),0);
                    趋势类-CHO:MA(MID,N1)-MA(MID,N2);
                    MACHO:MA(趋势类-CHO,M);

    :param mkt_data DataFrame 股票历史行情数据，日维度，需要包含收盘价['close']、开盘价['open']、
                                                    最高价['high']、最低价['low']、成交量['volume']
    :param n1 int CHO参数N1
    :param n2 int CHO参数N2
    :param m1 int MACHO参数M
    :param m2 int CHO与MA均线进行比较，一般取90

    :return mkt_data DataFrame 新增3列['趋势类-CHO']['MACHO']['MA90']
    """
    #计算指标
    close = mkt_data['close']
    open = mkt_data['open']
    high = mkt_data['high']
    low = mkt_data['low']
    vol = mkt_data['volume']
    MID = vol*(2*close-high-low)/(high+low)
    CHO = close.rolling(n1, min_periods=1).mean() - close.rolling(n2, min_periods=1).mean()
    MACHO = CHO.rolling(m1, min_periods=1).mean()
    MA90 = close.rolling(m2, min_periods=1).mean()
    #指标赋值
    mkt_data['MA90'] = MA90
    mkt_data['趋势类-CHO'] = CHO
    mkt_data['MACHO'] = MACHO

    return mkt_data

#计算信号
def calc_signal(mkt_data):
    """
    比较CHO和MA均线，计算信号，1为买进，-1为卖出;

    :param mkt_data DataFrame 股票历史行情数据，日维度，需要包含收盘价['close']、趋势类-CHO、MA

    :return mkt_data DataFrame 新增1列['signal']
    """
    CHO = mkt_data['趋势类-CHO']
    MA90 = mkt_data['MA90']
    CLOSE = mkt_data['close']
    """ 计算信号 """
    signals = []
    for cho, precho, ma, close in zip(CHO, CHO.shift(1), MA90, CLOSE):
        signal = None
        if (cho > 0) & (precho < 0) & (close > ma):
            signal = 1
        elif (cho < 0) & (precho > 0) & (close < ma):
            signal = -1
        signals.append(signal)
    """ 信号赋值 """
    mkt_data['signal'] = signals
    return mkt_data

#计算持仓
def calc_position(mkt_data):
    """
    计算持仓;

    :param mkt_data DataFrame 股票历史行情数据，日维度，需要包含信号['signal']

    :return mkt_data DataFrame 新增1列['position']
    """
    mkt_data['position'] = mkt_data['signal'].fillna(method='ffill').shift(1).fillna(0)
    return mkt_data

#计算结果
def statistic_performance(mkt_data, r0=0.03, data_period=1440):
    """
    策略表现;

    :param mkt_data DataFrame 股票历史行情数据，日维度，需要包含持仓['position']、波动率['pct_chg']

    :return mkt_data DataFrame  新增序列型特征，持仓收益，持仓胜负，累计持仓收益，回撤，超额收益
    :return performance_df DataFrame  新增数值型特征，'累计收益','多仓次数', '多仓胜率', '多仓平均持有期','空仓次数', '空仓胜率',
                                    '空仓平均持有期','日胜率', '最大回撤', '年化收益/最大回撤','年化收益', '年化标准差', '年化夏普'
    """
    position = mkt_data['position']

    """      序列型特征
        hold_r :      持仓收益
        hold_win :    持仓胜负
        hold_cumu_r : 累计持仓收益
        drawdown :    回撤
        ex_hold_r :   超额收益
    """
    hold_r = mkt_data['pct_chg'] / 100 * position
    hold_win = hold_r > 0
    hold_cumu_r = (1 + hold_r).cumprod() - 1
    drawdown = (hold_cumu_r.cummax() - hold_cumu_r) / (1 + hold_cumu_r).cummax()
    ex_hold_r = hold_r - r0 / (250 * 1440 / data_period)

    mkt_data['hold_r'] = hold_r
    mkt_data['hold_win'] = hold_win
    mkt_data['hold_cumu_r'] = hold_cumu_r
    mkt_data['drawdown'] = drawdown
    mkt_data['ex_hold_r'] = ex_hold_r

    """       数值型特征
        v_hold_cumu_r：         累计持仓收益
        v_pos_hold_times：      多仓开仓次数
        v_pos_hold_win_times：  多仓开仓盈利次数
        v_pos_hold_period：     多仓持有周期数
        v_pos_hold_win_period： 多仓持有盈利周期数
        v_neg_hold_times：      空仓开仓次数
        v_neg_hold_win_times：  空仓开仓盈利次数
        v_neg_hold_period：     空仓持有盈利周期数
        v_neg_hold_win_period： 空仓开仓次数
        v_hold_period：         持仓周期数（最后一笔未平仓订单也算）
        v_hold_win_period：     持仓盈利周期数（最后一笔未平仓订单也算）
        v_max_dd：              最大回撤
        v_annual_std：          年化标准差
        v_annual_ret：          年化收益
        v_sharpe：              夏普率
    """
    v_hold_cumu_r = hold_cumu_r.tolist()[-1]

    v_pos_hold_times = 0
    v_pos_hold_win_times = 0
    v_pos_hold_period = 0
    v_pos_hold_win_period = 0
    v_neg_hold_times = 0
    v_neg_hold_win_times = 0
    v_neg_hold_period = 0
    v_neg_hold_win_period = 0
    for w, r, pre_pos, pos in zip(hold_win, hold_r, position.shift(1), position):
        # 有换仓（先结算上一次持仓，再初始化本次持仓）
        if pre_pos != pos:
            # 判断pre_pos非空：若为空则是循环的第一次，此时无需结算，直接初始化持仓即可
            if pre_pos == pre_pos:
                # 结算上一次持仓
                if pre_pos > 0:
                    v_pos_hold_times += 1
                    v_pos_hold_period += tmp_hold_period
                    v_pos_hold_win_period += tmp_hold_win_period
                    if tmp_hold_r > 0:
                        v_pos_hold_win_times += 1
                elif pre_pos < 0:
                    v_neg_hold_times += 1
                    v_neg_hold_period += tmp_hold_period
                    v_neg_hold_win_period += tmp_hold_win_period
                    if tmp_hold_r > 0:
                        v_neg_hold_win_times += 1
            # 初始化本次持仓
            tmp_hold_r = r
            tmp_hold_period = 0
            tmp_hold_win_period = 0
        else:  # 未换仓
            if abs(pos) > 0:
                tmp_hold_period += 1
                if r > 0:
                    tmp_hold_win_period += 1
                if abs(r) > 0:
                    tmp_hold_r = (1 + tmp_hold_r) * (1 + r) - 1

    v_hold_period = (abs(position) > 0).sum()
    v_hold_win_period = (hold_r > 0).sum()
    v_max_dd = drawdown.max()
    v_annual_ret = pow(1 + v_hold_cumu_r,
                       1 / (data_period / 1440 * len(mkt_data) / 250)) - 1
    v_annual_std = ex_hold_r.std() * np.sqrt(250 * 1440 / data_period)
    v_sharpe = v_annual_ret / v_annual_std

    """ 生成Performance DataFrame """
    performance_cols = ['累计收益',
                        '多仓次数', '多仓胜率', '多仓平均持有期',
                        '空仓次数', '空仓胜率', '空仓平均持有期',
                        '日胜率', '最大回撤', '年化收益/最大回撤',
                        '年化收益', '年化标准差', '年化夏普'
                        ]
    performance_values = ['{:.2%}'.format(v_hold_cumu_r),
                          v_pos_hold_times, '{:.2%}'.format(v_pos_hold_win_times / v_pos_hold_times),
                          '{:.2f}'.format(v_pos_hold_period / v_pos_hold_times),
                          v_neg_hold_times, '{:.2%}'.format(v_neg_hold_win_times / v_neg_hold_times),
                          '{:.2f}'.format(v_neg_hold_period / v_neg_hold_times),
                          '{:.2%}'.format(v_hold_win_period / v_hold_period),
                          '{:.2%}'.format(v_max_dd),
                          '{:.2f}'.format(v_annual_ret / v_max_dd),
                          '{:.2%}'.format(v_annual_ret),
                          '{:.2%}'.format(v_annual_std),
                          '{:.2f}'.format(v_sharpe)
                          ]
    performance_df = pd.DataFrame(performance_values, index=performance_cols)
    return mkt_data, performance_df

#可视化
def visualize_performance(mkt_data):
    """
    可视化;

    :param mkt_data DataFrame 股票历史行情数据，日维度，需要包含日期['date']、收盘价['close']、持仓['position']、
                                           持仓收益['hold_r']、累计持仓收益['hold_cumu_r']、回撤['drawdown']

    :return
    """
    mkt_data['trade_datetime'] = mkt_data['date'].apply(lambda x: datetime.datetime.strptime(str(x), '%Y-%m-%d'))
    dt = mkt_data['trade_datetime']

    f1 = figure(height=300, width=700,
                sizing_mode='stretch_width',
                title='Target Trend',
                x_axis_type='datetime',
                x_axis_label="trade_datetime", y_axis_label="close")
    f2 = figure(height=200, sizing_mode='stretch_width',
                title='Position',
                x_axis_label="trade_datetime", y_axis_label="position",
                x_axis_type='datetime',
                x_range=f1.x_range)
    f3 = figure(height=200, sizing_mode='stretch_width',
                title='Return',
                x_axis_type='datetime',
                x_range=f1.x_range)
    f4 = figure(height=200, sizing_mode='stretch_width',
                title='Drawdown',
                x_axis_type='datetime',
                x_range=f1.x_range)

    indi = figure(height=200, sizing_mode='stretch_width',
                  title='趋势类-CHO',
                  x_axis_type='datetime',
                  x_range=f1.x_range
                  )

    # 绘制行情
    close = mkt_data['close']
    cumu_hold_close = (mkt_data['hold_cumu_r'] + 1)
    f1.line(dt, close / close.tolist()[0], line_width=1)
    f1.line(dt, cumu_hold_close, line_width=1, color='red')

    # 绘制指标
    indi = figure(height=200, sizing_mode='stretch_width',
                  title='趋势类-CHO',
                  x_axis_type='datetime',
                  x_range=f1.x_range
                  )
    CHO = mkt_data['趋势类-CHO']
    MACHO = mkt_data['MACHO']
    indi.line(dt, CHO, line_width=1, color='red')
    indi.line(dt, MACHO, line_width=1, color='blue')

    # 绘制仓位
    position = mkt_data['position']
    f2.step(dt, position)

    # 绘制收益
    hold_r = mkt_data['hold_r']
    f3.vbar(x=dt, top=hold_r)

    # 绘制回撤
    drawdown = mkt_data['drawdown']
    f4.line(dt, -drawdown, line_width=1)

    # p = column(f1,f2,f3,f4)
    p = gridplot([[f1],
                  [indi],
                  [f2],
                  [f3],
                  [f4]
                  ])
    show(p)

#运行部分
data = pd.read_csv('data/000300.csv')
data = calc_CHO(data, n1=10, n2=20, m1=6, m2=90)
data = calc_signal(data)
data = calc_position(data)
result_daily, performance_df = statistic_performance(data)#
visualize_performance(result_daily)
print(performance_df)
