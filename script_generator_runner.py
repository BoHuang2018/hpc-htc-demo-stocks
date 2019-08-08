import argparse
import csv
import subprocess
import time


def generate_condor_submit_trigger_text(csv_file_queue):
    """
    To generate a text file looks like htcondor-submit-tasks
    :param csv_file_queue: Temporally, it is the file nasdaq_symbols_all.csv
    :return:
    """

    def get_queue_value(csv_file=csv_file_queue):
        """
        To get a proper value of queue for function generate_condor_submit_trigger_text().
        Temporally, we use the number of rows of nasdaq_symbols_all.csv as value of queue
        :return:
        """
        with open(csv_file, 'r') as symbol_csv_file:
            csv_symbol_reader = csv.reader(symbol_csv_file)
            company_numbers = sum(1 for row in csv_symbol_reader)
        del csv_file
        return company_numbers

    queue = get_queue_value(csv_file_queue)
    with open('htcondor-submit-tasks-app.txt', 'w') as htc:
        htc.write('executable              = task_randomwalk_process-app.sh \n')
        htc.write('arguments               = $(Process) \n')
        htc.write('transfer_input_files    = randomwalk_process.py,nasdaq_symbols_all.csv \n')
        htc.write('Transfer_Output_Files   = "" \n')
        htc.write('when_to_transfer_output = ON_EXIT \n')
        htc.write('log                     = run.$(Process).log \n')
        htc.write('Error                   = err.$(Process) \n')
        htc.write('Output  = out.$(Process) \n')
        htc.write('queue {}'.format(queue))
    return queue


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
        trp.write('index=$(($1 + 2)) \n')
        trp.write('stockfile=nasdaq_symbols_all.csv \n')
        trp.write('stock=$(awk "NR == ${index} {print; exit}" ${stockfile} | cut -d, -f1) \n')
        trp.write('export HOME=`pwd` \n')
        trp.write('chmod +x ./randomwalk_process.py \n')
        trp.write('./randomwalk_process.py --stock_symbols_file ${stockfile} --start_date %s --end_date %s ' 
                  '--stock_symbol ${stock} --HTCondor_env 1 > ${stock}.csv \n' % (start_date, end_date))
        trp.write('CLOUDSDK_PYTHON=/usr/bin/python '
                  'gsutil cp ${stock}.csv gs://hpc-htc-demo-stocks/stock_simulations_based_on_%s_%s/'
                  % (start_date, end_date))
    return True

'''
def finished_jobs_counter():
    """
    To count the number of simulation files in specific folder in Cloud Storage,
    when the number is same as total account, we know htcondor has finished the jobs
    :param total_amount: Int. We use the value of queue in funciton generate_condor_submit_trigger_text()
    :return:
    """
    return subprocess.check_output("gsutil du gs://hpc-htc-demo-stocks/output_single_stock/ | wc -l", shell=True)
'''


def _parse_args():
    parser = argparse.ArgumentParser('To trigger the condor_submit',
                                     description="To set the number of jobs in the txt file.")
    parser.add_argument('--queue', default='nasdaq_symbols_all.csv',
                        help="the number of jobs would be submitted to HTcondor cluster.")
    parser.add_argument('--start_date', type=str, required=True, help='the start date of historical stock prices.')
    parser.add_argument('--end_date', type=str, required=True, help='the end date of historical stock prices.')
    return parser.parse_args()


def main():
    args = _parse_args()
    the_queue = generate_condor_submit_trigger_text(csv_file_queue=args.queue)
    generate_condor_sh_file(start_date=args.start_date, end_date=args.end_date)
    condor_start_time = time.time()
    subprocess.call("condor_submit htcondor-submit-tasks-app.txt", shell=True)

    finished_jobs = 0
    while finished_jobs < the_queue:
        finished_jobs = \
            int(subprocess.check_output("gsutil du gs://hpc-htc-demo-stocks/stock_simulations_based_on_%s_%s/ | wc -l"
                                        % (args.start_date, args.end_date), shell=True))
        time.sleep(0.5)
    condor_end_time = time.time()
    print("The queue has been finished, {} jobs by condor_submit, within {} seconds"
          .format(finished_jobs, condor_end_time-condor_start_time))


if __name__ == '__main__':
    main()

