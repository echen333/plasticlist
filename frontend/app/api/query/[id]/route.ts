// app/api/query/[id]/route.ts
import { NextRequest } from 'next/server';

export const runtime = 'edge';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ id: string }> }
) {
  // 1. Await the promised params
  const resolvedParams = await context.params;
  const { id } = resolvedParams;

  console.log('GET route called for query id:', id);
  
  try {
    if (!id) {
      return new Response(
        JSON.stringify({ error: 'No ID provided' }),
        { status: 400 }
      );
    }
    
    // 2. Fetch the conversation from your Python backend
    const response = await fetch(`${API_URL}/api/query/${id}`, {
      method: 'GET',
    });

    if (!response.ok) {
      throw new Error(`Backend returned ${response.status}`);
    }

    const data = await response.json();
    return new Response(JSON.stringify(data), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
    
  } catch (error) {
    console.error('Query fetch error:', error);
    return new Response(
      JSON.stringify({ error: 'Failed to fetch query' }),
      { status: 500 }
    );
  }
}
