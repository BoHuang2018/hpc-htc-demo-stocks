# hpc-htc-demo-stocks
## A demo to build high-throughput-computing cluster on Google Cloud Platform
This repository presents a lightweight demo of HTCondor cluster on GCP (Google Cloud Platform). Such a cluster can be applied 
to many fields' work. We do only stocks price simulation with random walk process and Monte-Carlo in this repository. 

### Background 
This repository got expired by an example from Google Cloud Solution (link: https://cloud.google.com/solutions/analyzing-portfolio-risk-using-htcondor-and-compute-engine), 
which deploys a high-throughput-computing (htc) cluster with HTCondor and do simulation for four stocks (AMZN, GOOG, FB, NLFX) with random walk process
and Monte-Carlo (1000 simulations for each stock).

### What we will do
1. #### Scale up to thousands stocks (all companies listed on Nasdaq)
   We would go through all companies listed on Nasdaq, the current amount is 8856 (updated per day). For each stock, it will do 1000 random-walk 
   simulations, it says near nine million simulations all together.
   By my Macbook pro (2.8 GHz Core i7, 16 GB RAM), the whole process takes over three hours. We will see the HTC cluster on GCP does such work in just minutes. 
   
2. #### Adjust size of the cluster
   The original example fixes size of the HTC-cluster as six virtual machines: one central manager, one jobs submitter and four workers. 
   In this repository, users can set number of the machines. Though, please estimate cost of the machines. For example, I used 400 predefined n1-standard-1 virtual machines and 400 preemptible n1-standard-1 virtual machines. The cluster took around 3 minutes to do simulation for all 8851 companies listed on Nasdaq, current price for 
   n1-standard-1 is 0.0475$ and 0.01$ per machine per hour for predefined and preemptible respectively, then cost for the 3 minutes work was 1.15$ (= 3 x 400 / 60 x (0.0475 + 0.01)), in addition, it costed money for used RAM of those machines. 

3. #### Speed further up by parallel computing 
   We can speed further up by using more VMs and more advanced VMs. For example, it will run faster if it allocates n1-standard-4 instead of n1-standard-1. But the cost will fly up. 
   Parallel computing helps. Since we use n1-standard-4 VMs, we should run computation in 4 parallel processes. In my recent test, it allocated eight n1-standard-4 VMs, did 4-processing in each VMs. It took only 290 seconds. 
   While it took 360 seconds with 32 n1-standard-4 VMs but single processing per machine.        
   
### Architecture and process of this reporsitory
![architecture and process](https://github.com/BoHuang2018/hpc-htc-demo-stocks/blob/master/HPC-HTC-DEMO-STOCKS.png)
The above image shows the architecture of the HTC-cluster and its working process. Let's go through it block by block from left to right. 

#### Prepare Storage Bucket and VM-images
All relevant code and simulation results will be stored in Cloud Storage. We would build a bucket in Cloud Storage for this project.
We would build reusable virtual machines images and leave them on Google Cloud Platform. It would be very easy to create the HTC-cluster when we need it, and destroy it after the work to stop money counting. 

#### Deployment HTCondor-cluster
With the prepared virtual machine images and coding files, the HTConder-cluster can be created by one line of command. 
This cluster consists of one central manager machine (condor-master), one submitter machine (condor-submit) and several worker machines (condor-compute). 

Once we trigger the cluster, submitter machine will distribute the jobs to worker machines and the manager would cover the scheduling things. If some of the workers are stuck or lie down, the relevant jobs will be rescheduled to other workers by the manager machine.

#### Model work in each condor-compute
Each worker machine will run the assigned codes with assigned data, deliver results to Cloud Storage. 

### Step by Step Implementation 
Now let's implement this repository step by step. The blocks in gray is what we will do with the Cloud Shell's terminal. 

#### 0. Before you start
First of all, please make sure that you have created project and enabled billing on Google Cloud Platform. 

We highly recommend to use GCP's Cloud Shell with Linux as your platform. 
Please install Cloud-SDK into your own Linux system if you would not use GCP's Cloud Shell. 
OSX is not a good choice because of the Makefile. 

In the following steps, it assumes that we work on the Cloud Shell.

#### 1. Migrate the files to Cloud Shell
1.1  Grab the whole project from GitHub : 

   `user_name@cloudshell:~ (your project)$ git clone https://github.com/BoHuang2018/hpc-htc-demo-stocks.git`
   
   Or,
   
   `user_name@cloudshell:~ (your project)$ git clone https://github.com/avalonsolutions/avalonx-stockpriceprediction.git`
   
1.2  Move into this repository's folder, we will run some 'make'-command :

   `$ cd hpc-htc-demo-stocks`

   Or,
   
   `$ cd avalonx-stockpriceprediction`

##### 1.3  Build bucket in Cloud Storage and transport files there :

   `$ make upload bucketname=hpc-htc-demo-stocks`
       


#### 2. Build Virtual Machine Images and create cluster

##### 2.1 Build images for manager machine, submitter machine and worker machine: 
   
   `$ make createimages`

2.2 Create the HTC-cluster:

   `$ make createcluster`
   
Note the "properties" in the .yaml file (condor-cluster.yaml), we can increase the number of "count" (number of predefined virtual machines)
and "pvmcount" (number of preemptible virtual machines) to hundreds and even thousands. Please estimate the
cost before you use those big numbers. 

Now we set 0 as 'count' and 8 as 'pvmcount', and the 'instancetype' is 'n1-standard-4'. 
It says we will use only 8 preemptible virtual machines in the type of n1-standard-4. 
The total number of virtual machines would be 10, because we need one for condor-master and one for condor-submit.
    

#### 3. Let the HTC-cluster work for you.     

Now your high-throughput-computing cluster is ready, it's time to run it. 


As we have mentioned above, we need to trigger the condor-submit, then it would submit the long sequence of simulation 
jobs to the condor-compute machines. Before we trigger it, we need to transport the necessary files from Storage to 
condor-submit's disk: 
    
   > user_name@cloudshell:~/hpc-htc-demo-stocks (project)$ make ssh bucketname=hpc-htc-demo-stocks
    
Then we can trigger the condor-submit:

   > user_name@cloudshell:~/hpc-htc-demo-stocks (project)$ gcloud compute ssh condor-submit --zone us-east1-b --command "python3 script_generator_runner.py --start_date=2017-06-01 --end_date=2019-06-01"

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
     > user_name@cloudshell:~/hpc-htc-demo-stocks (project)$ make destroycluster


The End.       
            
          





