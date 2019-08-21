import argparse
import csv
import subprocess
import time
import pandas_datareader as web


def generate_condor_submit_trigger_text(queue):
    """
    To generate a text file looks like htcondor-submit-tasks
    :param csv_file_queue: Temporally, it is the file nasdaq_symbols_all.csv
    :return:
    """
    with open('htcondor-submit-tasks-app.txt', 'w') as htc:
        htc.write('executable              = task_randomwalk_process-app.sh \n')
        htc.write('arguments               = $(Process) \n')
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
    To generate a .sh file looks like task_random_process.sh
    :param start_date: Str. The start date of historical stock prices. For example '2017-01-01'
    :param end_date: Str. The end date of historical stock prices. For example '2019-01-01'
    :param stock_symbol: Str. Symbol of stock. Like AAPL
    :return:
    """
    with open('task_randomwalk_process-app.sh', 'w') as trp:
        trp.write('#! /bin/bash \n')
        trp.write('index=$(($1+1)) \n')
        trp.write('stockfile=nasdaq_symbols_in_rows.csv \n')
        # trp.write('stock_symbols_sequence=$(awk "NR == ${index} {print; exit}" ${stockfile} | cut -d, -f1) \n')
        trp.write('stock_symbols_sequence=$(awk "NR == ${index} {print; exit}" ${stockfile}) \n')
        trp.write('export HOME=`pwd` \n')
        trp.write('chmod +x ./randomwalk_multiprocess.py \n')
        trp.write('./randomwalk_multiprocess.py --start_date %s --end_date %s '
                  '--stock_symbols_list ${stock_symbols_sequence} \n'
                  % (start_date, end_date))
        trp.write('CLOUDSDK_PYTHON=/usr/bin/python '
                  'gsutil cp *.csv gs://hpc-htc-demo-stocks/stock_simulations_based_on_%s_%s/'
                  % (start_date, end_date))
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
        time.sleep(0.1)
    condor_end_time = time.time()
    print("The queue has been finished, {} jobs by condor_submit, within {} seconds"
          .format(finished_jobs, condor_end_time-condor_start_time))


if __name__ == '__main__':
    main()

