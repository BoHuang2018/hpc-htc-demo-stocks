#!/usr/bin/env python3
"""
This program implements such a process : scrape historical price --> Monte-Carlo simulation --> write in CSV file
    for a sequence of stocks by multiprocessing (Pool).
There is no crossfire between processes, i.e. each process will do all simulation work assigned to it.
This program will be used on GCP virtual machines through HTCondor.

The following functions will be called in this order:
    main() --> _parse_args() --> run_pool() --> to_simulate_single_stock() --> _get_data()
"""
import argparse
import pandas_datareader as web
import pandas
import numpy
import csv
import math
import logging
from random import randint
from multiprocessing import Pool

logging.basicConfig(filename='model_test.log', datefmt='%m/%d/%Y %I:%M:%S %p',
                    level=logging.DEBUG,
                    format='%(asctime)s %(filename)s: %(message)s',
                    filemode='w')
logging.getLogger("urllib3").propagate = False
# logging.getLogger("requests").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

TRADING_DAYS = 252  # Number of trading days on stock, i.e. time interval of simulation


def _get_data(company_symbol, historical_data, number_of_iteration=1000):
    """
    Do the random walk process in monte-carlo simulation.
    :param company_symbol: String. Like 'AAPL', 'GOOG'
    :param historical_data: pandas.core.frame.Dataframe. Historical stock prices downloaded by pandas_datareader
    :param number_of_iteration: Int. Number of simulations of Monte-Carlo
    :return: List of float. Results of Monte-Carlo simulation.
    """
    # calculate the compound annual growth rate (CAGR) which will give us
    # our mean return input (mu)
    #
    days = (historical_data.index[-1] - historical_data.index[0]).days
    # print(marketd.index[-1], " , ", marketd.index[0])
    cagr = (historical_data['Close'][-1] / historical_data['Close'][1]) ** (365.0 / days) - 1
    #
    # create a series of percentage returns and calculate the annual
    # volatility of returns
    #
    historical_data['Returns'] = historical_data['Close'].pct_change()
    vol = historical_data['Returns'].std() * numpy.sqrt(TRADING_DAYS)
    data = []
    starting_price = historical_data['Close'][-1]
    position = randint(10, 1000) * 10
    for i in range(number_of_iteration):
        daily_returns = numpy.random.normal(cagr / TRADING_DAYS,
                                            vol / math.sqrt(TRADING_DAYS),
                                            TRADING_DAYS) + 1
        price_list = [company_symbol, position, i, starting_price]
        for x in daily_returns:
            price_list.append(price_list[-1] * x)
        data.append(price_list)
    return data


def to_simulate_single_stock(company_symbol_start_date_end_date):
    """
    Do monte-carlo simulation for a single stock symbol, self.company, have historical prices
    for every trading day in the given time interval, and generate a csv for the stock.
    Path for the csv file is the current folder.
    If the API cannot offer available data with given time-interval and stock symbol, it would write csv with
    '_empty_1/2' in the name:
          _empty_1 : the historical data is not available because of the time interval
          _empty_2 : the historical data is not available because of the stock symbol (not available on Yahoo finance)
    The reason to generate empty csv is to make the number of csv files in Cloud Storage bucket be same as the
    number of stocks in the Nasdaq Company List. When the two numbers are same, the system will send a report that all
    simulations are done.

    This reporting mechanism is a complement for HTCondor has no programmatic reporting function.
    :param: company_symbol_start_date_end_date: Tuple of Strings. Like ('AAPL', '2017-01-01', '2019-01-01')
    :return:
    """
    company_symbol = company_symbol_start_date_end_date[0]
    start_date = company_symbol_start_date_end_date[1]
    end_date = company_symbol_start_date_end_date[2]
    try:
        raw_data = web.get_data_yahoo(company_symbol, start=start_date, end=end_date)
        # If the earliest date of historical price is three days away from the given start_date, we will assume the
        # historical data is not available, and generate an empty csv file
        if abs((raw_data.index[0] - pandas.Timestamp(start_date)).days) > 3:
            logger.info("Start date for {} is {} while start_date = {}, so skip this stock"
                        .format(company_symbol, raw_data.index[0], start_date))
            with open(company_symbol + '_empty_1.csv', 'w') as csvfile:
                # csv_writer = writer(csvfile)
                csvfile.write("No content, because of the time interval issue.")
        else:
            simulations = _get_data(company_symbol=company_symbol, historical_data=raw_data, number_of_iteration=1000)
            with open(company_symbol + '.csv', 'w', newline='') as csvfile:
                csv_writer = csv.writer(csvfile)
                for row in simulations:
                    csv_writer.writerow(row)
            del simulations  # To save RAM
            del raw_data
            return True
    except (KeyError, TypeError, IndexError, web._utils.RemoteDataError) as err:
        logger.error(err)
        # Sometimes, a stock symbol is not available anymore, but has not been deleted from Nasdaq Company List
        logger.info("Not access to historical price for {}, please check Yahoo Finance manually".format(company_symbol))
        with open(company_symbol + '_empty_2.csv', 'w') as csvfile:
            csvfile.write("No content, because of no historical price in Yahoo.")
    return True


def _parse_args():
    parser = argparse.ArgumentParser('randomwalk_multiprocess',
                                     description='Monte-Carlo simulation of stock prices '
                                                 'behavior based on data from Yahoo')
    parser.add_argument('--start_date', type=str, default='2017-01-01',
                        help="the start date of historical time interval")
    parser.add_argument('--end_date', type=str, default='2019-01-01',
                        help='the end date of historical time interval')
    parser.add_argument('--stock_symbols_list', type=str, help='a sequence of stock symbols splitted by "," ')
    return parser.parse_args()


def run_pool(start_date, end_date, stock_symbols):
    stock_symbols_list = stock_symbols.split(',')
    # if '\r' in stock_symbols_list[-1]:
    stock_symbols_list[-1] = stock_symbols_list[-1][:-1] if '\r' in stock_symbols_list[-1] else stock_symbols_list[-1]
    # print something in the out.* file in condor-submit machine, easy to troubleshoot
    print(len(stock_symbols_list))
    print(stock_symbols_list)
    # organize the parameters for multiprocessing
    parameters_list = [(symbol, start_date, end_date) for symbol in stock_symbols_list]
    with Pool(4) as pool:
        pool.map(to_simulate_single_stock, parameters_list) # (function, list)
    return True


def main():
    args = _parse_args()
    run_pool(start_date=args.start_date, end_date=args.end_date, stock_symbols=args.stock_symbols_list)


if __name__ == '__main__':
    main()