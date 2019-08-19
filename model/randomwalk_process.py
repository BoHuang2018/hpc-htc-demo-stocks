#!/usr/bin/env python3
import sys
import argparse
import pandas_datareader as web
# import pandas
import numpy
import csv
import math
import time
import logging
from random import randint

logging.basicConfig(filename='./model_test.log', datefmt='%m/%d/%Y %I:%M:%S %p',
                    level=logging.DEBUG,
                    format='%(asctime)s %(filename)s: %(message)s',
                    filemode='w')
logging.getLogger("urllib3").propagate = False
# logging.getLogger("requests").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

TRADING_DAYS = 252  # Number of trading days on stock, i.e. time interval of simulation


def get_all_symbols_and_write():
    """
    The generate a csv file including companies' names, symbols and other information. Now we assume the file is
    'Nasdaq Company List'. Because of Nasdaq update the file everyday. So we should run this function everyday to follow
    the official updating.
    :return:
    """
    all_nasdaq = web.get_nasdaq_symbols()
    all_nasdaq.to_csv(path_or_buf='./data/nasdaq_symbols_all.csv')
    return True


class DataModel(object):
    """
    This class does the random walk process based on the historical stocks prices (close prices) from Yahoo Finance.
    Users can select :
        1. company_numbers: The companies having 'best simulation' in the simulation interval.
            For example, 'company_numbers = 10' requires ten stocks with best simulation based on the selected
            interval of historical prices.
        2. time interval of historical data: start_date ~ end_date, for instance 2017-01-01 -- 2018-01-01
        3. company_symbol: Symbol of a stock. This lets people to check simulation for a specific stock.
    Please note that the above '1' and '3' would not be used together. It says that users can select '1 & 2' or
    '1 & 3'.
      - 1 & 2 : To get stocks with best simulations based on the selected interval of historical prices.
           For example, 1. company_numbers = 10
                        2. start_date = 2017-01-01, end_date = 2019-01-01
                        Then this class will tell us the top 10 stocks based on the historical prices
                        from 2017-01-01 to 2019-01-01
      - 3 & 2 : To get simulations of a given stock based on its historical prices from 2017-01-01 to 2019-01-01
    """

    def __init__(self, start_date, end_date, company_symbol, HTCondor_environment,
                 companies_symbols_file='./data/nasdaq_symbols_all.csv',
                 output_path='./data/output/', output_path_single='./data/output_single_stock/'):
        """
        To initialize the variables.
        :param company_numbers: Int. Number of companies would be picked out with top simulations.
        :param start_date: String. Staring date with historical prices, like '2017-01-01'
        :param end_date:   String. Ending date with historical prices, like '2019-01-01'
        :param company_symbol: String. Symbol of a stock, for instance 'AAPL', 'GOOG'
        :param companies_symbols_file: Path of csv file involving companies' symbols, names and other information.
                                       The file can be generated and updated by the function
                                                                                    get_all_symbols_and_write()
        :param output_path: The path to store simulation results in csv file when we do simulations for a set of stocks
        :param output_path_single: The path to store simulation results in csv file when we do simulations for single stock
        :param HTCondor_environment: INT 0 or 1. If 1, we should use _write_csv_stdout(self) to write simulation result
        """
        self.verbose = False
        self.company = company_symbol
        self.companies_symbols_file = companies_symbols_file
        # self.company_numbers = company_numbers
        self.start_date = start_date
        self.end_date = end_date
        self.symbols_for_simulation = None
        self._raw_data = None
        self.data = None
        self.iter_count = 1000
        self.from_csv = None
        self.output_path = output_path
        self.output_path_single = output_path_single
        # to get the number of days a stock must have in the historical interval
        self.the_correct_number_of_days = len(web.get_data_yahoo('QQQ', start=start_date, end=end_date))
        # if there is no specific company_symbol, then we go through all companies in Nasdaq Company List
        if isinstance(company_symbol, type(None)):
            with open(self.companies_symbols_file, 'r') as symbol_csv_file:
                csv_symbol_reader = csv.reader(symbol_csv_file)
                self.company_numbers = sum(1 for row in csv_symbol_reader)
        else:
            self.company_numbers = None
        self.HTCondor_environment = HTCondor_environment

    def _get_symbols(self):
        """
        Get symbols of the stocks will be simulated from the csv file stored in self.companies_symbols_file .
        List of String, like [... , 'YCOM', 'YCS', 'YELP', ...] will be transferred to self.symbols_for_simulation
        :return: True
        """
        symbols_list = []
        with open(self.companies_symbols_file, 'r') as symbol_csv_file:
            csv_symbol_reader = csv.DictReader(symbol_csv_file)
            for line in csv_symbol_reader:
                if len(symbols_list) < self.company_numbers:
                    symbols_list.append(line['NASDAQ Symbol'])
                    del line['NASDAQ Symbol']
        self.symbols_for_simulation = symbols_list

    def _from_yahoo_api(self, symbol):
        """
        Get the close price data from yahoo finance api.
        The prices will be transferred to self._raw_data
        :param symbol: String. Item in self.symbols_for_simulation
        :return: True
        """
        try:
            df = web.get_data_yahoo(symbol, start=self.start_date, end=self.end_date)
        except (KeyError, TypeError, IndexError) as err:
            logger.error(err)
            return False
        except:
            logger.error("Unexpected Error: ", sys.exc_info()[0])
            return False
        self._raw_data = df  # ['Close']
        return True

    def _write_csv_all(self):
        """
        To write the simulations into a csv file in the self.output_path
        :return: True
        """
        with open(self.output_path + self.company + '.csv', 'w', newline='') as csvfile:
            csv_writer = csv.writer(csvfile)
            for row in self.data:
                csv_writer.writerow(row)
        return True

    def _write_csv_single(self):
        """
        To write the simulations into a csv file in the self.output_path
        :return: True
        """
        with open(self.output_path_single + self.company + '.csv', 'w', newline='') as csvfile:
            csv_writer = csv.writer(csvfile)
            for row in self.data:
                csv_writer.writerow(row)
        return True

    def _write_csv_stdout(self):
        """
        To write the simulation-result into a csv file with sys.stdout
        When we run this program with HTCondor environment, we would use this function
        :return:
        """
        csv_writer = csv.writer(sys.stdout)
        for row in self.data:
            csv_writer.writerow(row)

    def _get_data(self):
        """
        Do the monte-carlo simulation and transferred the result to self.data
        :return: True
        """
        marketd = self._raw_data
        #
        # calculate the compound annual growth rate (CAGR) which will give us
        # our mean return input (mu)
        #
        days = (marketd.index[-1] - marketd.index[0]).days
        # print(marketd.index[-1], " , ", marketd.index[0])
        cagr = (marketd['Close'][-1] / marketd['Close'][1]) ** (365.0 / days) - 1
        #
        # create a series of percentage returns and calculate the annual
        # volatility of returns
        #
        marketd['Returns'] = marketd['Close'].pct_change()
        vol = marketd['Returns'].std() * numpy.sqrt(TRADING_DAYS)
        data = []
        starting_price = marketd['Close'][-1]
        position = randint(10, 1000) * 10
        for i in range(self.iter_count):
            daily_returns = numpy.random.normal(cagr / TRADING_DAYS,
                                                vol / math.sqrt(TRADING_DAYS),
                                                TRADING_DAYS) + 1
            price_list = [self.company, position, i, starting_price]
            for x in daily_returns:
                price_list.append(price_list[-1] * x)
            data.append(price_list)
        self.data = data
        return True

    def to_simulate_all(self):
        """
        Do monte-carlo simulations for all stocks have historical prices of every trading day in the given time interval,
        and generate individual csv files for each stock. Path for the csv files is self.output_path
        :return: True
        """
        assert isinstance(self.company, type(None)) and not isinstance(self.company_numbers, type(None)), \
            "self.company must be None and self.company_numbers must be an available integer " \
            "when we get simulation on a set of stocks."
        self._get_symbols()
        for s in self.symbols_for_simulation:
            self.company = s
            # print("Symbol : ", s, "; -- ", self.symbols_for_simulation.index(s))
            if self._from_yahoo_api(symbol=s):
                # print("Length: ", len(self._raw_data))
                if len(self._raw_data) == self.the_correct_number_of_days:
                    # print(self._raw_data.index[0], self._raw_data.index[-1])
                    self._get_data()
                    if self.HTCondor_environment == 1:
                        self._write_csv_stdout()
                    else:
                        self._write_csv_all()
                    del self.data
                    del self._raw_data
            else:
                continue
        del self.company
        return True

    def to_simulate_single_stock(self):
        """
        Do monte-carlo simulation for a single given stock, self.company,
        have historical prices for every trading day in the given
        time interval, and generate a csv for the stock. Path for the csv file is self.output_path_single
        :return:
        """
        assert not isinstance(self.company, type(None)) and isinstance(self.company_numbers, type(None)), \
            "self.company must be an available stock symbol " \
            "and self.company_numbers must be None when we get single simulation."
        if self._from_yahoo_api(symbol=self.company):
            try:
                len(self._raw_data) == self.the_correct_number_of_days
            except:
                print("No correct historical length-{} for {} between {} and {}, "
                      "please check Yahoo Finance manually"
                      .format(self.the_correct_number_of_days, self.company, self.start_date, self.end_date))
                # raise KeyboardInterrupt
                sys.exit(1)
            self._get_data()
            if self.HTCondor_environment == 1:
                self._write_csv_stdout()
            else:
                self._write_csv_single()
            del self.data
            del self._raw_data
        else:
            print("Not access to historical price for {} between {} and {}, "
                  "please check Yahoo Finance manually".format(self.company, self.start_date, self.end_date))
            sys.exit(1)
        return True

    def run(self):
        if not isinstance(self.company, type(None)):  # then we would do simulation for single stock
            self.to_simulate_single_stock()
        else:
            self.to_simulate_all()


def _parse_args():
    parser = argparse.ArgumentParser('randomwalk_process',
                                     description='Monte-Carlo simulation of stock prices '
                                                 'behavior based on data from Yahoo')
    parser.add_argument('--start_date', type=str, default='2017-01-01',
                        help="the start date of historical time interval")
    parser.add_argument('--end_date', type=str, default='2019-01-01',
                        help='the end date of historical time interval')
    parser.add_argument('--stock_symbols_file', help='path to csv file involving stock symbols')
    parser.add_argument('--stock_symbol', type=str, help="symbol of a stock")
    parser.add_argument('--HTCondor_env', type=int, help="in HTCondor environment or not.")
    return parser.parse_args()


def main():
    logger.info("Starting model/model_test.py")
    start_time = time.time()
    args = _parse_args()
    data_model = DataModel(start_date=args.start_date,
                           end_date=args.end_date,
                           companies_symbols_file=args.stock_symbols_file,
                           company_symbol=args.stock_symbol,
                           HTCondor_environment=args.HTCondor_env)
    data_model.run()
    end_time = time.time()
    logger.info("Execution time for simulating {} companies: {}."
                .format(data_model.company_numbers, end_time - start_time))


if __name__ == '__main__':
    # get_all_symbols_and_write()
    main()
