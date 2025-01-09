// app/api/query/initial/route.ts
import { NextResponse } from 'next/server';

export async function POST(req: Request) {
  try {
    const { question } = await req.json();
    
    const response = await fetch('http://localhost:8000/api/query/initial', {
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
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error in initial query route:', error);
    return NextResponse.json(
      { error: 'Failed to create initial query' },
      { status: 500 }
    );
  }
}
