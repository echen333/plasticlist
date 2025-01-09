'use client';

import { useEffect, useState, use } from 'react';
import { useRouter } from 'next/navigation';
import ReactMarkdown from 'react-markdown';
import { 
  Button,
  Card,
  CardContent,
  Typography,
  CircularProgress,
  Box,
  Container
} from '@mui/material';

interface PageParams {
  params: Promise<{ id: string }>;
}

function BackButton() {
  const router = useRouter();
  return (
    <Button 
      variant="contained" 
      color="primary"
      onClick={() => router.push('/')}
    >
      Ask Another Question
    </Button>
  );
}

export default function QueryPage({ params }: PageParams) {
  const resolvedParams = use(params);
  const queryId = resolvedParams.id;
  
  const [streamedResponse, setStreamedResponse] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);

  useEffect(() => {
    let eventSource: EventSource | null = null;
    let mounted = true;

    const startStreaming = async () => {
      try {
        if (eventSource) {
          eventSource.close();
        }
        
        eventSource = new EventSource(`/api/query/${queryId}/stream`);
        
        eventSource.onopen = () => {
          setIsStreaming(true);
          setLoading(false);
        };

        eventSource.onmessage = (event) => {
          if (!mounted) return;
          
          try {
            const data = JSON.parse(event.data);
            
            if (data.content) {
              setStreamedResponse(prev => prev + data.content);
            }
            
            if (data.error) {
              setError(data.error);
              eventSource?.close();
              setIsStreaming(false);
            }
            
            if (data.end) {
              eventSource?.close();
              setIsStreaming(false);
            }
          } catch (error) {
            setError('Failed to parse stream data');
          }
        };

        eventSource.onerror = () => {
          if (!mounted) return;
          setError('Stream connection error');
          eventSource?.close();
          setIsStreaming(false);
        };

      } catch (error) {
        if (!mounted) return;
        setError('Failed to set up streaming connection');
      }
    };

    startStreaming();

    return () => {
      mounted = false;
      if (eventSource) {
        eventSource.close();
      }
    };
  }, [queryId]);

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Card>
        <CardContent>
          <Typography variant="h5" gutterBottom>
            Query Results
          </Typography>
          
          {loading && !streamedResponse && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
              <CircularProgress size={20} />
              <Typography color="text.secondary">
                Processing your query...
              </Typography>
            </Box>
          )}

          {error && (
            <Box sx={{ 
              bgcolor: 'error.light', 
              p: 2, 
              borderRadius: 1,
              mb: 2
            }}>
              <Typography color="error">Error: {error}</Typography>
            </Box>
          )}

          <Box sx={{ position: 'relative' }}>
            {(streamedResponse || isStreaming) && (
              <Box sx={{ mb: 2 }}>
                <ReactMarkdown className="prose max-w-none">
                  {streamedResponse || ''}
                </ReactMarkdown>
              </Box>
            )}

            {isStreaming && (
              <Box sx={{ 
                mt: 1, 
                display: 'flex', 
                alignItems: 'center',
                gap: 1
              }}>
                <Box sx={{
                  width: 8,
                  height: 8,
                  bgcolor: 'primary.main',
                  borderRadius: '50%',
                  animation: 'pulse 1.5s infinite'
                }} />
                <Typography variant="body2" color="text.secondary">
                  Receiving response...
                </Typography>
              </Box>
            )}
          </Box>

          <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 2 }}>
            <BackButton />
          </Box>
        </CardContent>
      </Card>
    </Container>
  );
}