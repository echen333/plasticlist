# PlasticList: Understanding Plastic Chemical Exposure in Food

A comprehensive food safety database and search engine analyzing plastic-related chemicals in everyday foods. Based on testing 775 samples across 312 food products, PlasticList provides an intelligent interface for querying chemical testing data and scientific findings.

## Getting Started

### Prerequisites
- Node.js 18+
- Python 3.12+
- Pinecone account
- Voyage AI API key
- Claude API key
- Supabase account

### Quick Start
1. Clone and set up environment:
   ```bash
   git clone https://github.com/echen333/plasticlist.git
   cd plasticlist
   cp .env.example .env  # Fill in your API keys
   ```

2. Install dependencies:
   ```bash
   # Frontend
   cd frontend && npm install
   # Backend
   cd ../backend && pip install -r requirements.txt
   ```

3. Start the services:
   ```bash
   # Terminal 1: Frontend
   cd frontend && npm run dev
   # Terminal 2: Backend
   cd backend && uvicorn api.main:app --reload
   ```

Visit http://localhost:3000 to start querying the database.

## Architecture

The search interface uses a specialized dual-index architecture:

### Search Engine Core
- Advanced RAG (Retrieval-Augmented Generation) implementation
- Pinecone vector database with two specialized indices:
  - `plasticlist2`: General knowledge and scientific context
  - `plasticlist3`: Detailed TSV data with vectors encoding sample metadata (chemical levels, testing conditions, safety thresholds)
- Voyage AI 3 Large embeddings for accurate chemical and food context matching
- Claude 3 Sonnet for scientifically-accurate response generation

### Frontend & Backend
- Real-time streaming responses via Server-Sent Events (SSE)
- Conversation-based UI supporting contextual follow-up questions
- FastAPI backend with streaming support
- Supabase for conversation history and state management

## Unique Features

1. **Specialized Chemical Testing Database**
   - Comprehensive testing of 18 plastic-related chemicals
   - Raw data from ISO/IEC 17025-accredited laboratory
   - Rigorous QA/QC including isotope dilution mass spectrometry
   - Detailed metadata on testing conditions and methodologies

2. **Dual-Index Scientific RAG**
   - Combines general scientific knowledge with detailed chemical test data
   - Weighted retrieval balancing context and specific measurements
   - Vector-encoded sample metadata for precise chemical information retrieval
   - Configurable vector counts for optimal information density

3. **Real-time Scientific Response Generation**
   - Streaming responses with progressive rendering
   - Context-aware conversation management
   - Chemical-specific answer validation
   - Persistent conversation history for complex scientific queries
