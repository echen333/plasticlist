'use client';

import { use, useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import ReactMarkdown from 'react-markdown';
import {
  Button,
  Card,
  CardContent,
  Typography,
  CircularProgress,
  Box,
  Container,
  TextField,
  Divider,
  Fade
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
  const [conversation, setConversation] = useState<ConversationQuery[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [suggestedFollowups, setSuggestedFollowups] = useState<string[]>([]);
  const [loadingFollowups, setLoadingFollowups] = useState(false);

  // SSE tracking
  const [isStreaming, setIsStreaming] = useState(false);
  const [activeQueryId, setActiveQueryId] = useState<string | null>(null);

  // Follow-up question
  const [followUpQuestion, setFollowUpQuestion] = useState('');

  // Function to generate followup suggestions
  const generateFollowups = async () => {
    if (!conversationId || conversation.length === 0) return;
    
    try {
      setLoadingFollowups(true);
      const res = await fetch('/api/query/generate-followups', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          conversation_id: conversation[conversation.length - 1].id,
          question: conversation[conversation.length - 1].question
        })
      });
      
      if (!res.ok) {
        const errorText = await res.text();
        throw new Error(`Failed to generate followups: ${res.status} - ${errorText}`);
      }
      
      let data;
      try {
        data = await res.json();
        if (!data.followups) {
          throw new Error('Response missing followups data');
        }
      } catch (parseError) {
        throw new Error('Failed to parse server response: ' + parseError.message);
      }

      // Parse followups using regex
      const followups = data.followups.match(/FOLLOWUP\d: (.+)$/gm)
        ?.map(f => f.replace(/FOLLOWUP\d: /, '')) || [];
      
      if (followups.length === 0) {
        console.warn('No followup questions found in response');
      }
      
      setSuggestedFollowups(followups);
    } catch (err) {
      console.error('Failed to generate followups:', err);
      setError(err.message); // Show error in UI
    } finally {
      setLoadingFollowups(false);
    }
  };

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
      } catch (err) {
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
            // Wait a bit before generating new followups to allow fade-out animation
            setTimeout(() => {
              generateFollowups();
            }, 500);
          }
        } catch (err) {
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

  // 6. Scroll to bottom whenever conversation updates or streaming status changes
  useEffect(() => {
    if (bottomRef.current) {
      // Use requestAnimationFrame to ensure DOM has updated
      requestAnimationFrame(() => {
        bottomRef.current?.scrollIntoView({ 
          behavior: 'smooth',
          block: 'end'
        });
      });
    }
  }, [conversation, isStreaming, activeQueryId]);

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
    } catch (err) {
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
              <ReactMarkdown className="prose max-w-none">
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
            <Box sx={{ display: 'flex', gap: 2 }}>
                  <Button
                    variant="contained"
                    color="primary"
                    onClick={handleFollowUpSubmit}
                    disabled={loading || !conversationId}
                  >
                    Submit Follow-up
                  </Button>
                  <Button
                    variant="outlined"
                    color="secondary"
                    onClick={() => window.location.href = '/'}
                  >
                    Ask a new question
                  </Button>
                </Box>

            {/* Suggested followup buttons */}
            {suggestedFollowups.length > 0 && (
              <Fade in={suggestedFollowups.length > 0} timeout={800}>
                <Box sx={{ mt: 2, display: 'flex', flexDirection: 'column', gap: 1 }}>
                  <Divider sx={{ my: 2 }} />
                  <Typography variant="subtitle1">Suggested follow-ups:</Typography>
                  {loadingFollowups ? (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <CircularProgress size={20} />
                    <Typography variant="body2" color="text.secondary">
                      Generating suggestions...
                    </Typography>
                  </Box>
                ) : (
                  suggestedFollowups.map((question, i) => (
                    <Button
                      key={i}
                      variant="outlined"
                      onClick={async () => {
                        try {
                          setLoading(true);
                          setError(null);
                          setSuggestedFollowups([]); // Clear followups immediately

                          const res = await fetch('/api/query/followup', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                              question,
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
                              question,
                              response: '',
                              status: 'processing'
                            }
                          ]);

                          // Start streaming the new query
                          setActiveQueryId(newQueryId);
                        } catch (err) {
                          setError('Failed to submit follow-up question');
                        } finally {
                          setLoading(false);
                        }
                      }}
                      disabled={loading || !conversationId}
                    >
                      {question}
                    </Button>
                  ))
                  )}
                </Box>
              </Fade>
            )}
          </Box>

          {/* Invisible ref for auto-scrolling */}
          <div ref={bottomRef} />
        </CardContent>
      </Card>
    </Container>
  );
}
