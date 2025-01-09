'use client';

import React from 'react';
import { Container, Card, CardContent, Typography, TextField } from '@mui/material';
import TestConversation from '../query/[id]/TestConversation';

export default function TestPage() {
  const [inputValue, setInputValue] = React.useState('');

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Card>
        <CardContent>
          <Typography variant="h5" gutterBottom>
            Test Conversation
          </Typography>
          
          <TestConversation />

          {/* Input field to test state persistence */}
          <TextField
            fullWidth
            label="Type here to test state persistence"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            sx={{ mt: 4 }}
          />
        </CardContent>
      </Card>
    </Container>
  );
}
