# AURA Deployment & Operations Guide

## 1. Local Development
```bash
# Terminal 1: Backend
pnpm dev:backend

# Terminal 2: Frontend
pnpm dev
```

## 2. Docker Containerization
Backend Dockerfile:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ backend/
EXPOSE 8000
CMD ["python", "backend/run.py"]
```

## 3. AWS Production Architecture
- **Web Layer**: AWS ECS Fargate or Vercel for Next.js 16 frontend.
- **API Layer**: AWS ECS Fargate / App Runner for FastAPI backend.
- **Database**: Neon Serverless PostgreSQL or Amazon Aurora PostgreSQL.
- **Object Storage**: Amazon S3 private bucket with SSE-S3 encryption and signed URLs.
- **Secrets Management**: AWS Secrets Manager.
- **Monitoring**: AWS CloudWatch + Sentry.

## 4. Rollback & Disaster Recovery
- Point-in-time PostgreSQL recovery.
- Version-controlled migrations.
- Audit trail cryptographic integrity verification tool (`GET /api/v1/audit/verify`).
