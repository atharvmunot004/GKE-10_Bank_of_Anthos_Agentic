# Assets-DB Test Database Dockerfile
# Copyright 2024 Google LLC
#
# PostgreSQL database container specifically for testing the assets-db microservice

FROM postgres:13-alpine

# Set environment variables
ENV POSTGRES_DB=assets-db
ENV POSTGRES_USER=assets-admin
ENV POSTGRES_PASSWORD=assets-pwd

# Copy initialization scripts
COPY initdb/ /docker-entrypoint-initdb.d/

# Expose PostgreSQL port
EXPOSE 5432

# Add health check
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=5 \
    CMD pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB} || exit 1

# Add labels for identification
LABEL purpose="testing"
LABEL component="assets-db"
LABEL maintainer="assets-db-test-suite"
