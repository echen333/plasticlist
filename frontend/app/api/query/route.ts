// app/api/query/route.ts
import { NextResponse } from 'next/server';

export async function POST(req: Request) {
  try {
    const { question } = await req.json();
    
    // Explicitly call Python backend
    const response = await fetch('http://localhost:8000/api/query', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ question })
    });

    if (!response.ok) {
      throw new Error(`Backend responded with status: ${response.status}`);
    }

    const data = await response.json();
    console.log("Response from Python backend:", data); // Debug log
    
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error in API route:', error);
    return NextResponse.json(
      { error: 'Failed to create query' },
      { status: 500 }
    );
  }
}