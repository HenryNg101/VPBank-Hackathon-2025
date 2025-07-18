# Semantic Chunking & Global Search LLM System

This project implements a scalable LLM-based system for **semantic chunking** and **global document search**, leveraging serverless infrastructure and containerized services on AWS.

## 🔍 Overview

The system processes input documents, including docx, pdf, image, and excel files, converts them into HTML or text, semantically chunks the content using LLMs, and indexes it for later semantic search. The infrastructure is provisioned via AWS CloudFormation and orchestrates the interaction between Lambda functions, containerized services, and cloud storage.

---

## 📁 Project Structure

### `CFTemplate.yaml`

AWS CloudFormation template that defines all necessary cloud resources, including:

* Lambda functions
* API Gateway
* ECS/ECR services
* IAM roles
* S3 buckets and permissions
* DynamoDB table

### `docx-to-html-image/`

Dockerized microservice responsible for converting `.docx` documents into clean HTML. This prepares the content for downstream semantic processing.

### `lambdaFunctions/`

Contains AWS Lambda function code used to:

* Orchestrate document processing workflows
* Trigger container jobs
* Handle storage and metadata operations

### `semantic_chunking/`

Dockerized microservice responsible for:

* Running LLM-based semantic chunking on document content
* Generating vector representations or structured chunks
* Preparing the data for search indexing

---

## 🧭 System Architecture

![Architecture Diagram](./images/Data%20Flow%20&%20Use%20of%20AWS.png)

The system is fully cloud-native and modular. Each component can be updated or scaled independently, ensuring flexibility and maintainability.

---

## 🚧 TODO / Future Work

* [ ] Add example input/output data
* [ ] Integrate vector database or search backend
* [ ] Improve chunking pipeline efficiency
* [ ] Write deployment & usage instructions
* [ ] Integrate frontend Next.js application's code
