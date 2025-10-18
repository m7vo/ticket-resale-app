# Ticket Resale App

A peer-to-peer marketplace where fans can buy and sell concert tickets securely with no platform fees.

## Features

- User verification with email and seller ratings
- Search listings by artist, date, venue, section, and price
- Direct messaging between buyers and sellers
- User trust scores and review system
- Zero platform fees
- Fraud protection with verified badges and restrictions

## Tech Stack

Backend: FastAPI, PostgreSQL, SQLAlchemy, JWT
Frontend: React, Axios, React Router
Deployment: Docker
Planned: WebSockets for real-time updates

## Setup

### 1. Clone the repo
git clone <your-repo-url>
cd ticket-resale-app

### 2. Backend
python -m venv venv
source venv/bin/activate  # Windows: venv\\Scripts\\activate
cd backend
pip install -r requirements.txt
cp ../.env.example ../.env  # Edit with DB credentials
psql -U postgres -d ticket_app -f database/schema.sql
python app.py
# Runs on http://localhost:8000

### 3. Frontend
cd frontend
npm install
npm start
# Runs on http://localhost:3000

## Project Structure

ticket-resale-app/
├── backend/
│   ├── app.py
│   ├── models/
│   ├── routes/
│   ├── utils/
│   └── database/schema.sql
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   └── services/
└── README.md

## Authentication

- JWT-based login
- Email verification
- Passwords hashed with bcrypt

## API Docs

Run the backend and visit http://localhost:8000/docs.

## Contributing

1. Fork the repo
2. Create a branch (git checkout -b feature/YourFeature)
3. Commit and push
4. Open a pull request

## License

MIT License

