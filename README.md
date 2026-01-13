# Health API

FastAPI application for health data tracking with JWT authentication and Firestore database.

## Prerequisites

- Docker and Docker Compose
- Google Cloud SDK (only needed for Cloud Run deployment)

## Setup

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd fastprac
```

### 2. Database Setup

Choose one of the following options:

#### Option A: Firestore Emulator (For local testing)

**Using Docker Compose:**
```bash
# Start both the app and emulator with one command
docker-compose up
```

This starts:
- Firestore emulator on port 8081
- FastAPI app on port 8080
- Automatically connects them via Docker networking

#### Option B: Real Firestore (Cloud Run)

This application uses **Application Default Credentials (ADC)** when deployed to Cloud Run.

- No service account keys or secrets are required.
- Authentication to Firestore is handled via the **Cloud Run runtime service account**, with access controlled using IAM roles (`roles/datastore.user` is typical).

## Cloud Run Deployment

This service is containerized using Docker and deploys cleanly to Google Cloud Run using ADC (no secrets).

Deploy to Cloud Run (builds from source using the included Dockerfile):

```bash
gcloud run deploy health-api \
  --source . \
  --region australia-southeast1 \
  --allow-unauthenticated
```

Cloud Run will:
- Build the container from the included Dockerfile
- Deploy the service
- Output a public HTTPS URL

Authentication & Security:
- No credentials are committed to this repository
- Cloud Run uses **Application Default Credentials**
- Firestore access is granted via IAM (`roles/datastore.user`) on the service account

## Run Locally with Docker

### Option 1: Docker Compose (Simplest)

```bash
# Start everything with one command
docker-compose up
```

This automatically:
- Builds the app image
- Starts the Firestore emulator
- Starts the app
- Connects them via Docker networking

### Option 2: Manual Docker Setup

**Prerequisites:** Start the Firestore emulator first (see "Database Setup" above).

```bash
# Build the Docker image
docker build -t health-api .

# Run the container (connect to Firestore emulator on same Docker network)
docker run -p 8080:8080 \
  --network health-api-network \
  -e FIRESTORE_EMULATOR_HOST=firestore-emulator:8080 \
  -e GCP_PROJECT_ID=test-project \
  -e JWT_SECRET=your-secret-key-change-in-production \
  health-api
```

The API will be available at:
- **API Base**: http://localhost:8080
- **Interactive Docs**: http://localhost:8080/docs
- **Alternative Docs**: http://localhost:8080/redoc

## Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `FIRESTORE_EMULATOR_HOST` | Firestore emulator host (e.g., `localhost:8081`) | No | - |
| `GCP_PROJECT_ID` | Google Cloud Project ID | No | Uses ADC default |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account key JSON | No | Uses ADC |
| `JWT_SECRET` | JWT signing secret | Yes (prod) | `your-secret-key-change-in-production` in `app/dependencies.py` |

## Testing

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=app --cov-report=html
open htmlcov/index.html  # View coverage report

# Run only unit tests (no database needed)
pytest tests/unit/

# Run only integration tests (requires emulator)
export FIRESTORE_EMULATOR_HOST=localhost:8081
pytest tests/integration/
```

## API Endpoints

### Authentication
- `POST /auth/register` - Register a new user
- `POST /auth/login` - Login and receive JWT token
- `GET /auth/me` - Get current authenticated user info

### Health Data
- `POST /users/{user_id}/health-data` - Create health data entry
- `GET /users/{user_id}/health-data?start=DD-MM-YYYY&end=DD-MM-YYYY` - Get health data (date range required)
- `GET /users/{user_id}/health-data/summary?start_date=DD-MM-YYYY&end_date=DD-MM-YYYY` - Get summary statistics

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
fastprac/
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
└── README.md               # This file
```

## Development

### Code Style
- Follow PEP 8
- Type hints are used throughout
- Docstrings for complex functions

### Key Technologies
- **FastAPI**: Web framework
- **Firestore**: NoSQL database
- **JWT**: Authentication
- **Pydantic**: Data validation
- **pytest**: Testing framework

## Troubleshooting

**Issue: `gcloud: command not found`**
- Install Google Cloud SDK (see Option A above)
- Or use Docker for the emulator (recommended)
- Or deploy to Cloud Run using ADC (Option B)

**Issue: Firestore emulator Java compatibility error (`NoClassDefFoundError: LegacySystemExit`)**
- This occurs when using Java 21+ with older emulator versions
- **Solution:** Use Docker for the emulator (see Option A - Docker method above)
- Or install Java 17: `brew install openjdk@17` (requires Xcode)

**Issue: `Your default credentials were not found`**
- Set `FIRESTORE_EMULATOR_HOST` for local development
- Or run `gcloud auth application-default login` (local ADC) or deploy to Cloud Run (uses ADC)

**Issue: Tests failing**
- Make sure Firestore emulator is running for integration tests
- Unit tests don't require database

## License

[Your License Here]
