"""
This is the entrance program of the whole project.

It implements such a process:
    main() --> _parse_args() --> get_all_symbols_in_rows()
        --> generate_condor_submit_trigger_text() --> generate_condor_sh_file()
            --> trigger the whole project by subprocess.call()
                --> watch the number of csv files in Cloud Storage's bucket
                    --> report jobs are done

The generated .txt and .sh files would be transported to submitter machine of the HTCondor cluster, and
do their jobs there.
"""

import argparse
import csv
import subprocess
import time
import pandas_datareader as web


def generate_condor_submit_trigger_text(queue):
    """
    To generate a .txt-file to manage the submitter machine
    :param queue: Int. Number of jobs the will be submitted to worker machines from submitter machine to worker machines.
                  Now the number is decided by number of groups of stock symbols.
                  For example, we divide the 8856 stock symbols to 128 groups, queue = 128.
    :return:
    """
    with open('htcondor-submit-tasks-app.txt', 'w') as htc:
        htc.write('executable              = task_randomwalk_process-app.sh \n')
        htc.write('arguments               = $(Process) \n')
        #
        # Look at the functions mentioned in following two lines
        # randomwalk_multiprocess.py : this program will be runned in each worker machine
        # nasdaq_symbols_in_rows.csv : this file stores all stock symbols and organize them into lines,
        #                              each line has a certain number of symbols.
        #
        htc.write('transfer_input_files    = randomwalk_multiprocess.py,nasdaq_symbols_in_rows.csv \n')
        htc.write('Transfer_Output_Files   = "" \n')
        htc.write('when_to_transfer_output = ON_EXIT \n')
        htc.write('log                     = run.$(Process).log \n')
        htc.write('Error                   = err.$(Process) \n')
        htc.write('Output  = out.$(Process) \n')
        htc.write('queue {}'.format(queue))
    return True


def generate_condor_sh_file(start_date, end_date):
    """
    To generate a .sh file to manage worker machines in the following process:
        get a row of symbols --> do simulation and generate csv file --> transport csv file to Cloud Storage
    :param start_date: Str. The start date of historical stock prices. For example '2017-01-01'
    :param end_date: Str. The end date of historical stock prices. For example '2019-01-01'
    :param stock_symbol: Str. Symbol of stock. Like AAPL
    :return:
    """
    with open('task_randomwalk_process-app.sh', 'w') as trp:
        trp.write('#! /bin/bash \n')
        trp.write('index=$(($1+1)) \n')  # for-loop the rows of the csv file storing stock symbols
        trp.write('stockfile=nasdaq_symbols_in_rows.csv \n')  # this csv stores all stock symbols
        trp.write('stock_symbols_sequence=$(awk "NR == ${index} {print; exit}" ${stockfile}) \n')  # get a row
        trp.write('export HOME=`pwd` \n')
        trp.write('chmod +x ./randomwalk_multiprocess.py \n')   # trigger the main program to work
        trp.write('./randomwalk_multiprocess.py --start_date %s --end_date %s '
                  '--stock_symbols_list ${stock_symbols_sequence} \n'
                  % (start_date, end_date))
        trp.write('CLOUDSDK_PYTHON=/usr/bin/python '
                  'gsutil -m cp *.csv gs://hpc-htc-demo-stocks/stock_simulations_based_on_%s_%s/'
                  % (start_date, end_date))  # transport result to Cloud Storage
    return True


def _parse_args():
    parser = argparse.ArgumentParser('To trigger the condor_submit',
                                     description="To set the number of jobs in the txt file.")
    parser.add_argument('--queue', type=int, default='128',
                        help="the number of jobs would be submitted to HTCondor cluster.")
    parser.add_argument('--start_date', type=str, required=True, help='the start date of historical stock prices.')
    parser.add_argument('--end_date', type=str, required=True, help='the end date of historical stock prices.')
    return parser.parse_args()


def get_all_symbols_in_rows(rows, output_csv_name='nasdaq_symbols_in_rows.csv'):
    """
    Scrape all stock symbols from Nasdaq Company List and store them in a csv file by rows.
    :param rows: Int. Number of rows of stock symbols the csv file will have. Note that number of symbols in each row
                      would be same except the last row.
    :param output_csv_name: Int. Name of the csv file
    :return: Int. Total number of stock symbols in the Nasdaq Company List.
                  This returning would be used to judge the HTCondor cluster has done all jobs or not.
    """
    all_nasdaq = web.get_nasdaq_symbols().index
    number_of_normal_rows = len(all_nasdaq) // (rows-1)
    number_of_last_row = len(all_nasdaq) % (rows-1)
    with open(output_csv_name, 'w', newline='') as csv_file:
        csv_writer = csv.writer(csv_file)
        for r in range(rows):
            if r < rows-1:
                csv_writer.writerow(list(all_nasdaq[r * number_of_normal_rows: (r+1) * number_of_normal_rows]))
            else:
                csv_writer.writerow(list(all_nasdaq[(-1 * number_of_last_row) : ]))
    return len(all_nasdaq)


def main():
    args = _parse_args()
    total_number_of_symbols = get_all_symbols_in_rows(rows=args.queue)
    generate_condor_submit_trigger_text(queue=args.queue)
    generate_condor_sh_file(start_date=args.start_date, end_date=args.end_date)

    condor_start_time = time.time()

    subprocess.call("condor_submit htcondor-submit-tasks-app.txt", shell=True)
    finished_jobs = 0
    while finished_jobs < total_number_of_symbols:
        finished_jobs = \
            int(subprocess.check_output("gsutil du gs://hpc-htc-demo-stocks/stock_simulations_based_on_%s_%s/ | wc -l"
                                        % (args.start_date, args.end_date), shell=True))
        time.sleep(0.05)
    condor_end_time = time.time()
    print("The queue of {} has been finished, {} csv-files in Cloud Storage. It took {} seconds."
          .format(args.queue, finished_jobs, condor_end_time-condor_start_time))


if __name__ == '__main__':
    main()

