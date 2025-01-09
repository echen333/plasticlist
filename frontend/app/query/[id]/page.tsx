'use client';

import { use, useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import CustomCodeBlock from './CustomCodeBlock';
import {
  Button,
  Card,
  CardContent,
  Typography,
  CircularProgress,
  Box,
  Container,
  TextField
} from '@mui/material';

// Data interfaces
interface ConversationQuery {
  id: string;
  question: string;
  response?: string;
  status?: string;
}

interface CurrentQuery extends ConversationQuery {
  conversation_id: string;
}

interface QueryData {
  current_query: CurrentQuery;
  conversation: ConversationQuery[];
}

interface PageParams {
  params: Promise<{ id: string }>;
}

export default function QueryPage({ params }: PageParams) {
  // 1. Resolve the Next.js dynamic route param
  const resolvedParams = use(params);
  const queryId = resolvedParams.id;

  // 2. React state
  const [conversation, setConversation] = useState<ConversationQuery[]>([{
    id: 'test-1',
    question: 'How do I analyze data with Python?',
    response: `Here's an example of data analysis with Python:

\`\`\`python
import pandas as pd
import numpy as np

# Load and analyze data
df = pd.read_csv('data.csv')
summary = df.describe()

# Calculate statistics
mean_value = df['column'].mean()
std_dev = df['column'].std()

print(f"Mean: {mean_value}")
print(f"Standard Deviation: {std_dev}")
\`\`\`

You can modify this code based on your needs.`
  }]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedBlocks, setExpandedBlocks] = useState<{[key: string]: boolean}>({});

  // SSE tracking
  const [isStreaming, setIsStreaming] = useState(false);
  const [activeQueryId, setActiveQueryId] = useState<string | null>(null);

  // Test conversation state initialized above

  // Follow-up question
  const [followUpQuestion, setFollowUpQuestion] = useState('');

  // 3. Scroll ref (we'll scroll to bottom on conversation change)
  const bottomRef = useRef<HTMLDivElement>(null);

  // 4. Fetch conversation data once on mount
  useEffect(() => {
    const fetchConversation = async () => {
      try {
        setLoading(true);
        setError(null);

        const res = await fetch(`/api/query/${queryId}`);
        if (!res.ok) {
          throw new Error(`API returned ${res.status}`);
        }

        const data: QueryData = await res.json();

        // We store the conversation_id so we can post follow-ups
        // setConversationId(data.current_query[0].conversation_id);
        setConversationId(data.current_query.conversation_id);

        // Build an array of all queries
        setConversation(data.conversation);

        // If the current query is still processing, open SSE
        if (data.current_query.status === 'processing') {
          setActiveQueryId(data.current_query.id);
        }
      } catch (error) {
        console.error('Fetch error:', error);
        setError('Failed to fetch conversation');
      } finally {
        setLoading(false);
      }
    };

    fetchConversation();
  }, [queryId]);

  // 5. SSE: whenever activeQueryId is set, stream the response for that query
  useEffect(() => {
    if (!activeQueryId) return;

    let eventSource: EventSource | null = null;
    let mounted = true;

    const startSSE = () => {
      setIsStreaming(true);

      eventSource = new EventSource(`/api/query/${activeQueryId}/stream`);
      eventSource.onmessage = (event) => {
        if (!mounted) return;

        try {
          const data = JSON.parse(event.data);
          
          if (data.content) {
            // Append streamed text to the appropriate query in conversation
            setConversation((prev) =>
              prev.map((item) => {
                if (item.id === activeQueryId) {
                  return {
                    ...item,
                    response: (item.response || '') + data.content
                  };
                }
                return item;
              })
            );
          }

          if (data.error) {
            setError(data.error);
            eventSource?.close();
            setIsStreaming(false);
            setActiveQueryId(null);
          }

          if (data.end) {
            // streaming done
            eventSource?.close();
            setIsStreaming(false);
            setActiveQueryId(null);
            // Optionally, refetch final conversation or patch local state
          }
        } catch (error) {
          console.error('SSE parse error:', error);
          setError('Failed to parse SSE data');
        }
      };

      eventSource.onerror = () => {
        if (!mounted) return;
        setError('Stream connection error');
        eventSource?.close();
        setIsStreaming(false);
        setActiveQueryId(null);
      };
    };

    startSSE();

    return () => {
      mounted = false;
      if (eventSource) {
        eventSource.close();
      }
    };
  }, [activeQueryId]);

  // 6. Scroll to bottom whenever conversation updates
  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [conversation]);

  // 7. Ask a follow-up on the same page
  const handleFollowUpSubmit = async () => {
    if (!followUpQuestion.trim() || !conversationId) return;

  console.log("Current state:", {
    conversationId,
    followUpQuestion,
    typeOfConversationId: typeof conversationId
  });

  const payload = {
    question: followUpQuestion,
    conversation_id: conversationId
  };

  console.log("Stringified payload:", JSON.stringify(payload));

  try {
      setLoading(true);
      setError(null);

      const res = await fetch('/api/query/followup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: followUpQuestion,
          conversation_id: conversationId
        })
      });

      if (!res.ok) {
        throw new Error(`Backend responded with ${res.status}`);
      }

      const data = await res.json();
      const newQueryId = data.id;

      // Insert a placeholder object for the new query
      setConversation((prev) => [
        ...prev,
        {
          id: newQueryId,
          question: followUpQuestion,
          response: '',
          status: 'processing'
        }
      ]);

      // Clear the input
      setFollowUpQuestion('');

      // Start streaming the new query
      setActiveQueryId(newQueryId);
    } catch (error) {
      console.error('Follow-up submission error:', error);
      setError('Failed to submit follow-up question');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Card>
        <CardContent>
          <Typography variant="h5" gutterBottom>
            Conversation
          </Typography>

          {/* Loading + Error */}
          {loading && !conversation.length && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
              <CircularProgress size={20} />
              <Typography color="text.secondary">
                Loading or Processing...
              </Typography>
            </Box>
          )}

          {error && (
            <Box
              sx={{
                bgcolor: 'error.light',
                p: 2,
                borderRadius: 1,
                mb: 2
              }}
            >
              <Typography color="error">Error: {error}</Typography>
            </Box>
          )}

          {/* Render conversation */}
          {conversation.map((q) => (
            <Box
              key={q.id}
              sx={{ mb: 2, p: 1, border: '1px solid #ccc', borderRadius: 1 }}
            >
              <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
                Q: {q.question}
              </Typography>
              <ReactMarkdown
                className="prose max-w-none"
                components={{
                  code: ({ inline, className, children }) => {
                    const blockId = `${q.id}-${Math.random()}`;
                    return (
                      <CustomCodeBlock
                        inline={inline}
                        className={className}
                        isExpanded={expandedBlocks[blockId] || false}
                        onToggle={() => setExpandedBlocks(prev => ({
                          ...prev,
                          [blockId]: !prev[blockId]
                        }))}
                      >
                        {children}
                      </CustomCodeBlock>
                    );
                  }
                }}
              >
                {q.response || ''}
              </ReactMarkdown>
            </Box>
          ))}

          {/* Show streaming indicator */}
          {isStreaming && (
            <Box
              sx={{
                mt: 1,
                display: 'flex',
                alignItems: 'center',
                gap: 1
              }}
            >
              <CircularProgress size={20} />
              <Typography variant="body2" color="text.secondary">
                Receiving response...
              </Typography>
            </Box>
          )}

          {/* Follow-up form */}
          <Box sx={{ mt: 4 }}>
            <TextField
              fullWidth
              label="Ask a follow-up"
              variant="outlined"
              value={followUpQuestion}
              onChange={(e) => setFollowUpQuestion(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  handleFollowUpSubmit();
                }
              }}
              sx={{ mb: 2 }}
            />
            <Button
              variant="contained"
              color="primary"
              onClick={handleFollowUpSubmit}
              disabled={loading || !conversationId}
            >
              Submit Follow-up
            </Button>
          </Box>

          {/* Invisible ref for auto-scrolling */}
          <div ref={bottomRef} />
        </CardContent>
      </Card>
    </Container>
  );
}
