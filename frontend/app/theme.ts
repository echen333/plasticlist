// app/theme.ts
import { createTheme } from '@mui/material/styles';

declare module '@mui/material/Button' {
  interface ButtonPropsVariantOverrides {
    suggested: true;
  }
}

const theme = createTheme({
  palette: {
    primary: {
      main: '#FFD700', // A warm yellow for interactive elements
      light: '#FFE44D',
      dark: '#CCB100',
    },
    secondary: {
      main: '#000000',
    },
    background: {
      default: 'rgb(233, 233, 233)',
      paper: 'rgb(233, 233, 233)',
    },
    text: {
      primary: '#000000',
      secondary: '#333333',
    },
  },
  typography: {
    fontFamily: '"Roboto Mono", "Courier New", monospace',
    h4: {
      fontWeight: 600,
      letterSpacing: '-0.02em',
    },
    h6: {
      fontWeight: 600,
      letterSpacing: '-0.01em',
    },
    body1: {
      lineHeight: 1.7,
      letterSpacing: '0.01em',
    },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        '*::-webkit-scrollbar': {
          width: '8px',
          backgroundColor: 'rgb(233, 233, 233)', // Matches your background color
        },
        '*::-webkit-scrollbar-thumb': {
          backgroundColor: '#888',
          borderRadius: '4px',
        },
        '*::-webkit-scrollbar-track': {
          backgroundColor: 'rgb(233, 233, 233)', // Matches your background color
        },
      },
    },
    MuiButton: {
      variants: [
        {
          props: { variant: 'suggested' as const},
          style: {
            textTransform: 'none',
            borderRadius: 4,
            backgroundColor: '#FFD700',
            color: '#000000',
            border: '1px solid #CCB100',
            '&:hover': {
              backgroundColor: '#BFA100',
            },
          },
        },
      ],
      styleOverrides: {
        root: {
          textTransform: 'none',
          borderRadius: 4,
        },
        outlined: {
          backgroundColor: '#FFD70020',
          '&:hover': {
            backgroundColor: '#FFD70040',
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 4,
          '&:hover': {
            backgroundColor: '#FFD70020',
          },
        },
        outlined: {
          borderColor: '#FFD700',
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiInputBase-input': {
            color: '#000000',
          },
        },
      },
    },
  },
});

export default theme;
