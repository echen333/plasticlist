# PlasticList: Understanding Plastic Chemical Exposure in Food

A comprehensive food safety database and search engine analyzing plastic-related chemicals in everyday foods. Based on testing 775 samples across 312 food products, PlasticList found that 86% contained detectable levels of plastic chemicals, with some exceeding European safety limits by up to 32,000%.

## Key Findings

- Detected plastic chemicals in all tested baby foods, prenatal supplements, breast milk, yogurt, and ice cream products
- Found that less-processed foods contain fewer chemicals than highly processed ones
- Discovered hot foods in takeout containers had 34% higher levels after 45 minutes
- Identified phthalates in 73% of products, phthalate substitutes in 73%, and bisphenols in 22%
- Used rigorous testing methodology including GC/MS and isotope dilution mass spectrometry

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
