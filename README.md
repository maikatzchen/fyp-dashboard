## Cloud Platform for Predicting Natural Disasters (FYP)

This project is a cloud-based platform designed to predict **flood events** in Malaysia, specifically states that are prone to floods like Terengganu, Kelantan and Pahang, using real-time and historical environmental data by  integrating **classification machine learning model** with cloud services to support early warning systems and disaster preparedness.

## Project Objective

To develop a scalable and intelligent cloud solution that can:
- Predict potential flood risks using AI/ML models
- Ingest and process real-time data from multiple sources
- Provide a user-friendly dashboard for early flood alerts
- Send alerts in case of flood risks

## Key Technologies

- **Google Cloud Platform (GCP)**  
  - **Vertex AI** - Training and deploying AI/ML model
  - **Cloud Run** - Host dashboard as a serverless containerized web app
  - **Cloud Build** - Used with GitHub CI/CD for building and deploying app
  - **Google Earth Engine (GEE)** (not GCP-native but tightly integrated) - IMERG Rainfall Data
  - **Cloud IAM** - Manage access and permissions for services and APIs
  - **Cloud Storage** - Store model training datasets
  - **Firestore** - NoSQL database to store user emails for email alerts

- **Open-Meteo API**
  - Real-time weather input

- **Python**
  - Data preprocessing, model training and dashboard development

- **Streamlit**
  - Dashboard visualization

## Features

- Real-time rainfall monitoring
- AI-based flood risk classification
- Interactive dashboard for visualization and alerts
- Email notifications in case of predicted flood risks


