import schedule
import pandas as pd
import pyupbit
pd.set_option('display.max_rows', None)

import warnings
warnings.filterwarnings('ignore')

from datetime import datetime
import time

access_key = "a"
secret_key = "a"

upbit = pyupbit.Upbit(access_key, secret_key)
krw = upbit.get_balance("KRW")
print(krw)

def get_ma120(ticker):
    df = pyupbit.get_ohlcv(ticker, interval="minutes240")
    ma120 = df['close'].rolling(120).mean().iloc[-1]
    return ma120

def tr(data):
    data['previous_close'] = data['close'].shift(1)
    data['high-low'] = abs(data['high'] - data['low'])
    data['high-pc'] = abs(data['high'] - data['previous_close'])
    data['low-pc'] = abs(data['low'] - data['previous_close'])

    tr = data[['high-low', 'high-pc', 'low-pc']].max(axis=1)

    return tr

def atr(data, period):
    data['tr'] = tr(data)
    atr = data['tr'].rolling(period).mean()

    return atr

def supertrend(df, period=7, atr_multiplier=2):
    hl2 = (df['high'] + df['low']) / 2
    df['atr'] = atr(df, period)
    df['upperband'] = hl2 + (atr_multiplier * df['atr'])
    df['lowerband'] = hl2 - (atr_multiplier * df['atr'])
    df['in_uptrend'] = True

    for current in range(1, len(df.index)):
        previous = current - 1

        if df['close'][current] > df['upperband'][previous]:
            df['in_uptrend'][current] = True
        elif df['close'][current] < df['lowerband'][previous]:
            df['in_uptrend'][current] = False
        else:
            df['in_uptrend'][current] = df['in_uptrend'][previous]

            if df['in_uptrend'][current] and df['lowerband'][current] < df['lowerband'][previous]:
                df['lowerband'][current] = df['lowerband'][previous]

            if not df['in_uptrend'][current] and df['upperband'][current] > df['upperband'][previous]:
                df['upperband'][current] = df['upperband'][previous]
    return df


in_position = False

def check_buy_sell_signals(df):
    global in_position
    global big_uptrend
    global cv_ma120

    print("checking for buy and sell signals")
    print(df.tail(5))

    last_row_index = len(df.index) - 1
    previous_row_index = last_row_index - 1
    close95 = df['close'][-1] * 0.95
    ma120 = get_ma120("KRW-ETH")
    closevalue = df['close'][-1]

    if closevalue >= ma120 :
        cv_ma120 = True
        print("cv_ma120 >= ma120")
    else :
        cv_ma120 = False
        print("cv_ma1120 < ma120")

    if ((not df['in_uptrend'][previous_row_index] and df['in_uptrend'][last_row_index]) and (close95 > ma120))\
                or ((df['in_uptrend'][previous_row_index] and df['in_uptrend'][last_row_index]) and (close95 > ma120)) :
            if not in_position:
                try :
                    krw = upbit.get_balance("KRW")
                    upbit.buy_market_order("KRW-ETH", krw*0.998)
                    now = datetime.now()
                    print(now)
                    print("success to buy")
                    in_position = True
                except :
                    print("Buy 에러 발생")
            else:
                print("already in position, nothing to do")
    else :
        pass

    if (df['in_uptrend'][previous_row_index] and not df['in_uptrend'][last_row_index]) or not cv_ma120:
        if in_position:
            try :
                print("changed to downtrend -> sell")
                eth = upbit.get_balance("ETH")
                upbit.sell_market_order("KRW-ETH", eth)
                now=datetime.now()
                print(now)
                print("success to sell")
                in_position = False
            except :
                print("Sell 에러 발생")
        else:
            print("You aren't in position, nothing to sell")

def run_bot():
    print(f"Fetching new bars for {datetime.now().isoformat()}")
    bars = pyupbit.get_ohlcv("KRW-ETH", interval="minute240")
    df = pd.DataFrame(bars[:-1], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

    supertrend_data = supertrend(df)
    
    check_buy_sell_signals(supertrend_data)

schedule.every(10).seconds.do(run_bot)

while True:
    try :
        schedule.run_pending()
    except:
        print("에러 발생")
    time.sleep(1)


