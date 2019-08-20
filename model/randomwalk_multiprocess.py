#!/usr/bin/env python3
import sys
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


def _write_csv_stdout(self):
    """
    To write the simulation-result into a csv file with sys.stdout
    When we run this program with HTCondor environment, we would use this function
    :return:
    """
    csv_writer = csv.writer(sys.stdout)
    for row in self.data:
        csv_writer.writerow(row)


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


def get_all_symbols_in_rows(rows=100, output_csv_name='nasdaq_symbols_in_rows.csv'):
    all_nasdaq = web.get_nasdaq_symbols().index
    # total_number = len(all_nasdaq)
    # print(len(all_nasdaq))
    number_of_normal_rows = len(all_nasdaq) // (rows-1)
    number_of_last_row = len(all_nasdaq) % (rows-1)
    with open(output_csv_name, 'w') as csv_file:
        csv_writer = csv.writer(csv_file)
        for r in range(rows):
            if r < rows-1:
                csv_writer.writerow(list(all_nasdaq[r * number_of_normal_rows: (r+1) * number_of_normal_rows]))
            else:
                csv_writer.writerow(list(all_nasdaq[-1*number_of_last_row:]))
    return True


def _from_yahoo_api(symbol, start_date, end_date):
    """
    Get the close price data from yahoo finance api.
    The prices will be transferred to self._raw_data
    :param symbol: String. Item in self.symbols_for_simulation
    :param start_date: String. Like '2017-01-01'
    :param end_date: String.   Like '2019-01-01'
    :return: True
    """
    try:
        df = web.get_data_yahoo(symbol, start=start_date, end=end_date)
        return df
    except (KeyError, TypeError, IndexError, web._utils.RemoteDataError) as err:
        logger.error(err)
        pass
    return None


def to_simulate_single_stock(company_symbol_start_date_end_date):
    """
    Do monte-carlo simulation for a single given stock symbol, self.company,
    have historical prices for every trading day in the given
    time interval, and generate a csv for the stock. Path for the csv file is self.output_path_single
    :param: company_symbol_start_date_end_date: Tuple of Strings. Like ('AAPL', '2017-01-01', '2019-01-01')
    :return:
    """
    company_symbol = company_symbol_start_date_end_date[0]
    start_date = company_symbol_start_date_end_date[1]
    end_date = company_symbol_start_date_end_date[2]
    raw_data = _from_yahoo_api(symbol=company_symbol, start_date=start_date, end_date=end_date)
    if not isinstance(raw_data, type(None)):

        # if there are ten days between the historical start-date and the parameter, start_date, 
        # then we ignore this stock
        if abs((raw_data.index[0] - pandas.Timestamp(start_date)).days) > 10:
            logger.info("Start date for {} is {} while start_date = {}, so skip this stock"
                        .format(company_symbol, raw_data.index[0], start_date))
            with open(company_symbol + '_empty.csv', 'w') as csvfile:
                csv_writer = csv.writer(csvfile)
                csv_writer.writerow("No content, because of the time interval issue.")
        else:    
            simulations = _get_data(company_symbol=company_symbol, historical_data=raw_data, number_of_iteration=1000)
            # csv_writer = csv.writer(sys.stdout)
            # for row in simulations:
            #     csv_writer.writerow(row)
            with open(company_symbol + '.csv', 'w', newline='') as csvfile:
                csv_writer = csv.writer(csvfile)
                for row in simulations:
                    csv_writer.writerow(row)
            # print("Get historical data from {} and simulation is done".format(company_symbol))
            return True
            del simulations
    else:
        logger.info("Not access to historical price for {} between {} and {}, "
                    "please check Yahoo Finance manually".format(company_symbol, start_date, end_date))
        with open(company_symbol + '_empty.csv', 'w') as csvfile:
            csv_writer = csvfile.write(csvfile)
            csv_writer.writerow("No content, because of no historical price in Yahoo.")
    del raw_data
    return True


def _parse_args():
    parser = argparse.ArgumentParser('randomwalk_process',
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
    parameters_list = [(symbol, start_date, end_date) for symbol in stock_symbols_list]
    with Pool(4) as pool:
        pool.map(to_simulate_single_stock, parameters_list) # (function, list)
    return True


def main():
    args = _parse_args()
    get_all_symbols_in_rows(rows=128)
    run_pool(start_date=args.start_date, end_date=args.end_date, stock_symbols=args.stock_symbols_list)


if __name__ == '__main__':
    main()