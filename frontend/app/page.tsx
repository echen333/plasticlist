// app/page.tsx
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { TextField, Button, Container, Typography, Box, Chip, Stack, Link } from '@mui/material';

const sampleQueries = [
  "What are all the entries with tap water as a blind?",
  "What were the most interesting things about the study?",
  "What did they find about tap water?",
  "Who are the advisors behind the project?",
  "Give me the 20 products that arrived at the lab last.",
  "What percentage of entries measured as '<LOQ'?",
  "How many distinct blinded names are there and which names come up with the most frequency?"
];

export default function HomePage() {
  const [question, setQuestion] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  const handleSampleQuery = (sample: string) => {
    setQuestion(sample);
    handleSubmitDirect(sample);
  };

  const handleSubmitDirect = async (sample: string) => {
    setIsLoading(true);
    try {
      const res = await fetch('/api/query/initial', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: sample })
      });

      const data = await res.json();

      if (data.error) {
        throw new Error(data.error);
      }

      if (data.id) {
        router.push(`/query/${data.id}`);
      }
    } catch (err) {
      console.error('Error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;

    setIsLoading(true);
    try {
      const res = await fetch('/api/query/initial', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question })
      });

      const data = await res.json();

      if (data.error) {
        throw new Error(data.error);
      }

      // Only redirect if we get a valid ID back
      if (data.id) {
        router.push(`/query/${data.id}`);
      }
    } catch (err) {
      console.error('Error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Container maxWidth="md" sx={{ mt: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom>
          PlasticList Search
        </Typography>
        <Typography variant="body1" paragraph>
          PlasticList Search is a demo search interface for the{' '}
          <Link
            href="https://www.plasticlist.org/"
            target="_blank"
            rel="noopener noreferrer"
            sx={{ fontWeight: 'bold' }}
          >
            PlasticList
          </Link>{' '}
          project, a research initiative that tested over 100 everyday foods from the Bay Area for the presence of plastic chemicals. The study, conducted by a team of independent researchers, quantified the levels of endocrine-disrupting chemicals (EDCs) and other plastic-related substances in common food items. The accompanying TSV dataset contains extensive data on chemical levels, testing conditions, and safety thresholds.
        </Typography>

        <Typography variant="body1" paragraph>
          Ask questions about the findings, methodology, or specific products tested. You can find more details about the website <Link
            href="https://github.com/echen333/plasticlist"
            target="_blank"
            rel="noopener noreferrer"
            sx={{ fontWeight: 'bold' }}
          >here</Link>.
        </Typography>
        
      </Box>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h6" gutterBottom>
          Sample Questions
        </Typography>
        <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', gap: 1 }}>
          {sampleQueries.map((query) => (
            <Chip
              key={query}
              label={query}
              onClick={() => handleSampleQuery(query)}
              variant="outlined"
              sx={{ mb: 1 }}
              disabled={isLoading}
            />
          ))}
        </Stack>
      </Box>
      <form onSubmit={handleSubmit}>
        <TextField
          id="question-input"
          key="question-input"
          fullWidth
          label="Ask a question about plastics"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          margin="normal"
          disabled={isLoading}
          variant="outlined"
        />
        <Button
          variant="contained"
          type="submit"
          disabled={isLoading}
        >
          {isLoading ? 'Submitting...' : 'Submit Question'}
        </Button>
      </form>
    </Container>
  );
}
