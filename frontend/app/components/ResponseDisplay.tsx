// app/components/ResponseDisplay.tsx
'use client';

import { Card, CardContent, Typography, CircularProgress, Alert } from '@mui/material';

type ResponseDisplayProps = {
  question?: string;
  answer?: string;
  isLoading?: boolean;
  error?: string;
};

export default function ResponseDisplay({ 
  question,
  answer,
  isLoading, 
  error 
}: ResponseDisplayProps) {
  if (isLoading) {
    return (
      <Card>
        <CardContent>
          <CircularProgress />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Alert severity="error">
        {error}
      </Alert>
    );
  }

  if (!answer) {
    return null;
  }

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Question: {question}
        </Typography>
        <Typography variant="body1" component="div">
          <Typography variant="subtitle1" gutterBottom>
            Answer:
          </Typography>
          {answer}
        </Typography>
      </CardContent>
    </Card>
  );
}