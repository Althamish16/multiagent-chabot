# Multiagent Chatbot

A proof-of-concept (POC) multiagent chatbot system built with FastAPI backend and React frontend. The system orchestrates multiple specialized AI agents for handling different types of tasks including email management, calendar operations, file summarization, and note-taking.

## Architecture

### Backend
- **Framework**: FastAPI
- **Database**: MongoDB
- **AI Integration**: Emergent Integrations LLM with OpenAI GPT-5
- **Agents**: Email Agent, Calendar Agent, File Summarizer Agent, Notes Agent

### Frontend
- **Framework**: React 19
- **Styling**: Tailwind CSS
- **UI Components**: Radix UI
- **Routing**: React Router DOM

## Features

- **Intelligent Agent Orchestration**: Automatically routes user requests to the appropriate specialized agent
- **Real-time Chat Interface**: Modern, responsive chat UI with message history
- **Multi-agent Support**: Dedicated agents for email, calendar, file processing, and note management
- **Session Management**: Persistent chat sessions with message history
- **CORS Enabled**: Full cross-origin support for frontend-backend communication

## Prerequisites

- Python 3.11+
- Node.js 16+
- MongoDB instance
- OpenAI API access via Emergent Integrations
- Git

## Setup Instructions

### 1. Clone the Repository
```bash
git clone <repository-url>
cd multiagent-chatbot
```

### 2. Backend Setup

#### Install Python Dependencies
```bash
cd backend
pip install -r requirements.txt
```

#### Environment Configuration
Create a `.env` file in the `backend/` directory with the following variables:
```env
MONGO_URL=mongodb://localhost:27017
DB_NAME=ai_agents_poc
EMERGENT_LLM_KEY=your_emergent_llm_api_key
```

#### Start the Backend Server
```bash
python server.py
```
The backend will start on `http://localhost:8000`

### 3. Frontend Setup

#### Install Node Dependencies
```bash
cd ../frontend
npm install
```

#### Start the Development Server
```bash
npm start
```
The frontend will start on `http://localhost:3000`

## API Endpoints

### Chat Management
- `POST /api/chat` - Send a chat message
- `GET /api/chat/{session_id}` - Get chat history for a session
- `DELETE /api/chat/{session_id}` - Delete a chat session

### Agent Operations
- `POST /api/agents/email` - Email agent operations
- `POST /api/agents/calendar` - Calendar agent operations
- `POST /api/agents/files` - File summarizer operations
- `POST /api/agents/notes` - Notes agent operations

## Project Structure

```
multiagent-chatbot/
├── backend/
│   ├── server.py          # Main FastAPI application
│   ├── requirements.txt   # Python dependencies
│   └── .env              # Environment variables (create this)
├── frontend/
│   ├── src/
│   │   ├── App.js        # Main React application
│   │   ├── components/   # Reusable UI components
│   │   └── hooks/        # Custom React hooks
│   ├── package.json      # Node dependencies
│   └── public/           # Static assets
├── tests/                # Test files
├── test_reports/         # Test execution reports
└── README.md            # This file
```

## Development

### Running Tests
```bash
# Backend tests
cd backend
python -m pytest

# Frontend tests
cd frontend
npm test
```

### Building for Production
```bash
# Backend
cd backend
# Use your preferred deployment method (Docker, cloud service, etc.)

# Frontend
cd frontend
npm run build
## Next Implementation

### Authentication & Security
- **SSO Login with Azure Active Directory (AAD)**: Implement single sign-on authentication with Microsoft Azure AD, with main login handling through the backend

### Multi-Agent Collaboration Enhancement
- **LangGraph Integration**: Integrate LangGraph framework to enable sophisticated multi-agent collaboration and orchestration
- **Enhanced Agent Coordination**: Currently agents work independently; LangGraph will enable seamless collaboration between agents on complex, multi-step tasks requiring coordinated workflows

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built with FastAPI and React
- AI capabilities powered by Emergent Integrations
- UI components from Radix UI
- Styling with Tailwind CSS