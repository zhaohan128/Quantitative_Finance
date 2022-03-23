# -*- coding: utf-8 -*-
#通达信HSL-换手线.
#换手率线(HSL)将每天的换手率数值连成一条曲线就形成了换手率线。换手率线的取值范围是0～100。换手率大，表示股票成交活跃;换手率小，表示成交冷清。
#相关资料：https://quant.gtja.com/data/dict/technicalanalysis#hsl-%E6%8D%A2%E6%89%8B%E7%BA%BF
#https://www.zcaijing.com/cjlzb/7396.html
#本文件：主要对DBQRV进行回测，需要数据包含换手率['turnover']
#测试时间：20220321
"""
指标公式：
1.换手率线=100×成交量(手)/(流通股本(股)/100)
2.MAHSL= HSL的M日简单移动平均

用法注释：
1.换手线是根据换手率绘制的曲线，使对于成交量的研判
2.不受股本变动的影响，更增加了成交量具有可比性。
"""

#加载库
import numpy as np
import pandas as pd
import datetime

from bokeh.plotting import figure, show, output_notebook
from bokeh.layouts import column, row, gridplot, layout
from bokeh.models import Span

#计算HSL和MAHSL 的值
def calc_HSL(mkt_data, M=5):
    """
    计算HSL和MAHSL 的值
    1.换手率线=100×成交量(手)/(流通股本(股)/100)
    2.MAHSL= HSL的M日简单移动平均

    :param mkt_data DataFrame 个股历史行情数据，日维度，需要包含成交量['volume']
    :param M int MAHSL参数M

    :return mkt_data DataFrame 新增2列，HSL和MAHSL 的值
    """

    mkt_data['HSL'] = 100 * mkt_data['turnover']
    mkt_data['MAHSL'] = mkt_data['HSL'].rolling(M).mean()

    return mkt_data

#可视化
def visualize_performance(mkt_data):
    """
    可视化;

    :param mkt_data DataFrame 股票历史行情数据，日维度，需要包含日期['date']、收盘价['close']

    :return plot html 可交互式图
    """
    mkt_data['trade_datetime'] = mkt_data['date'].apply(lambda x: datetime.datetime.strptime(str(x), '%Y-%m-%d'))
    dt = mkt_data['trade_datetime']

    f1 = figure(height=300, width=700,
                sizing_mode='stretch_width',
                title='Target Trend',
                x_axis_type='datetime',
                x_axis_label="trade_datetime", y_axis_label="close")

    indi = figure(height=200, sizing_mode='stretch_width',
                  title='Factor',
                  x_axis_type='datetime',
                  x_range=f1.x_range
                  )

    # 绘制行情
    close = mkt_data['close']
    f1.line(dt, close / close.tolist()[0], line_width=1)

    # 绘制指标
    indi.line(dt, mkt_data['HSL'], line_width=1, color='green')
    indi.line(dt, mkt_data['MAHSL'], line_width=1, color='yellow')

    # p = column(f1,f2,f3,f4)
    p = gridplot([[f1],
                  [indi]
                  ])
    show(p)

#运行部分
data = pd.read_csv('data/000001.csv')
data = calc_HSL(data)
visualize_performance(data)

