import React from 'react';
import { Accordion, AccordionSummary, AccordionDetails } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';

interface CustomCodeBlockProps {
  children: React.ReactNode;
  className?: string;
  inline?: boolean;
}

const isPythonCode = (className?: string, content?: string): boolean => {
  // Check if explicitly marked as Python
  if (className?.includes('python')) {
    return true;
  }

  // If not explicitly marked, check content for Python-like patterns
  const contentStr = String(content);
  const pythonPatterns = [
    /^import\s+\w+/m,           // import statements
    /^from\s+\w+\s+import/m,    // from ... import statements
    /^def\s+\w+\s*\(/m,         // function definitions
    /^class\s+\w+/m,            // class definitions
    /^\s*#.*$/m,                // Python comments
    /print\s*\(/,               // print statements
    /pandas|numpy|sklearn/       // common Python libraries
  ];

  return pythonPatterns.some(pattern => pattern.test(contentStr));
};

export default function CustomCodeBlock({ children, className, inline }: CustomCodeBlockProps) {
  // Don't wrap inline code
  if (inline) {
    return <code className={className}>{children}</code>;
  }

  const codeText = String(children).trim();
  const isPython = isPythonCode(className, codeText);

  // Return standard rendering for non-Python code
  if (!isPython) {
    return (
      <pre className={className}>
        <code>{codeText}</code>
      </pre>
    );
  }

  // For Python, wrap in MUI Accordion (auto-collapsed)
  return (
    <Accordion 
      defaultExpanded={false} 
      sx={{
        marginY: 2,
        backgroundColor: 'background.paper',
        border: '1px solid',
        borderColor: 'divider',
        borderRadius: 1,
        boxShadow: 'none',
        '&:before': {
          display: 'none',
        },
        '& .MuiAccordionSummary-root': {
          minHeight: 48,
          borderBottom: '1px solid',
          borderBottomColor: 'divider',
          backgroundColor: 'action.hover',
          '&:hover': {
            backgroundColor: 'action.selected',
          },
        },
        '& .MuiAccordionDetails-root': {
          padding: 2,
          backgroundColor: 'background.default',
        },
        '& pre': {
          margin: 0,
          padding: 2,
          overflow: 'auto',
          backgroundColor: 'background.paper',
          borderRadius: 1,
          fontFamily: 'monospace',
          fontSize: '0.875rem',
          lineHeight: 1.5,
        },
        '& code': {
          color: 'text.primary',
        },
      }}
    >
      <AccordionSummary 
        expandIcon={<ExpandMoreIcon />}
        aria-label="Expand Python code"
      >
        Python Code
      </AccordionSummary>
      <AccordionDetails>
        <pre className={className}>
          <code>{codeText}</code>
        </pre>
      </AccordionDetails>
    </Accordion>
  );
}