// app/page.tsx
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { TextField, Button, Container, Typography, Box, Chip, Stack } from '@mui/material';

const sampleQueries = [
  "what are all the entries with tap water as a blind",
  "what were the most interesting things about the study?",
  "what did they find about tap water?",
  "who are the advisors behind the project?",
  "give me the 20 products that arrived at the lab last",
  "how many distinct blinded names are there and what was distribution"
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
          PlasticList
        </Typography>
        <Typography variant="body1" paragraph>
          PlasticList is a scientific project that tested 775 samples of 312 foods for plastic-related chemicals. The project analyzed 18 different chemicals, including phthalates and bisphenols, finding plastic chemicals in 86% of tested foods. Led by a team of researchers and advised by experts from UNC, Columbia, CMU, and Mount Sinai, PlasticList aims to understand the presence of plastic chemicals in everyday foods.
        </Typography>
        <Typography variant="body1" paragraph>
          Ask questions about our findings, methodology, or specific products we tested. For example, you can ask about tap water findings, interesting discoveries, or details about specific food items.
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
          fullWidth
          label="Ask a question about plastics"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          margin="normal"
          disabled={isLoading}
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
