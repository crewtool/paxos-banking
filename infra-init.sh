#!/bin/bash
# Script for managing infrastructure

project_id=$1
current_project_id=$(gcloud config get-value project --verbosity none)
if [ -z "$current_project_id" ]; then
  while true; do
    if [ -z "$project_id" ]; then
      read -e -p "No project set. Provide project name: " project_id
    else
      break
    fi
  done
fi

if [ "$current_project_id" == "$project_id" ] || [ "$project_id" == "" ]; then
	project_id=$current_project_id
	echo "Project ID: $project_id"
else
 	# Check if the project exists
  if gcloud projects describe "$project_id" &> /dev/null; then
    gcloud config set project $project_id
    echo -e "\033[0;33mProject ID: $project_id\033[0m"
  else
    # Ask the user if they want to create the project.
    read -e -p "Project '$project_id' does not exist. Do you want to create it? (Y/n) " REP
    if [[ $REP == "y" || $REP == "Y" || $REP == "" ]] ; then
      # Create the project.
      gcloud projects create "$project_id"
      gcloud config set project $project_id
      echo -e "\033[0;32mProject ID: $project_id\033[0m"
    else
      echo "Did not create a project. Exiting."
      exit 0
    fi
  fi
fi

echo "Enabling apis..."
gcloud services enable compute.googleapis.com
gcloud services enable container.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable firestore.googleapis.com
gcloud services enable appengine.googleapis.com

# Check if the compute region is already set to europe-central2.
region=$(gcloud config get-value compute/region)
if [ "$region" != "europe-central2" ]; then
  # Set the compute region to europe-central2.
  region="europe-central2"
  echo "Updating region..."
  gcloud config set compute/region $region
  echo -e "\033[0;33mRegion: $region\033[0m"
else
  echo "Region: $region"
fi

echo "Creating service account..."
service_account="bankingserviceaccount"
gcloud iam service-accounts create $service_account
gcloud projects add-iam-policy-binding $project_id --member="serviceAccount:$service_account@$project_id.iam.gserviceaccount.com" --role="roles/owner"
gcloud iam service-accounts keys create bankingkey.json --iam-account=$service_account@$project_id.iam.gserviceaccount.com

echo "Creating repository..."
gcloud artifacts repositories create banking-repo --project=$project_id --repository-format=docker --location=$region --description="Banking service docker repository"

echo "Firestore creation..."
gcloud app create --region $region
gcloud firestore databases create --region $region
