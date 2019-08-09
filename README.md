# hpc-htc-demo-stocks
#### _A demo using high-performance-computing in high-throughput-computing_
This repository presents a lightweight demo of HTCondor cluster on GCP (Google Cloud Platform). Such a cluster can be applied 
to many fields' work. We do only stocks price simulation with random walk process and Monto-Carlo in this repository. 

### Background 
This repository got expired by an example from Google Cloud Solution (link: https://cloud.google.com/solutions/analyzing-portfolio-risk-using-htcondor-and-compute-engine), 
which deploys a high-throughput-computing (htc) cluster with HTCondor and do simulation for four stocks (AMZN, GOOG, FB, NLFX) with random walk process
and Monte-Carlo (1000 simulations for each stock).

#### To present the power of HTC-cluster on GCP, we do change on the following aspects:

1. ##### Increase the subjects of simulation to thousands stocks (all companies listed on Nasdaq)
   We would go through all companies listed on Nasdaq, the current amount is 8851. For each stock, it will do 1000 random-walk 
   simulations, it says near nine million simulations all together.
   By my Macbook pro (2.8 GHz Core i7, 16 GB RAM), the whole process takes over three hours. On GCP, we will build a HTC-cluster consists of 
   34 virtual-machines, and shrink the working time to around 6 minutes. 
   
2. ##### Download the historical data by given time interval instead of using stored data
   The original example use a fixed historical data with fixed time interval. This repository allows each working machine in the cluster
   to call the API, pandas_datareader, to downloaded the historical stock prices from Yahoo. The time interval would be set by parameters 
   "start_date" and "end_date".

3. ##### Size of the cluster is adjustable
   The original example fixes size of the HTC-cluster as six virtual machines: one central manager, one jobs submiter and four workers. 
   In this example, users can set number of the machines. Though, please estimate cost of the machines. For example, I used 400 predefined n1-standard-1 virtual machines and 400 preemptible n1-standard-1 virtual machines. The cluster took around 3 minutes to do simulation for all 8851 companies listed on Nasdaq, current price for 
   n1-standard-1 is 0.0475$ and 0.01$ per machine per hour for predefined and preemptible respectively, then cost for the 3 minutes work was 1.15$ (= 3 x 400 / 60 x (0.0475 + 0.01)), in addition, it costed money for used RAM of those machines. 
   
   
### Architecture and process of this reporsitory
![architecture and process](https://github.com/BoHuang2018/hpc-htc-demo-stocks/blob/master/HPC-HTC-DEMO-STOCKS.png)
The above image shows the architecture of the HTC-cluster and its working process. Let's go through it block by block from left to right. 

##### Prepare Storage Bucket and VM-images
For simplicity, we store all relevant code and files in Cloud Storage. It facilitates invoking the whole project across machines connected to Internet. We would build reusable virtual machines images and leave them on Google Cloud Platform. It would be very easy to create the HTC-cluster when we need it, and destroy it after the work to stop money counting. We would create three images for condor-master, condor-submit and condor-compute respectively. 

##### Deployment HTCondor-cluster
With the prepared virtual machine images, make-file, yaml-files and .sh files, the cluster can be created by one line of command. The cluster consists of one central manager machine (condor-master), one submiter machine (condor-submit) and several worker machines (condor-compute). What the manager machine would do is invisible and out of our operation. Once we trigger the cluster with a sequence of jobs, the submiter machine would distribute the jobs to worker machines and the manager would cover the scheduling things. If some of the workers are stuck or lie down, the relevant jobs will be rescheduled to other workers by the manager machine.

##### Model work in each condor-compute
This block is independent of the HTC-cluster, i.e. we can put other models in this block to apply the cluster to other task. At last, we upload the simulation results to Cloud Storage waiting for further process. 


### Step by Step Implementation 
Now let's implement this repository step by step. 

#### 0. Before you start
Because we will deploy the HTC-cluster on GCP, please make sure that you have created project and enabled billing on Google Cloud Platform. 

We highly recommend to use GCP's Cloud Shell with Linux as your platform. Because we have wrappered many command-line operations in Make file, OSX is not a good choise. Please install Cloud-SDK into your own Linux system if you would not use GCP's Cloud Shell. 

In the following content, it assumes that we work on the Cloud Shell.

#### 1. Migrate the files to Cloud Shell
    1. Grab the whole project from GitHub : 
    
       user_name@cloudshell:~ (your project)$ git clone https://github.com/BoHuang2018/hpc-htc-demo-stocks.git
    
    2. Move into this repository's folder, we will run some 'make'-command :
    
       user_name@cloudshell:~ (your project)$ cd hpc-htc-demo-stocks
    
    3. Build bucket in Cloud Storage and store files :
    
       user_name@cloudshell:~/hpc-htc-demo-stocks (project)$ make upload bucketname=hpc-htc-demo-stocks
       
   The third command involves line 41~52 in Makefile. Let's go through the key commands in that block
   1. gsutil mb gs://${bucketname}  # make a bucket with the given name in Cloud Storage
   2. gsutil cp source-path gs://destination-path  # copy the files to the bucket 
   
   Note: 'hpc-htc-demo-stocks' is a fixed name in this repository, type-error leads to other errors.
   
#### 2. Build Virtual Machine Images and create cluster
    The process to build images is : create instance (virtual machines) --> stop instance --> create image --> delete instance
    The whole process can be done by the following command: 
        
        user_name@cloudshell:~ (your project)$ git make createimages
    
The above simple command calls line 8~32 in Makefile. Let's look at some key points:

    1. --image debian-9-stretch-v20190729
       
       We use the newest verison of debian-9, because the old versions (2018) does not support the package 'pandas_datareader' which
       would be used to grab historical data from Yahoo.
    
    2. --metadata-from-file startup-script=startup-scripts/$@.sh
       
       This uses the startup-files to drive vitual machine to do something once it boots up. In this case, every time we create
       the HTC-cluster, all vitural machines of the cluster will do something. For example, in the file /startup-scripts/condor-compute.sh,
       we can see 
       
       1. sudo apt install python3-pip -y  # install pip 
       2. pip3 install pandas-datareader   # install package pandas-datareader 
    
    3. This block would be gone through three times, because we need to build images for central manager machine (condor-master),
       submitter machine (condor-submit) and worker machine (condor-compute) individually. 
       
   After the images are ready, we can create the HTC-cluster by this command :
       
       user_name@cloudshell:~/hpc-htc-demo-stocks (project)$ make createcluster
       
   We can see what stay behind is the .jinja files and .yaml files in /deplaymentmanager. The files are using the Google's Cloud Deployment Manager. 
    
Note the "properties" in the .yaml file (condor-cluster.yaml), we can increase the number of "count" (number of predefined virtual machines)
and "pvmcount" (number of preemptible virtual machines) to hundreds and even thousands. Please estimate the
cost before you use those big numbers. 

Now we use 12 as 'count' and 20 as 'pvmcount', and the 'instancetype' is 'n1-standard-4'. 
It says we will use 12 predefinded virtual machines and 20 preemptible virtual machines in the type of n1-standard-4. 
The total number of virtual machines would be 34, because we need one for condor-master and one for condor-submit.
    

#### 3. Let the HTC-cluster work for you.     

    Now your high-throughput-computing cluster is ready, it's time to run it. 
    
    To get more intuitive control, you can load to the condor-submit's terminal by this command
    
        user_name@cloudshell:~/hpc-htc-demo-stocks (project)$ gcloud compute ssh condor-submit --zone us-east1-b
    
    Then the terminal would become like this:
    
        user_name@condor-submit:~$ 
    
    Let's write 'exit' and come back to our Cloud Shell's terminal:
        
        user_name@cloudshell:~/hpc-htc-demo-stocks (project)$
        
    As we have mentioned above, we need to trigger the condor-submit, then it would submit the long sequence of simulation 
    jobs to the condor-compute machines. Before we trigger it, we need to transport the necessary files from Storage to 
    condor-submit's disk: 
        
        user_name@cloudshell:~/hpc-htc-demo-stocks (project)$ make ssh bucketname=hpc-htc-demo-stocks
        
    Then we can trigger the condor-submit:
    
        user_name@cloudshell:~/hpc-htc-demo-stocks (project)$ gcloud compute ssh condor-submit --zone us-east1-b --command "python3 script_generator_runner.py --start_date=2017-06-01 --end_date=2019-06-01"
    
    In the above line, we choose the historical stock prices from 2017-06-01 to 2019-06-01. The terminal would print like 
    
        Submitting job(s)..........
        
    There will be many '.' because there is a long sequence jobs what condor-submit needs to submit. 
    After a while, the terminal print something about the jobs are finished and tell the total time consuming. 
    
    In your Storage's bucket, gs://hpc-htc-demo-stocks, there finds a new folder named as 
    'stock_simulation_based_on_2017-06-01_2019_06_01', which includes .csv files storing the simulation results. 
    
   
    
#### 4. Look into the condor-submit:
    If you are curious about what condor-submit do, you can load back to the condor-submit's terminal:
        
        user_name@cloudshell:~/hpc-htc-demo-stocks (project)$ gcloud compute ssh condor-submit --zone us-east1-b
        
    And use the HTCondor's function 'condor_q':
        
        user_name@condor-submit:~$ condor_q
    
    Then it would list all jobs, tell you how many has be done, how many is on hold, and so on.
    
    At the same time, there would finds files named like 'err.1' ... 'err.8800' ... 'out.', 'run.' which 
    would be very useful if you want to see more detailed info. 
    
In the folder /htcondor/*, the files are not used in this case. Yes, we need two files like them to trigger the cluster.
Once you trigger the condor-submit by "python3 script_generator_runner.py ...", the python file will generate two similar
files at real time, and make the cluster work. 

#### Clean up   
Please remember to delete all resource on GCP if you would not use the HTC-cluster for a while, or the billing from GCP will 
be heavy because the cluster using 34 virtual machines. 
    
    There are two ways to clean up
    1. Delete the whole project on the GCP 
    2. Destroy the HTC-cluster and delete the bucket in Cloud Storage (the bucket is not expensive) by GCP console 
       To destroy the cluster :
          user_name@cloudshell:~/hpc-htc-demo-stocks (project)$ make destroycluster


The End.       
            
          





