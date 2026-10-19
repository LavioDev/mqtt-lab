FROM node:22-alpine AS frontend-build
WORKDIR /frontend
COPY dashboard/frontend/package.json dashboard/frontend/package-lock.json ./
RUN npm ci
COPY dashboard/frontend/ ./
RUN npm run build

FROM python:3.13-slim-trixie
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY dashboard/backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --system --uid 10001 --create-home dashboard
COPY dashboard/backend/app.py ./app.py
COPY --from=frontend-build /frontend/dist ./static
USER 10001:10001
EXPOSE 8080
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
