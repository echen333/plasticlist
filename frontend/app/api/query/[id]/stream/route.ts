// import { type NextRequest } from 'next/server';

export const runtime = 'edge';

const API_URL = 'https://plasticlist-production.up.railway.app';

export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  
  console.log('Stream route called for id:', id);
  
  try {
    const response = await fetch(`${API_URL}/api/query/${id}/stream`, {
      method: 'GET',
    });
    if (!response.ok) {
      throw new Error(`Backend returned ${response.status}`);
    }
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