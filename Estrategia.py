from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import datetime  # For datetime objects
import os.path  # To manage paths
import sys  # To find out the script name (in argv[0])

# Import the backtrader platform
import backtrader as bt


# Create a Stratey
class Strategy(bt.Strategy):
    params = (
        ("bollinger_period", 20),
        ("bollinger_dev", 2),
        ("short_sma_period", 15),
        ("long_sma_period", 60),
        ("stop_loss_percent", 0.3),
    )

    def log(self, txt, dt=None):
        ''' Logging function for this strategy'''
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        # Keep a reference to the "close" line in the data[0] dataseries
        self.dataclose = self.datas[0].close

        # To keep track of pending orders and buy price/commission
        self.order = None
        self.buyprice = None
        self.buycomm = None

        # Add Bollinger Bands indicator
        self.bollinger = bt.indicators.BollingerBands(
            self.datas[0], period=self.params.bollinger_period, devfactor=self.params.bollinger_dev)

        # Add short-term and long-term Simple Moving Averages
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

        returns = [self.dataclose[i] - self.dataclose[i - 1] for i in range(-1, -4, -1)]
        return all(return_ < 0 for return_ in returns)
    
    def good_days(self):
        returns = [self.dataclose[i] - self.dataclose[i - 1] for i in range(-1, -4, -1)]
        return all(return_ > 0 for return_ in returns)

    def is_hammer(self):
        # Check if the current candle is a hammer
        close = self.dataclose[0]
        open_ = self.datas[0].open[0]
        high = self.datas[0].high[0]
        low = self.datas[0].low[0]

        # Conditions for a bullish hammer
        return close > open_ and self.bad_days()

    def is_deadman(self):
        # Check if the current candle is a hammer
        close = self.dataclose[0]
        open_ = self.datas[0].open[0]
        high = self.datas[0].high[0]
        low = self.datas[0].low[0]

        # Conditions for a bullish hammer
        return close < open_ and self.good_days()


    def next(self):
        if self.order:
            return

        if not self.position:
            # Buy when closing price is below the lower Bollinger Band
            # and short-term SMA is above long-term SMA
            if (self.dataclose[0] < self.bollinger.lines.bot[0] and
                self.short_sma > self.long_sma and self.short_sma > self.long_sma[-1]
                ) or self.is_hammer():
                size = int(self.broker.get_cash() * .9 / self.dataclose)

                self.order = self.buy(size=size)

        else:
            # Sell when closing price is above the upper Bollinger Band
            # and short-term SMA is below long-term SMA
            if (self.dataclose[0] > self.bollinger.lines.top[0] and
                self.short_sma < self.long_sma and self.short_sma < self.long_sma[-1]
                ) or self.is_deadman():
                self.order = self.sell(size=self.position.size)

if __name__ == '__main__':
    # Create a cerebro entity
    cerebro = bt.Cerebro()

    # Add a strategy
    cerebro.addstrategy(Strategy)

    # Datas are in a subfolder of the samples. Need to find where the script is
    # because it could have been called from anywhere
    modpath = os.path.dirname(os.path.abspath(sys.argv[0]))
    datapath = os.path.join(modpath, './datas/orcl-1995-2014.txt')

    # Create a Data Feed
    data = bt.feeds.YahooFinanceCSVData(
        dataname=datapath,
        # Do not pass values before this date
        fromdate=datetime.datetime(1996, 1, 1),
        # Do not pass values before this date
        todate=datetime.datetime(2014, 12, 31),
        # Do not pass values after this date
        reverse=False)

    # Add the Data Feed to Cerebro
    cerebro.adddata(data)

    # Set our desired cash start
    cerebro.broker.setcash(100000.0)
    

    # Set the commission
    cerebro.broker.setcommission(commission=0.0001)

    # Print out the starting conditions
    print('Start Portfolio Value: %.2f, Cash: %.2f' % (cerebro.broker.getvalue(), cerebro.broker.get_cash()))

    # Run over everything
    cerebro.run()

    # Print out the final result with both portfolio value and cash
    print('Final Portfolio Value: %.2f, Cash: %.2f' % (cerebro.broker.getvalue(), cerebro.broker.get_cash()))


    # Plot the result
    cerebro.plot()
    