# hpc-htc-demo-stocks
### *A demo simulating thousands stocks with high-performance-computing cluster in high-throughput-computing structure*
This repository presents a lightweight demo of HTCondor cluster on GCP (Google Cloud Platform). Such a cluster can be applied 
to many fields' work. We do only stocks price simulation with random walk process and Monto-Carlo in this repository. 

### Background 
This repository got expired by an example on High-throug from Google Cloud Solution (link: https://cloud.google.com/solutions/analyzing-portfolio-risk-using-htcondor-and-compute-engine), 
which deploys a high-throughput-computing (htc) cluster with HTCondor and do simulation for four stocks (AMZN, GOOG, FB, NLFX) with random walk
and Monte-Carlo (1000 simulation for each stock).

###### To present the power of HTC-cluster on GCP, we did change on the following aspects:

1. Increase the subjects of simulation to thousands stocks (all companies listed on Nasdaq)
   The project would go through all companies listed on Nasdaq, the amount is around 8851. For each stock, it will do 1000 random-walk 
   simulation, it says near nine million simulations all together.
   By my Macbook pro (2.8 GHz Core i7, 16 GB RAM), the whole process takes over three hours. On GCP, we can build a HTC-cluster consists of 
   hundred virtual-machines, and shrink the working time to around 3 minutes. 
   
2. Download the historical data by given time interval instead of using stored data
   The original example use a fixed historical data with fixed time interval. This repository allows each working machine in the cluster
   call the API, pandas_datareader, to downloaded the historical stock prices from Yahoo. And user can set 'start_date' and 'end_date' to 
   decide the time interval. 

3. Size of the cluster is adjustable
   The original example fixes size of the HTC-cluster as six virtual machines: one central manager, one jobs submiter and four workers. 
   In this example, users can set number of the machines. Though, please estimate cost of the machines. For example, I used 400 predefined n1-standard-1 virtual machines and 400 preemptible n1-standard-1 virtual machines. The cluster took around 3 minutes to do simulation for all 8851 companies listed on Nasdaq, current price for 
   In this example, users can set number of the machines. Though, please estimate cost of the machines. For example, I used 400 n1-standard-1 
   n1-standard-1 is 0.0475$ and 0.01$ per machine per hour for predefined and preemptible respectively, then cost for the 3 minutes work was 1.15$ (= 3 x 400 / 60 x (0.0475 + 0.01)), in addition, it costed money for used RAM of those machines. Please be aware of the the real cost would be different, because some preemptible virtual machines could be reclaimed by other GCP-users. If you use Google's price calculator to do price estimation, please be aware of the discounting items. In this case, the discounting might not work. It's a little complicated topic beyond this repository, we would like to build another repostitory on that.
   
### Architecture and process of this reporsitory
![architecture and process](https://github.com/BoHuang2018/hpc-htc-demo-stocks/blob/master/HPC-HTC-DEMO-STOCKS.png)
The above image shows the architecture of the HTC-cluster and working process of this repository. Let's go through it block by block from left to right. 

###### Prepare Storage Bucket and VM-images
For simplicity, we store all relevant code and files in Cloud Storage. It facilitates invoke the whole project and running code across machines connected to Internet. For saving money, we would build reusable virtual machines images and leave them on Google Cloud Platform. Then it would be very easy to create the HTC-cluster when we need it, and destroy it after the work to stop money counting. We would create three images for condor-master, condor-submit and condor-compute respectively. 

###### Deployment HTCondor-cluster
With the prepared virtual machine images, make-file, yaml-files and .sh files, the cluster can be created by one command. The cluster consists of one central manager machine (condor-master), one submiter machine (condor-submit) and several worker machines (condor-compute). What the manager machine would do is invisible and out of our operation. Once we trigger the cluster with a sequence of jobs, the submiter machine would distribute the jobs to worker machines and the manager would cover the scheduling things. If some of the workers are stuck or lie down, the relevant jobs will be rescheduled to other machines by the manager machine.

###### Model work in each condor-compute
This block is independent of the HTC-cluster, i.e. we can put other models in this block to apply the cluster to other task. At last, we upload the simulation results to Cloud Storage waiting for further process. 

### Step by step implementation 
Now let's implement this repository step by step. 

#### 0. Before you start
Because we will deploy the HTC-cluster on GCP, please make sure that you have created project and enabled billing on Google Cloud Platform. 

We highly recommanded to use GCP's Cloud Shell with Linux-Ubuntu as your platform. Because we have wrappered many command-line operation in Make file, OSX is not a good choise. Please install Cloud-SDK into your own Linux system if you would not use GCP's Cloud Shell. 

In the following content, it assumes that we work on the Cloud Shell.

#### 1. Migrate the files to Cloud Shell 




