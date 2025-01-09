// app/api/query/[id]/stream/route.ts
import { NextRequest } from 'next/server';

export const runtime = 'edge';

export async function GET(
  request: NextRequest,
  context: { params: { id: string } }
) {
  const { params } = context;
  const { id } = await params;
  
  console.log('Stream route called for id:', id);
  
  try {
    const response = await fetch(`http://localhost:8000/api/query/${id}/stream`, {
      method: 'GET',
    });

    if (!response.ok) {
      throw new Error(`Backend returned ${response.status}`);
    }

    // Pass through the response directly
    return new Response(response.body, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
    });
  } catch (error) {
    console.error('Streaming error:', error);
    return new Response(
      `data: ${JSON.stringify({ error: 'Streaming failed' })}\n\n`,
      {
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache',
          'Connection': 'keep-alive',
        },
      }
    );
  }
}