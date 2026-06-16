#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
docker build -t api-gateway:smoke-test .
echo "OK: docker build succeeded"
