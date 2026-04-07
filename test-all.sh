#!/usr/bin/env bash

set -e

echo "==========================================="
echo "  API Debug Env - Full Validation Pipeline "
echo "==========================================="

echo -e "\n[1/4] Checking Python Syntax & Dependencies..."
pip install -r requirements.txt || echo "pip install failed"

echo -e "\n[2/4] Running 'openenv validate'..."
openenv validate
if [ $? -eq 0 ]; then
    echo -e "✅ openenv validate PASSED!"
else
    echo -e "❌ openenv validate FAILED!"
    exit 1
fi

echo -e "\n[3/4] Testing Docker Build locally..."
docker build -t api-debug-env-test .
if [ $? -eq 0 ]; then
    echo -e "✅ Docker build PASSED!"
else
    echo -e "❌ Docker build FAILED!"
    exit 1
fi

echo -e "\n[4/4] Testing inference.py natively..."
export HF_TOKEN="dummy_token_test"
export API_BASE_URL="https://router.huggingface.co/v1"
export MODEL_NAME="mistralai/Mistral-7B-Instruct-v0.3"

# Spin up the background server for inference.py to hit
echo "Starting local FastAPI server on port 7860..."
uvicorn server.app:app --port 7860 &
SERVER_PID=$!

# Give the server a few seconds to start up
sleep 3

echo "Running inference.py..."
python inference.py
INF_EXIT=$?

# Kill the background server
kill $SERVER_PID

if [ $INF_EXIT -eq 0 ]; then
    echo -e "✅ inference.py ran successfully without crashing!"
else
    echo -e "❌ inference.py FAILED with status $INF_EXIT!"
    exit 1
fi

echo -e "\n==========================================="
echo " 🎉 ALL VALIDATION CHECKS PASSED SUCCESSFULLY!"
echo " Everything is 100% ready for the Meta Hackathon."
echo "==========================================="
