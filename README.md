# Health API

FastAPI application for health data tracking with JWT authentication and Firestore database.

## Prerequisites

### For Local Development
- **Git** - To clone the repository
- **Docker and Docker Compose** - To run the application, Firestore emulator, and tests
  - On macOS/Windows: Install [Docker Desktop](https://www.docker.com/products/docker-desktop)
  - On Linux: Install Docker Engine and Docker Compose
  - **Important**: Make sure Docker Desktop/Docker daemon is running before starting the app

### For Cloud Run Deployment
- **Google Cloud SDK** - Install from [cloud.google.com/sdk](https://cloud.google.com/sdk)
- **GCP Project** - A Google Cloud Platform project with billing enabled
- **Cloud Build API** - Must be enabled in your GCP project

## Setup

### 1. Clone the Repository

```bash
git clone https://github.com/AlejandroPosadaR/light-os.git
cd light-os
```

### 2. Start the Application

**Before running**: Ensure Docker Desktop (macOS/Windows) or Docker daemon (Linux) is running.

```bash
docker-compose up
```

This automatically:
- Builds the app image
- Starts the Firestore emulator
- Starts the app
- Connects them via Docker networking
- Configures all required environment variables (see `docker-compose.yml`)

The API will be available at:
- **API Base**: http://localhost:8080
- **Interactive Docs**: http://localhost:8080/docs

## Deploy to Cloud Run

This service is containerized using Docker and deploys cleanly to Google Cloud Run using ADC (no secrets).

### Prerequisites for Cloud Run

1. **Install Google Cloud SDK** (if not already installed):
   ```bash
   # macOS
   brew install google-cloud-sdk
   
   # Or download from: https://cloud.google.com/sdk/docs/install
   ```

2. **Authenticate with Google Cloud**:
   ```bash
   gcloud auth login
   ```

3. **Set your GCP project**:
   ```bash
   # Replace YOUR_PROJECT_ID with your actual GCP project ID
   # You can find it in the GCP Console or list projects with: gcloud projects list
   gcloud config set project YOUR_PROJECT_ID
   
   # Verify it's set correctly:
   gcloud config get-value project
   ```

4. **Enable required APIs**:
   ```bash
   gcloud services enable cloudbuild.googleapis.com
   gcloud services enable run.googleapis.com
   gcloud services enable firestore.googleapis.com
   gcloud services enable redis.googleapis.com
   gcloud services enable vpcaccess.googleapis.com
   ```

5. **Initialize Firestore** (one-time setup - choose Native mode):
   ```bash
   gcloud firestore databases create --region=australia-southeast1 --type=firestore-native
   ```
   ⚠️ **Important**: If you see "Database already exists", you can skip this step. Firestore is serverless - collections are created automatically on first write.

6. **Create Firestore composite index** (required for health data queries):
   ```bash
   gcloud firestore indexes composite create \
     --collection-group=health_data \
     --query-scope=COLLECTION \
     --field-config field-path=user_id,order=ASCENDING \
     --field-config field-path=timestamp,order=ASCENDING \
     --field-config field-path=__name__,order=ASCENDING
   ```
   ⏱️ **Estimated time**: 1-5 minutes
   
   This index is required for queries that filter by `user_id` and `timestamp` range, then order by `timestamp` and `__name__`.
   
   **Important**: 
   - The collection name `health_data` must match `COLLECTION_NAME` in `app/services/health_service.py`
   - Uses the project from `gcloud config get-value project` (set in step 3)

7. **Set up Application Default Credentials** (for local testing with Cloud Firestore):
   ```bash
   gcloud auth application-default login
   ```

### Deploy to Cloud Run

**Basic deployment** (without Redis):
```bash
gcloud run deploy health-api \
  --source . \
  --region australia-southeast1 \
  --allow-unauthenticated \
  --set-env-vars JWT_SECRET=your-secret-key-change-in-production
```

**Deployment with Memorystore Redis**:
```bash
# 1. Create Memorystore Redis instance
# ⏱️ Estimated time: 5-20 minutes
gcloud redis instances create health-redis \
  --size=1 \
  --region=australia-southeast1 \
  --redis-version=redis_7_0

# 2. Get Redis IP (run in same terminal - needed for step 4)
# Wait for step 1 to complete before running this
REDIS_IP=$(gcloud redis instances describe health-redis \
  --region=australia-southeast1 \
  --format="value(host)")

# 3. Create VPC connector (one-time setup per region)
# ⏱️ Estimated time: 5-15 minutes
# You can check status in another terminal: gcloud compute networks vpc-access connectors list --region=australia-southeast1
gcloud compute networks vpc-access connectors create cr-connector \
  --region=australia-southeast1 \
  --network=default \
  --range=10.8.0.0/28

# 4. Deploy Cloud Run with Redis (uses $REDIS_IP from step 2)
gcloud run deploy health-api \
  --source . \
  --region australia-southeast1 \
  --allow-unauthenticated \
  --vpc-connector=cr-connector \
  --set-env-vars REDIS_HOST=$REDIS_IP,REDIS_PORT=6379,JWT_SECRET=your-secret-key-change-in-production
```

Cloud Run will:
- Build the container from the included Dockerfile
- Deploy the service
- Output a public HTTPS URL

**Note**: In production, make sure to set the `JWT_SECRET` environment variable. For better security, use Google Cloud Secret Manager instead of plain environment variables.

### Redis (Memorystore)

The application supports Redis-based caching.

- **Local development**: Redis via Docker Compose
- **Production**: Redis via GCP Memorystore

Memorystore is a managed Redis service. The application code is identical—only the Redis host is configured via environment variables. Cloud Run connects to Memorystore using a VPC connector.

### Authentication & Security
- No credentials are committed to this repository
- Cloud Run uses **Application Default Credentials**
- Firestore access is granted via IAM (`roles/datastore.user`) on the service account

## Environment Variables

**Local Development**: All environment variables are automatically configured in `docker-compose.yml`. No manual setup needed.

**Production (Cloud Run)**: Set via `--set-env-vars` flag or Cloud Run console.

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `FIRESTORE_EMULATOR_HOST` | Firestore emulator host (e.g., `localhost:8081`) | No | - |
| `GCP_PROJECT_ID` | Google Cloud Project ID | No | Uses ADC default |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account key JSON | No | Uses ADC |
| `JWT_SECRET` | JWT signing secret | Yes (prod) | `your-secret-key-change-in-production` in `app/dependencies.py` |
| `REDIS_HOST` | Redis host | No | - |
| `REDIS_PORT` | Redis port | No | `6379` |

## Testing

Run tests using Docker Compose (recommended):

```bash
# Start services
docker-compose up -d

# Run with coverage report
docker-compose exec app pytest --cov=app --cov-report=html

# Open coverage report (macOS)
open htmlcov/index.html

# Open coverage report (Linux)
xdg-open htmlcov/index.html
```

The Firestore emulator is automatically started by Docker Compose, so all tests will work out of the box.

## API Endpoints

### Authentication
- `POST /auth/register` - Register a new user
- `POST /auth/login` - Login and receive JWT token
- `GET /auth/me` - Get current authenticated user info

### Health Data
- `POST /users/{user_id}/health-data` - Create health data entry
- `GET /users/{user_id}/health-data?start=DD-MM-YYYY&end=DD-MM-YYYY` - Get health data (date range required)
- `GET /users/{user_id}/summary?start=DD-MM-YYYY&end=DD-MM-YYYY` - Get summary statistics

### Example Request

```bash
# Register a user
curl -X POST "http://localhost:8080/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john@example.com",
    "password": "securepassword123"
  }'

# Login
curl -X POST "http://localhost:8080/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "securepassword123"
  }'

# Create health data (use token from login)
curl -X POST "http://localhost:8080/users/{user_id}/health-data" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "2026-01-08T08:30:00Z",
    "steps": 5000,
    "calories": 300,
    "sleepHours": 7.5
  }'
```

### JWT Configuration

JWT signing is configured via an environment variable (`JWT_SECRET`):
- Local development: set it manually in your shell or `.env`
- Cloud Run: provide it via environment variables or Secret Manager in the target project

## Project Structure

```
light-os/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── database.py          # Firestore client configuration
│   ├── dependencies.py      # JWT authentication dependencies
│   ├── models/              # Pydantic models
│   ├── routers/             # API route handlers
│   └── services/            # Business logic layer
├── tests/
│   ├── unit/                # Unit tests
│   └── integration/         # Integration tests
├── requirements.txt         # Python dependencies
└── README.md                # This file
```

## Development

### Key Technologies
- **FastAPI**: Web framework
- **Firestore**: NoSQL database
- **JWT**: Authentication
- **Pydantic**: Data validation
- **pytest**: Testing framework

## Troubleshooting

**Issue: `docker-compose: command not found`**
- Install Docker Desktop (macOS/Windows) or Docker Compose (Linux)
- Verify installation: `docker-compose --version`

**Issue: `Cannot connect to the Docker daemon`**
- Make sure Docker Desktop is running (macOS/Windows)
- On Linux: `sudo systemctl start docker`
- Verify: `docker ps`

**Issue: `gcloud: command not found`**
- Install Google Cloud SDK (only needed for Cloud Run deployment)
- See [Cloud Run deployment prerequisites](#prerequisites-for-cloud-run) above
- Or use Docker Compose for local development (recommended)

**Issue: `Your default credentials were not found`**
- For local development: Set `FIRESTORE_EMULATOR_HOST=localhost:8081` (handled automatically by docker-compose)
- For Cloud Run: Run `gcloud auth application-default login` or deploy to Cloud Run (uses ADC automatically)

**Issue: Tests failing**
- Make sure services are running: `docker-compose up -d`
- The Firestore emulator is automatically configured by Docker Compose (no manual environment variables needed)
- Unit tests don't require database

**Issue: Port already in use**
- If port 8080 is in use, modify `docker-compose.yml` to use a different port
- Or stop the conflicting service: `lsof -ti:8080 | xargs kill` (macOS/Linux)

## License

MIT License

Copyright (c) 2026 Alejandro Posada

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.