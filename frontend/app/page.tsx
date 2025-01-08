// app/page.tsx
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { TextField, Button, Container } from '@mui/material';

export default function HomePage() {
  const [question, setQuestion] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;
    
    setIsLoading(true);
    try {
      const res = await fetch('/api/query', {
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
        router.push(`/api/query/${data.id}`);
      }
    } catch (err) {
      console.error('Error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Container maxWidth="md" sx={{ mt: 4 }}>
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