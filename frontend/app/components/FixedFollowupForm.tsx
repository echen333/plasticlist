'use client';

import { Box, Button, TextField, Fade, Divider, Typography, CircularProgress } from '@mui/material';
import React from 'react';

interface FixedFollowupFormProps {
  conversationId: string | null;
  loading: boolean;
  followUpQuestion: string;
  setFollowUpQuestion: (question: string) => void;
  handleFollowUpSubmit: () => void;
  suggestedFollowups: string[];
  loadingFollowups: boolean;
}

export default function FixedFollowupForm({
  conversationId,
  loading,
  followUpQuestion,
  setFollowUpQuestion,
  handleFollowUpSubmit,
  suggestedFollowups,
  loadingFollowups
}: FixedFollowupFormProps) {
  return (
    <Box
      sx={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        bgcolor: 'background.paper',
        boxShadow: 4,
        p: 2,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        width: '100%',
        maxWidth: '900px', // Match Container maxWidth="md"
        margin: '0 auto',
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
          <Box sx={{ mt: 2, display: 'flex', flexDirection: 'column', gap: 1, width: '100%' }}>
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
                  onClick={() => {
                    setFollowUpQuestion(question);
                    handleFollowUpSubmit();
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
  );
}
