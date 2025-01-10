'use client';

import { use, useEffect, useRef, useState } from 'react';

import FixedFollowupForm from '../../components/FixedFollowupForm';
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

interface MarkdownCodeComponentProps extends React.HTMLProps<HTMLElement> {
  inline?: boolean;
  className?: string;
}

export default function QueryPage({ params }: PageParams) {
  // 1. Resolve the Next.js dynamic route param
  const resolvedParams = use(params);
  const queryId = resolvedParams.id;

  // 2. React state
  const [conversation, setConversation] = useState<ConversationQuery[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedBlocks, setExpandedBlocks] = useState<{ [key: string]: boolean }>({});
  const [suggestedFollowups, setSuggestedFollowups] = useState<string[]>([]);
  const [loadingFollowups, setLoadingFollowups] = useState(false);

  // SSE tracking
  const [isStreaming, setIsStreaming] = useState(false);
  const [activeQueryId, setActiveQueryId] = useState<string | null>(null);

  // Test conversation state initialized above

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
      } catch (error) {
        const parseError = error instanceof Error ? error : new Error('Unknown JSON parse error');
        throw new Error('Failed to parse server response: ' + parseError.message);
      }

      // Parse followups using regex
      const followups = data.followups.match(/FOLLOWUP\d: (.+)$/gm)
        ?.map((f: string) => f.replace(/FOLLOWUP\d: /, '')) || [];
      if (followups.length === 0) {
        console.warn('No followup questions found in response');
      }

      if (followups.length === 0) {
        console.warn('No followup questions found in response');
      }

      setSuggestedFollowups(followups);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'An error occurred');
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
      } catch (error) {
        console.error('Fetch error:', error);
        setError('Failed to fetch conversation');
      } finally {
        setLoading(false);
      }
    };

    fetchConversation();
  }, [queryId]);

  useEffect(() => {
    if (conversation.length > 0 && bottomRef.current && !loading) {
      bottomRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'end'
      });
    }
  }, [conversation.length, loading]);

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
            console.log("Error from server:", data.error)
            if (data.error) {
              // Append streamed text to the appropriate query in conversation
              setConversation((prev) =>
                prev.map((item) => {
                  if (item.id === activeQueryId) {
                    return {
                      ...item,
                      response: (item.response || '') + " Error executing query with error: " + data.error
                    };
                  }
                  return item;
                })
              );
            }
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

  useEffect(() => {
    if (bottomRef.current) {
      // Get the viewport height
      const viewportHeight = window.innerHeight;
      // Get the bottom ref's position
      const bottomPosition = bottomRef.current.getBoundingClientRect().bottom;
      // Check if we're already near bottom
      const isNearBottom = bottomPosition <= viewportHeight + 130; // 100px threshold

      // Only scroll if we're streaming or near bottom
      if (isStreaming || isNearBottom) {
        requestAnimationFrame(() => {
          bottomRef.current?.scrollIntoView({
            behavior: 'smooth',
            block: 'end'
          });
        });
      }
    }
  }, [conversation, isStreaming, activeQueryId, suggestedFollowups, loadingFollowups]);

  // 7. Ask a follow-up on the same page
  const handleFollowUpSubmit = async (overrideQuestion?: string) => {
    const finalQuestion = overrideQuestion || followUpQuestion;
    if (!finalQuestion.trim() || !conversationId) return;

    const payload = {
      question: finalQuestion,
      conversation_id: conversationId
    };

    console.log("Stringified payload:", JSON.stringify(payload));

    try {
      setLoading(true);
      setError(null);
      setSuggestedFollowups([])

      const res = await fetch('/api/query/followup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: finalQuestion,
          conversation_id: conversationId
        })
      });

      if (!res.ok) {
        const errorText = await res.text();
        console.error('Backend error:', {
          status: res.status,
          statusText: res.statusText,
          body: errorText
        });
        throw new Error(`Backend responded with ${res.status}: ${errorText}`);
      }

      const data = await res.json();
      const newQueryId = data.id;

      // Insert a placeholder object for the new query
      setConversation((prev) => [
        ...prev,
        {
          id: newQueryId,
          question: finalQuestion,
          response: '',
          status: 'processing'
        }
      ]);

      // Clear the input
      setFollowUpQuestion('');

      // Start streaming the new query
      setActiveQueryId(newQueryId);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(`Failed to submit follow-up question: ${errorMessage}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>

      <Container
        maxWidth="md"
        sx={{
          py: 4,
          height: 'calc(100vh - 200px)', // viewport height minus fixed form height
          overflowY: 'auto',
          position: 'relative',
          zIndex: 1
        }}
      >

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
                    code: ({ inline, className, children }: MarkdownCodeComponentProps) => {
                      const blockId = `code-block-${q.id}`;
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
                >{q.response || ''}
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
          </CardContent>
        </Card>

        {/* Suggested followup buttons in separate card */}
        {suggestedFollowups.length > 0 && (
          <Card sx={{ mt: 2 }}>
            <CardContent>
              <Fade in={suggestedFollowups.length > 0} timeout={2000}>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
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
                        variant="contained"
                        color="primary"
                        onClick={() => handleFollowUpSubmit(question)}

                        disabled={loading || !conversationId}
                      >
                        {question}
                      </Button>
                    ))
                  )}
                </Box>
              </Fade>
            </CardContent>
          </Card>
        )}
        <div ref={bottomRef} style={{ height: 1, width: '100%' }} />
      </Container>
      <Box
        sx={{
          position: 'fixed',
          bottom: 0,
          left: 0,
          right: 0,
          bgcolor: 'background.default',
          borderTop: '1px solid',
          borderColor: 'divider',
          zIndex: 2, // Higher than the content
          boxShadow: '0px -2px 8px rgba(0,0,0,0.1)' // Optional shadow for visual separation
        }}
      >
        <Container maxWidth="md">
          <FixedFollowupForm
            conversationId={conversationId}
            loading={loading}
            followUpQuestion={followUpQuestion}
            setFollowUpQuestion={setFollowUpQuestion}
            handleFollowUpSubmit={handleFollowUpSubmit}
            suggestedFollowups={suggestedFollowups}
            loadingFollowups={loadingFollowups}
            conversation={conversation}
          />
        </Container>
      </Box>

    </>
  );
}
