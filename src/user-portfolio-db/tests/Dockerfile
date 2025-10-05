# User-Portfolio-DB Test Database Dockerfile
# Copyright 2024 Google LLC
#
# PostgreSQL database container specifically for testing the user-portfolio-db microservice

FROM postgres:13-alpine

# Set environment variables
ENV POSTGRES_DB=user-portfolio-db
ENV POSTGRES_USER=portfolio-admin
ENV POSTGRES_PASSWORD=portfolio-pwd

# Ensure proper initialization
ENV POSTGRES_INITDB_ARGS="--encoding=UTF8 --locale=C"

# Copy initialization scripts
COPY initdb/ /docker-entrypoint-initdb.d/

# Make sure scripts are executable
RUN chmod +x /docker-entrypoint-initdb.d/*.sql 2>/dev/null || true

# Expose PostgreSQL port
EXPOSE 5432

# Add health check with longer startup period
HEALTHCHECK --interval=15s --timeout=10s --start-period=60s --retries=10 \
    CMD pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB} || exit 1

# Add labels for identification
LABEL purpose="testing"
LABEL component="user-portfolio-db"
LABEL maintainer="user-portfolio-db-test-suite"
