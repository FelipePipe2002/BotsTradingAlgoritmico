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
        ("short_sma_period", 10),
        ("long_sma_period", 60),
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

    def next(self):
        if self.order:
            return

        if not self.position:
            # Buy when closing price is below the lower Bollinger Band
            # and short-term SMA is above long-term SMA
            if (self.dataclose[0] < self.bollinger.lines.bot[0] and
                    self.short_sma > self.long_sma and
                    self.short_sma > self.long_sma[-1]):
                self.order = self.buy()

        else:
            # Sell when closing price is above the upper Bollinger Band
            # and short-term SMA is below long-term SMA
            if (self.dataclose[0] > self.bollinger.lines.top[0] and
                    self.short_sma < self.long_sma and
                    self.short_sma < self.long_sma[-1]):
                self.order = self.sell()

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
        fromdate=datetime.datetime(1995, 1, 1),
        # Do not pass values before this date
        todate=datetime.datetime(2014, 12, 31),
        # Do not pass values after this date
        reverse=False)

    # Add the Data Feed to Cerebro
    cerebro.adddata(data)

    # Set our desired cash start
    cerebro.broker.setcash(1000.0)

    # Add a FixedSize sizer according to the stake
    cerebro.addsizer(bt.sizers.FixedSize, stake=10)
    

    # Set the commission
    cerebro.broker.setcommission(commission=0.0)

    # Print out the starting conditions
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

    # Run over everything
    cerebro.run()

    # Print out the final result
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

    # Plot the result
    #cerebro.plot()