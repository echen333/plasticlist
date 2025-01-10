// app/api/query/initial/route.ts
import { NextResponse } from 'next/server';

const API_URL = 'https://plasticlist-production.up.railway.app';

export async function POST(req: Request) {
  try {
    const { question } = await req.json();
    
    console.log("New query")
    const response = await fetch(`${API_URL}/api/query/initial`, {
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
