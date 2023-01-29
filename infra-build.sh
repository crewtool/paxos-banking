#!/bin/bash

echo "Building images..."
gcloud builds submit --config build.yaml .
