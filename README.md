PROJECT_NAME=
gcloud config set project $PROJECT_NAME
gcloud services enable compute.googleapis.com
gcloud services enable container.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable cloudbuild.googleapis.com

gcloud artifacts repositories create hello-repo     --project=$PROJECT_NAME     --repository-format=docker     --location=europe-central2     --description="Docker repository"

gcloud builds submit   --tag europe-central2-docker.pkg.dev/$PROJECT_NAME/hello-repo/helloworld-gke .

gcloud container clusters create-auto helloworld-gke   --region europe-central2

kubectl apply -f dep1.yaml 
kubectl apply -f dep2.yaml 
kubectl apply -f dep3.yaml 


kubectl apply -f service.yaml


# To change selector you can modify 'change.py' and run
python change.py
