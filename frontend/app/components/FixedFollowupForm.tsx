'use client';

import { Box, Button, TextField, Fade, Typography } from '@mui/material';
import React from 'react';

interface FixedFollowupFormProps {
  conversationId: string | null;
  loading: boolean;
  followUpQuestion: string;
  setFollowUpQuestion: (question: string) => void;
  handleFollowUpSubmit: (overrideQuestion?: string) => void;
  suggestedFollowups: string[];
  loadingFollowups: boolean;
  conversation: Array<{ id: string; question: string; response?: string; status?: string; }>;
}

export default function FixedFollowupForm({
  conversationId,
  loading,
  followUpQuestion,
  setFollowUpQuestion,
  handleFollowUpSubmit,
  suggestedFollowups,
  loadingFollowups,
  conversation
}: FixedFollowupFormProps) {
  return (
    <Fade in={!loading} timeout={800}>
      <Box
      sx={{
        position: 'fixed',
        bottom: 24, // Add space from bottom
        left: '50%',
        transform: 'translateX(-50%)', // Center the bar
        bgcolor: 'background.paper',
        boxShadow: 4,
        p: 2,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        width: '100%',
        maxWidth: '900px', // Match Container maxWidth="md"
        borderRadius: '12px', // Add rounded corners
        zIndex: 1000
      }}
    >
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
      <Box sx={{ display: 'flex', gap: 2, width: '100%', justifyContent: 'center' }}>
        <Button
          variant="contained"
          color="primary"
          onClick={() => handleFollowUpSubmit()}
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
    </Box>
    </Fade>
  );
}
