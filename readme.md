

### Overview

**Creportfolio  Backend** is a FastAPI-based application for managing user authentication, file uploads, and file operations, seamlessly integrated with Google Cloud Platform (GCP). It provides:

* 🔐 **JWT-based user authentication**
* ☁️ **File upload**
* 🗂️ **Listing and deleting uploaded files**
* 🔄 **Database migrations via Alembic**
* 🚀 **Deployment-ready with Docker and Google Cloud Run**

---

## ⚙️ Tech Stack

* **Backend**: Python, FastAPI
* **Database**: PostgreSQL on Cloud SQL
* **AI Tools**: LangChain (planned integration)
* **Authentication**: JWT
* **Deployment**: Docker + Google Cloud Run

---

## 📁 Project Structure

```
myapp-backend/
├── alembic/
│   └── env.py
├── app/
│   ├── crud/
│   ├── models/
│   ├── router/
│   ├── services/
│   └── dependencies.py
├── .dockerignore
├── .gitignore
├── Dockerfile
├── main.py
├── requirements.txt
```

---

## 🔑 Prerequisites

* Python 3.11+
* Docker
* PostgreSQL client (`psql`)
* GCP Project with:

  * Cloud SQL instance: `buildingmanagement`
  * Service account with:
    * Secret Manager access
    * Storage Admin role

---

## 🚀 Setup Instructions
### 1. Clone the Repository

```bash
git clone https://github.com/your-username/myapp-backend.git
cd myapp-backend
```

### 2. Create `.env` File

```dotenv
DATABASE_URL=postgresql://admin:your-admin-password@34.55.183.128:5432/user_admin_gcp
CORS_ORIGINS=["your url "]
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_SENDER=
EMAIL_PASSWORD=your-email-app-password
SECRET_KEY=your-secure-32-char-key
```

> Replace placeholders with your actual credentials.

### 3. Install Dependencies

```bash
python -m venv myenv
source myenv/bin/activate  
pip install -r requirements.txt
```

### 4. Run Database Migrations

Check tables using:


```

### 5. Start the App Locally

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Open [http://localhost:8000/docs](http://localhost:8000/docs) for Swagger UI.

---

## 🐳 Run with Docker

```bash
docker build -t myapp-backend .
docker run --env-file .env -p 8080:8080 myapp-backend
```

Access: [http://localhost:8080/docs](http://localhost:8080/docs)

---

## 🔌 API Endpoints

All endpoints require Bearer token from `/auth/login`.

### 🔐 Login

```
POST /auth/login
```

**Body:**

```json
{
  "username": "admin@gmail.com",
  "password": "your-password"
}
```

**Response:**

```json
{
  "access_token": "jwt-token",
  "token_type": "bearer"
}
```

---

### 📤 Upload File

```
POST /user/standalone/upload
```

**Headers:** Authorization: Bearer token
**Body:** `file` (form-data)

---

### 📄 List Files

```
GET /user/list_simple_files/
```

---

### 🗑️ Delete File

```
DELETE /user/delete_simple_file/?file_id={file-id}
```

---

## 🧪 Testing with Postman

1. Set environment: `base_url = http://localhost:8080`
2. Authenticate: `POST {{base_url}}/auth/login`
3. Save `access_token`
4. Use `Bearer token` for all secured routes

---

## ☁️ Deployment to Google Cloud Run

### 1. Create Secrets

```bash
echo "your-db-url" > database-url.txt
gcloud secrets create database-url --data-file=database-url.txt
rm database-url.txt
# Repeat for: google-api-key, jwt-secret-key, etc.
```

### 2. Build & Push Docker Image

```bash
docker build -t gcr.io/sunny-airfoil-467202-f9/myapp-backend:latest .
gcloud auth configure-docker
docker push gcr.io/sunny-airfoil-467202-f9/myapp-backend:latest
```



---



## 📄 License

