from email.mime.text import MIMEText
import smtplib
import time
from apscheduler.schedulers.blocking import BlockingScheduler
import sendemail
import requests
import pandas as pd
from apscheduler.schedulers.blocking import BlockingScheduler
import numpy as np
pd.set_option('display.max_columns', None)

def timestamp_to_fomat(timestamp=None, format='%Y-%m-%d %H:%M:%S'):
    # 默认返回当前格式化好的时间
    # 传入时间戳的话，把时间戳转换成格式化好的时间，返回
    if timestamp:
        time_tuple = time.localtime(timestamp)
        res = time.strftime(format, time_tuple)
    else:
        res = time.strftime(format)  # 默认读取当前时间
    return res

#adquete data
BASE_URL = "https://api.binance.com"
# url = BASE_URL + "/api/v1/klines?symbol=BTCUSDT&interval=1m&limit=1000" # 会不一样
url = BASE_URL + "/api/v1/klines?symbol=ETHUSDT&interval=15m&limit=1000"
resp = requests.get(url)
resp = resp.json()
df = pd.DataFrame(resp)
df = df[:-1]
df = df.drop(columns=[6, 7, 8, 9, 10, 11])
df.columns=["opentime", "Open", "High", "Low", "Close", "Volume"]
df["Date"] = (df["opentime"]//1000).map(timestamp_to_fomat)
df = df.set_index(df["Date"])
df = df.drop(["opentime"],axis=1)
df['Open'] = pd.to_numeric(df['Open'])
df['High'] = pd.to_numeric(df['High'])
df['Low'] = pd.to_numeric(df['Low'])
df['Close'] = pd.to_numeric(df['Close'])
df['Volume'] = pd.to_numeric(df['Volume'])
df['ema12'] = None
df['ema26'] = None
df['diff'] = None
df['ema12'][0] = 2541.35
df['ema26'][0] = 2531.62
df['dea'] = None
df['dea'][0] = 6.35
df['macd'] = None
for i in range(1,len(df)):
    df['ema12'].iloc[i] = df['ema12'].iloc[i-1]*11/13 + df['Close'].iloc[i]*2/13
    df['ema26'].iloc[i] = df['ema26'].iloc[i-1]*25/27 + df['Close'].iloc[i]*2/27
    df['diff'].iloc[i] = df['ema12'].iloc[i] - df['ema26'].iloc[i]
    df['dea'].iloc[i] = df['dea'].iloc[i-1]*8/10 + df['diff'].iloc[i]*2/10
    df['macd'][i] = df['diff'][i] - df['dea'][i]

def find_local_tp(macd):
    if (macd[-2] > macd[-1]) and (macd[-3] < macd[-2]):
        return 'maxima'
    elif (macd[-2] < macd[-1]) and (macd[-2] < macd[-3]):
        return 'minima'
    elif np.abs((macd[-1] - macd[-2])/macd[-2]) > 4:
        print(np.abs((macd[-1] - macd[-2])/macd[-2]))
        return 'change too much'
    else:
        return 'not a signal'


# adquaire new data + new macd
def job():
    global df
    print('Start obtaining new data.')
    print(df)
    BASE_URL = "https://api.binance.com"
    # url = BASE_URL + "/api/v1/klines?symbol=BTCUSDT&interval=1m&limit=1000" # 会不一样
    url = BASE_URL + "/api/v1/klines?symbol=ETHUSDT&interval=15m&limit=1"
    resp = requests.get(url)
    resp = resp.json()
    new = pd.DataFrame(resp)
    new = new.drop(columns=[6, 7, 8, 9, 10, 11])
    new.columns = ["opentime", "Open", "High", "Low", "Close", "Volume"]
    new["Date"] = (new["opentime"] // 1000).map(timestamp_to_fomat)
    new = new.set_index(new["Date"])
    new = new.drop(["opentime"], axis=1)
    new['Open'] = pd.to_numeric(new['Open'])
    new['High'] = pd.to_numeric(new['High'])
    new['Low'] = pd.to_numeric(new['Low'])
    new['Close'] = pd.to_numeric(new['Close'])
    new['Volume'] = pd.to_numeric(new['Volume'])
    if new.index[-1] not in df.index:
        print('NEW data received, attaching to the new dataframe')
        new['ema12'] = df['ema12'][-1]*11/13 + new['Close']*2/13
        new['ema26'] = df['ema26'][-1]*25/27 + new['Close']*2/27
        new['diff'] = new['ema12'] - new['ema26']
        new['dea'] = df['dea'][-1]*8/10 + new['diff']*2/10
        new['macd'] = new['diff'] - new['dea']
        print(new)
        df = df.append(new)
        # print('new df',df)
        # 计算买卖点,signal: maxima, minima, change too much, not signal
        macd = df['macd'].iloc[-3:]
        signal = find_local_tp(macd)
        print('signal',signal)
        if signal == 'maxima':
            content = 'A local maxima detected. Consider selling at this point.'
            title = 'a local MAXIMA detected.'
            sendemail.send_email(content, title)
        elif signal == 'minima':
            content = 'A local minima detected. Consider buying at this point.'
            title = 'a local MINIMA detected.'
            sendemail.send_email(content,title)
        # elif signal == 'change too much':
        #     content = 'change too much'
        #     title = 'change too much'
        #     sendemail.send_email(content,title)





if __name__=="__main__":
    scheduler = BlockingScheduler()
    scheduler.add_job(job, 'cron', minute='14,29,44,59',second=58)
    scheduler.start()