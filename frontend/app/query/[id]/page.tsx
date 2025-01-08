'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { 
  Button,
  Card,
  CardContent,
  Typography,
  Skeleton,
  Box,
  Container
} from '@mui/material';

interface QueryResult {
  id: string;
  question: string;
  response: string;
  status: string;
  error: string | null;
  created_at: string;
  completed_at: string;
}

function BackButton() {
  const router = useRouter();
  return (
    <Button 
      variant="contained" 
      color="primary"
      onClick={() => router.push('/query')}
    >
      Ask Another Question
    </Button>
  );
}

function LoadingSkeleton() {
  return (
    <Card>
      <CardContent>
        <Box sx={{ mb: 3 }}>
          <Skeleton variant="rectangular" width={200} height={32} />
        </Box>
        <Box sx={{ mb: 3 }}>
          <Skeleton variant="rectangular" width="100%" height={24} />
          <Skeleton variant="rectangular" width="80%" height={24} sx={{ mt: 1 }} />
        </Box>
        <Box sx={{ mb: 3 }}>
          <Skeleton variant="rectangular" width="100%" height={120} />
        </Box>
      </CardContent>
    </Card>
  );
}

export default function QueryPage({ params }: { params: { id: string } }) {
  const [result, setResult] = useState<QueryResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch(`/api/query/${params.id}`);
        if (!response.ok) throw new Error('Failed to fetch results');
        const data = await response.json();
        setResult(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [params.id]);

  if (loading) {
    return (
      <Container maxWidth="md" sx={{ py: 4 }}>
        <LoadingSkeleton />
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxWidth="md" sx={{ py: 4 }}>
        <Card>
          <CardContent>
            <Typography color="error">{error}</Typography>
            <Box sx={{ mt: 2 }}>
              <BackButton />
            </Box>
          </CardContent>
        </Card>
      </Container>
    );
  }

  if (!result) {
    return null;
  }

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Card>
        <CardContent>
          <Box sx={{ mb: 3 }}>
            <Typography variant="h5" gutterBottom>
              Query Results
            </Typography>
          </Box>
          <Box sx={{ mb: 3 }}>
            <Typography variant="subtitle1" sx={{ mb: 1 }}>
              Question:
            </Typography>
            <Typography variant="body1" color="text.secondary">
              {result.question}
            </Typography>
          </Box>
          <Box sx={{ mb: 3 }}>
            <Typography variant="subtitle1" sx={{ mb: 1 }}>
              Response:
            </Typography>
            <Typography variant="body1" color="text.secondary" sx={{ whiteSpace: 'pre-wrap' }}>
              {result.response}
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
            <BackButton />
          </Box>
        </CardContent>
      </Card>
    </Container>
  );
}