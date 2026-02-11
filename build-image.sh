#!/usr/bin/env bash
set -e

VERSION=${1:-1.0.0}
IMAGE=gateway-api

echo "Building ${IMAGE}:${VERSION}"
docker build --no-cache -t ${IMAGE}:${VERSION} .

