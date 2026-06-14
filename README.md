# 🧠 Expression V1

> A serverless, AI-powered mental well-being application that combines facial expression detection with personalised journaling to deliver compassionate, real-time mental health guidance. **NOT DESIGNED TO REPLACE THERAPY OR COUNSELLING, TO BE SEEN AS SELF STUDY**

**Live Demo:** [https://dc2b8er08430l.cloudfront.net/)
**Repository:** [https://github.com/Edidevi/Expression](

---

## 📖 Overview
<img width="305" height="303" alt="image" src="https://github.com/user-attachments/assets/73985d78-a945-4e96-aa47-242caf53e07f" />

Expression is a mental health journaling app built on AWS that meets users wherever they are — whether they check in daily or only reach out when they an outlet for extreme emotions. Users can log how they're feeling through written input and detected facial expressions. The app then uses AI to deliver personalised, empathetic well-being advice grounded in their actual emotional state.

The core insight behind the project: not everyone can fully label their own emotions. Emotional intelligence can be taught and learned — and this app helps bridge that gap through gentle, AI-guided reflection.


---

## ✨ Features

- **Mood Journaling** — Users describe how they're feeling in text; entries are stored per user with timestamps.
- **Facial Expression Detection** — Integrates with Amazon Rekognition to detect visual emotional cues.
- **AI-Powered Advice** — Uses Amazon Bedrock (Claude Haiku) to generate compassionate, 2-sentence therapeutic guidance tailored to each user's mood, expression data, and journal text.
- **User Authentication** — Secure sign-up and login via Amazon Cognito (email-based, JWT-authenticated).
- **Journal History** — Past entries are retrieved and displayed per authenticated user from DynamoDB.
- **Fully Serverless** — No servers to manage; the entire backend runs on AWS Lambda, API Gateway, and CloudFront.

---

## 🏗️ Architecture

```
GitHub (source)
     │
     ▼
AWS CodePipeline  ──►  CodeBuild (Build + PostDeploy)
     │
     ▼
AWS CloudFormation (DeployStack)
     │
     ├── S3 (static website hosting)
     ├── CloudFront (CDN, HTTPS)
     ├── Amazon Cognito (auth)
     ├── API Gateway HTTP API (JWT-secured routes)
     ├── AWS Lambda (Python 3.12 handler)
     │     ├── Amazon Rekognition (expression detection)
     │     ├── Amazon Bedrock / Claude Haiku (AI advice)
     │     └── DynamoDB (entry storage)
     └── DynamoDB Table (mood-journal entries)
```

### CI/CD Pipeline (AWS CodePipeline)

As shown in the pipeline screenshot, deployments flow through four stages, all triggered by a push to the `main` branch:

| Stage | Tool | Description |
|---|---|---|
| **Source** | GitHub (via GitHub App) | Detects code changes |
| **Build** | AWS CodeBuild | Packages `lambda/index.py` into `lambda.zip` |
| **Deploy** | AWS CloudFormation | Deploys/updates the full app stack |
| **PostDeploy** | AWS CodeBuild | Syncs website assets to S3 and invalidates the CloudFront cache |

---

## 🗂️ Repository Structure

```
Expression/
├── lambda/
│   └── index.py              # Python 3.12 Lambda handler
├── website/                  # Static frontend (HTML/JS/CSS)
├── cloudformation.yaml       # App stack: Lambda, API, DynamoDB, Cognito, CloudFront
├── buildspec.yml             # Build phase: packages Lambda zip + artifacts
└── buildspec-post.yml        # Post-deploy: S3 sync + CloudFront invalidation
```

> **Architecture note:** The pipeline infrastructure (CodePipeline, CodeBuild, ArtifactsBucket, IAM roles) lives in a separate `pipeline.yaml` deployed once manually. `cloudformation.yaml` contains only the application stack — ensuring the pipeline never attempts to recreate itself on each run.

---

## ☁️ AWS Services Used

| Service | Role |
|---|---|
| **S3** | Static website hosting for the frontend |
| **CloudFront** | HTTPS CDN delivery (`d381ybey4gt21f.cloudfront.net`) |
| **Cognito** | User pool, email-based sign-up/login, JWT token issuance |
| **API Gateway (HTTP)** | Exposes `/detect`, `/resolve`, and `/entries` routes |
| **Lambda (Python 3.12)** | Core backend logic — mood processing, Rekognition calls, Bedrock AI |
| **Amazon Rekognition** | Detects facial expressions from user images |
| **Amazon Bedrock (Claude Haiku)** | Generates personalised mental well-being advice |
| **DynamoDB** | Stores journal entries (userId + entryId composite key) |
| **CodePipeline / CodeBuild** | CI/CD pipeline for automated deployment |
| **CloudFormation** | Infrastructure as Code for the full app stack |

---

## 🔌 API Endpoints

All routes are JWT-authenticated via Cognito and served through API Gateway.

| Method | Route | Description |
|---|---|---|
| `POST` | `/detect` | Submit mood, expression data, and journal text → returns AI advice + saves entry |
| `POST` | `/resolve` | Alias endpoint for mood resolution flow |
| `GET` | `/entries` | Retrieve all past journal entries for the authenticated user |

---

## 🚀 Deployment

### Prerequisites

- AWS CLI configured with appropriate permissions
- An existing CodeConnections connection to GitHub
- The pipeline stack already deployed manually

### Deploy the App Stack Manually (first time)

```bash
aws cloudformation deploy \
  --template-file cloudformation.yaml \
  --stack-name face-expression-lab \
  --capabilities CAPABILITY_IAM
```

### Subsequent Deployments

Push to the `main` branch — CodePipeline handles everything automatically:

1. Detects the change via GitHub App
2. Runs `buildspec.yml` to package the Lambda
3. Deploys `cloudformation.yaml` via CloudFormation
4. Runs `buildspec-post.yml` to sync the website and bust the CloudFront cache

---

## 💡 Design Decisions

**Why personalised AI advice rather than static content?**
Mental health is not one-size-fits-all. What works for one person may not help another. By combining the user's own written description with their detected visual expression, the AI can tailor advice to their specific state at that moment — making the app useful whether someone checks in every day or only when they're struggling.

**Why facial expression detection?**
Not everyone can fully articulate why they feel a certain way. Emotional intelligence is a learned skill, and the app uses Rekognition to surface cues the user may not have consciously registered, giving the AI more context for a more accurate and helpful response.

**Why serverless?**
The fully serverless architecture (Lambda + API Gateway + DynamoDB + CloudFront) means zero infrastructure management, automatic scaling, and pay-per-request pricing — ideal for a wellness app with variable usage patterns.

---

## 🛠️ Tech Stack

- **Frontend:** HTML, JavaScript, CSS (72.5% of codebase)
- **Backend:** Python 3.12 on AWS Lambda (27.5% of codebase)
- **AI Model:** `anthropic.claude-haiku-4-5-20251001-v1:0` via Amazon Bedrock
- **Infrastructure:** AWS CloudFormation (IaC)
- **CI/CD:** AWS CodePipeline + CodeBuild

---
