from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import datetime
import os.path
import sys

import backtrader as bt
import yfinance as yf
import locale

class Strategy(bt.Strategy):
    params = (
        ("bollinger_period", 20),
        ("bollinger_dev", 2),
        ("short_sma_period", 50),
        ("long_sma_period", 150),
        ("withdraw_profits",20),
        ("stop_loss",5),
        ("acceptable_margin",2),
        ("high_price_hammer",350),#3.5 veces el tamaño de la vela (close - open)
        ("low_price_hammer",10),
    )

    def log(self, txt, dt=None):
        ''' Logging function for this strategy'''
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        self.dataclose = self.datas[0].close
        
        self.order = None
        self.buyprice = None
        self.buycomm = None
        self.hammer_buy = None

        self.bollinger = bt.indicators.BollingerBands(
            self.datas[0], period=self.params.bollinger_period, devfactor=self.params.bollinger_dev)

        self.short_sma = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=self.params.short_sma_period)

        self.long_sma = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=self.params.long_sma_period)

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status in [order.Completed]:
            self.bar_executed = len(self)
        
        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

    def bad_days(self):
        balance = 0
        for i in range(-1,-4,-1):
            balance += self.dataclose[i] - self.dataclose[i-1]        
        return balance < - self.params.acceptable_margin #tendencia bajista considerable
    
    def good_days(self):
        balance = 0
        for i in range(-1,-4,-1):
            balance += self.dataclose[i] - self.dataclose[i-1]        
        return balance > self.params.acceptable_margin #tendencia bajista considerable

    def is_hammer(self): #compra 1 dia despues de encontrar el martillo
        close = self.dataclose[0]
        open_ = self.datas[0].open[0]
        high = self.datas[0].high[0]
        low = self.datas[0].low[0]
        
        if(close > open_ and (open_-low) > (close-open_)*(self.params.high_price_hammer/100) and ((high-close) < (close-open_)*(self.params.low_price_hammer/100)) and self.bad_days()):
            self.hammer_buy = self.datas[0].datetime.date()
            return True
        
        return False

    def is_deadman(self): #compra 1 dia despues de encontrar el martillo
        close = self.dataclose[0]
        open_ = self.datas[0].open[0]
        high = self.datas[0].high[0]
        low = self.datas[0].low[0]
        
        if(close < open_ and (close-low) > (open_-close)*(self.params.high_price_hammer/100) and (high-open_) < (open_-close)*(self.params.low_price_hammer/100) and self.bad_days()):
            return True
        
        return False
    
    def is_inverted_hammer(self): #compra 1 dia despues de encontrar el martillo
        close = self.dataclose[0]
        open_ = self.datas[0].open[0]
        high = self.datas[0].high[0]
        low = self.datas[0].low[0]
        
        if(close > open_ and (high-close) > (close-open_)*(self.params.high_price_hammer/100) and not((low-open_) < (close-open_)*-(self.params.low_price_hammer/100)) and self.bad_days()):
            self.hammer_buy = self.datas[0].datetime.date()
            return True
        
        return False
        
    
    def sell_hammer(self):#vender 3 dias despues de encontrar el martillo
        if (self.hammer_buy is not None and self.datas[0].datetime.date() - self.hammer_buy >= datetime.timedelta(days=2)): 
            self.hammer_buy = None
            return True
        return False
            
    def is_shooting_Star(self):
        close = self.dataclose[0]
        open_ = self.datas[0].open[0]
        high = self.datas[0].high[0]
        low = self.datas[0].low[0]
        
        if(close < open_ and (high-close) > (open_-close)*(self.params.high_price_hammer/100) and not((low-close) < (open_-close)*-(self.params.low_price_hammer/100)) and self.good_days()):
            self.hammer_buy = self.datas[0].datetime.date()
            return True
        
        return False
    
    def stop_loss(self):
        return self.dataclose[0] < self.buyprice * (1 - self.params.stop_loss / 100)

    def next(self):
        if self.order:
            return
        if not self.position:
            if (
                (self.dataclose[0] < self.bollinger.lines.bot[0]) or
                (self.short_sma > self.long_sma and self.short_sma[-1] < self.long_sma[-1]) or 
                (self.is_hammer()) or
                (self.is_inverted_hammer())
               ):
                size = int(self.broker.get_cash() * .9 / self.dataclose)
                self.buyprice = self.dataclose[0]
                self.order = self.buy(size=size)
            

        else:
            if (
                (self.short_sma < self.long_sma and self.short_sma[-1] > self.long_sma[-1]) or
                (self.is_shooting_Star()) or
                (self.sell_hammer()) or
                (self.stop_loss())  or
                (self.is_deadman())
               ):
                self.order = self.sell(size=self.position.size)
            


if __name__ == '__main__':
    cerebro = bt.Cerebro()

    cerebro.addstrategy(Strategy)

    modpath = os.path.dirname(os.path.abspath(sys.argv[0]))
    datapath = os.path.join(modpath, './datas/nvda-1999-2014.txt')

    '''
    data = bt.feeds.YahooFinanceCSVData(
        dataname=datapath,
        # Do not pass values before this date
        fromdate=datetime.datetime(1996, 1, 1),
        # Do not pass values before this date
        todate=datetime.datetime(2015, 12, 31),
        # Do not pass values after this date
        reverse=False)
    cerebro.adddata(data)
    '''
    symbol = "KO"
    data = yf.download(symbol, start="1996-01-01", end="2023-12-30")
    cerebro.adddata(bt.feeds.PandasData(dataname=data))
    

    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.0001)

    locale.setlocale(locale.LC_CTYPE, '')
    print('Start Portfolio Value: %.2f, Cash: %.2f' % (cerebro.broker.getvalue(), cerebro.broker.get_cash()))

    cerebro.run()
    
    print('Final Portfolio Value: %.2f, Cash: %.2f' % (cerebro.broker.getvalue(), cerebro.broker.get_cash()))


    cerebro.plot(style='candlestick')

