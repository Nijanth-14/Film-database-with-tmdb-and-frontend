#!/bin/bash

# Setup colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Starting Multimedia DBMS Demo ===${NC}"

# Navigate to script directory
cd "$(dirname "$0")"

# 1. Setup Backend
echo -e "\n${GREEN}[1/3] Setting up Python virtual environment...${NC}"
cd backend
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt
cd ..

# 2. Start Frontend Server
echo -e "\n${GREEN}[2/3] Starting Frontend Server on http://localhost:8080...${NC}"
cd frontend/dist
python3 -m http.server 8080 &
FRONTEND_PID=$!
cd ../..

# 3. Start Backend Server
echo -e "\n${GREEN}[3/3] Starting Backend API Server on http://localhost:8000...${NC}"
cd backend
echo "Press Ctrl+C to stop both servers."
uvicorn main:app --host 0.0.0.0 --port 8000

# Cleanup on exit
kill $FRONTEND_PID
deactivate
echo -e "\n${BLUE}Demo stopped.${NC}"
