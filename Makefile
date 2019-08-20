# Makefile
#
# basic commandlines stored that execute the various pieces of the demonstration

show:
	cat README.md

createimages: condor-master condor-compute condor-submit
	@echo "createimages - done"

condor-master condor-compute condor-submit:
	@if [ -z "$$(gcloud compute images list --quiet --filter='name~^$@' --format=text)" ]; then \
	   echo "" ;\
	   echo "- building $@" ;\
	   echo ""; \
	   gcloud compute instances create $@-template \
	     --zone us-east1-b \
	     --machine-type n1-standard-4 \
	     --image debian-9-stretch-v20190729 \
	     --image-project debian-cloud \
	     --boot-disk-size=10GB \
	     --metadata-from-file startup-script=startup-scripts/$@.sh ; \
	   sleep 300 ;\
	   gcloud compute instances stop --zone=us-east1-b $@-template ;\
	   gcloud compute images create $@  \
	     --source-disk $@-template   \
	     --source-disk-zone us-east1-b   \
	     --family htcondor-debian ;\
	   gcloud compute instances delete --quiet --zone=us-east1-b $@-template ;\
	else \
	   echo "$@ image already exists"; \
	fi


deleteimages:
	-gcloud compute images delete --quiet condor-master
	-gcloud compute images delete --quiet condor-compute
	-gcloud compute images delete --quiet condor-submit


upload:
ifeq ($(bucketname),)
	@echo "to upload the datafile (make sure you first run make download to pull the data from quandl.  then rerun this command"
	@echo "adding the gcs bucketname to create and push the data to."
	@echo "  make upload bucketname=<some bucket name>"
else 
	@echo "using ${bucketname}"
	-gsutil mb gs://${bucketname}
	gsutil cp model/* gs://${bucketname}/model/
	gsutil cp *.py gs://${bucketname}/
endif

createcluster:
	@echo "creating a condor cluster using deployment manager scripts"
	gcloud deployment-manager deployments create condor-cluster --config deploymentmanager/condor-cluster.yaml
	
destroycluster:
	@echo "destroying the condor cluster"
	gcloud deployment-manager deployments delete condor-cluster

ssh:
ifeq ($(bucketname),)
	@echo "set the bucketname in order to copy some of the data and model files to the submit host"
	@echo "  make sshtocluster bucketname=<some bucket name>"
	gcloud compute ssh condor-submit
else
	@echo "using ${bucketname}"
	@echo "before sshing to the submit host, let me copy some of the files there to make"
	@echo "it easier for you."
	@echo "  - copying the model"
	gcloud compute ssh condor-submit --command "gsutil cp gs://${bucketname}/model/* ." --zone us-east1-b
	@echo "  - copying the entrance python file: script_generator_runner.py"
	gcloud compute ssh condor-submit --command "gsutil cp gs://${bucketname}/script_generator_runner.py ." --zone us-east1-b
	@echo "now just sshing"
endif

bq: 
ifeq ($(bucketname),)
	@echo "to upload result file to bigquery, rerun this command but add the bucketname"
	@echo "  make bq bucketname=<some bucket name>"
else
	@echo "loading data from gs://${bucketname}/output/*.csv to bigquery table varBQTable"
	-bq mk montecarlo_outputs
	bq load --autodetect --source_format=CSV ${GOOGLE_CLOUD_PROJECT}:montecarlo_outputs.vartable gs://${bucketname}/output/*.csv 
	cat bq-aggregate.sql | bq query --destination_table montecarlo_outputs.portfolio > /dev/null
	@echo "\n"
	@echo "done..."
endif

rmbq:
	@echo "deleting dataset from bq: ${GOOGLE_CLOUD_PROJECT}:montecarlo_outputs"
	bq rm -rf ${GOOGLE_CLOUD_PROJECT}:montecarlo_outputs
	@echo "\n"
	@echo "done..."


clean:
	rm link.file WIKI_PRICES*.zip WIKI_PRICES*.csv 
