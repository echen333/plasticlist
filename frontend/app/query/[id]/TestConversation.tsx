import React from 'react';
import { Box, Typography } from '@mui/material';
import ReactMarkdown from 'react-markdown';
import CustomCodeBlock from './CustomCodeBlock';

export default function TestConversation() {
  return (
    <Box sx={{ mb: 2, p: 1, border: '1px solid #ccc', borderRadius: 1 }}>
      <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
        Q: How do I analyze data with Python?
      </Typography>
      <ReactMarkdown
        className="prose max-w-none"
        components={{
          code: ({ node, inline, className, children, ...props }) => (
            <CustomCodeBlock inline={inline} className={className}>
              {children}
            </CustomCodeBlock>
          )
        }}
      >
        {`Here's an example of data analysis with Python:

\`\`\`python
import pandas as pd
import numpy as np

# Load and analyze data
df = pd.read_csv('data.csv')
summary = df.describe()

# Calculate statistics
mean_value = df['column'].mean()
std_dev = df['column'].std()

print(f"Mean: {mean_value}")
print(f"Standard Deviation: {std_dev}")
\`\`\`

You can modify this code based on your needs.`}
      </ReactMarkdown>
    </Box>
  );
}
