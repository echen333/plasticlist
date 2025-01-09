# PlasticList Search Engine

A sophisticated search engine built to provide intelligent responses about plastics using RAG (Retrieval-Augmented Generation) technology. The system combines modern web technologies with advanced AI capabilities to deliver accurate, context-aware responses.

## Architecture

The project follows a modern microservices architecture with the following components:

### Frontend (Next.js 15)
- Built with Next.js 15 and Material UI for a responsive, modern interface
- Real-time streaming responses using Server-Sent Events (SSE)
- Conversation-based UI with support for follow-up questions
- TypeScript for type safety and better developer experience
- Markdown rendering for formatted AI responses

### Backend (FastAPI)
- FastAPI for high-performance API endpoints
- Streaming response support using FastAPI's StreamingResponse
- CORS middleware for secure frontend-backend communication
- Comprehensive error handling and logging

### Search Engine Core
- RAG (Retrieval-Augmented Generation) implementation
- Pinecone vector database for efficient similarity search
  - Two separate indices:
    - `plasticlist2`: General knowledge index
    - `plasticlist3`: TSV data index with 30 vector retrieval
- Voyage AI 3 Large for generating high-quality embeddings
- Claude 3 Sonnet for response generation
- Supabase for conversation history and state management

## Unique Features

1. **Dual-Index RAG System**
   - Combines general knowledge and specialized TSV data
   - Weighted retrieval from multiple sources
   - Configurable vector counts for different indices

2. **Real-time Response Streaming**
   - Server-Sent Events for immediate feedback
   - Progressive response rendering
   - Optimized for low latency

3. **Conversation Management**
   - Persistent conversation history
   - Context-aware follow-up questions
   - UUID-based conversation tracking

4. **Error Handling & Reliability**
   - Comprehensive error catching and reporting
   - Graceful degradation
   - Detailed logging for debugging

5. **Scalable Architecture**
   - Separate frontend and backend services
   - Environment-based configuration
   - Containerization-ready structure

## Development Process

The project was developed following these key steps:

1. **Initial Setup**
   - Environment configuration with essential API keys
   - Basic Next.js and FastAPI project scaffolding
   - Integration of Material UI components

2. **Core RAG Implementation**
   - Pinecone index creation and management
   - Integration with Voyage AI for embeddings
   - Implementation of vector similarity search

3. **Data Processing**
   - TSV data processing pipeline
   - Text chunking and embedding generation
   - Metadata management for context preservation

4. **Frontend Development**
   - Responsive UI implementation
   - Real-time streaming setup
   - Conversation UI components
   - Error handling and loading states

5. **Backend API Development**
   - Endpoint creation for queries
   - Streaming response implementation
   - Conversation state management
   - Error handling middleware

6. **Integration & Testing**
   - Frontend-backend integration
   - Streaming response testing
   - Conversation flow validation
   - Performance optimization

## Getting Started

### Prerequisites
- Node.js 18+
- Python 3.12+
- Pinecone account
- Voyage AI API key
- Claude API key
- Supabase account

### Environment Setup
1. Clone the repository
2. Copy `.env.example` to `.env` and fill in required credentials
3. Install dependencies:
   ```bash
   # Frontend
   cd frontend
   npm install

   # Backend
   cd ../backend
   pip install -r requirements.txt
   ```

### Running the Application
1. Start the frontend:
   ```bash
   cd frontend
   npm run dev
   ```

2. Start the backend:
   ```bash
   cd backend
   uvicorn api.main:app --reload
   ```

The application will be available at `http://localhost:3000`

## Technical Details

### API Endpoints

- `/api/query/initial`: Start a new conversation
- `/api/query/followup`: Submit follow-up questions
- `/api/query/{query_id}/stream`: Stream responses
- `/api/query/{query_id}`: Get query details

### Data Flow

1. User submits question
2. Backend generates embeddings using Voyage AI
3. Pinecone performs similarity search
4. Context is retrieved from both indices
5. Claude generates response with context
6. Response is streamed to frontend
7. Conversation history is updated in Supabase

### Performance Considerations

- Optimized embedding generation with rate limiting
- Efficient vector search with configurable parameters
- Streaming responses for better user experience
- Caching of conversation history
