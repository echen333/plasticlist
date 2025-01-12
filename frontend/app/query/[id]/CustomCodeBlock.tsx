import React, { useMemo } from 'react';
import { Accordion, AccordionSummary, AccordionDetails } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';

export interface CustomCodeBlockProps {
  children: React.ReactNode;
  className?: string;
  inline?: boolean;
  isExpanded: boolean;
  onToggle: () => void;
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

function CustomCodeBlock({ children, className, inline, isExpanded, onToggle }: CustomCodeBlockProps) {
  const codeText = useMemo(() => String(children).trim(), [children]);
  const isPython = useMemo(() => isPythonCode(className, codeText), [className, codeText]);
  
  const inlineCode = useMemo(() => (
    <code className={className}>{children}</code>
  ), [className, children]);
  
  const standardCode = useMemo(() => (
    <pre className={className}>
      <code>{codeText}</code>
    </pre>
  ), [className, codeText]);

  // Return appropriate rendering based on conditions
  if (inline) {
    return inlineCode;
  }

  if (!isPython) {
    return standardCode;
  }

  // For Python, wrap in MUI Accordion
  return (
    <Accordion 
      expanded={isExpanded}
      onChange={onToggle}
      sx={{
        width: '100%',
        minHeight: 48,
        marginY: 2,
        backgroundColor: 'background.paper',
        border: '1px solid',
        borderColor: 'divider',
        borderRadius: 1,
        boxShadow: 'none',
        transition: 'none',
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

export default React.memo(CustomCodeBlock, (prevProps, nextProps) => {
  // Only re-render if the content or className actually changed
  return (
    prevProps.children === nextProps.children &&
    prevProps.className === nextProps.className &&
    prevProps.inline === nextProps.inline
  );
});
