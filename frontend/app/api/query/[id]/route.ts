import { NextRequest } from 'next/server';

export const runtime = 'edge';

export async function GET(
  request: NextRequest,
  context: { params: { id: string } }
) {
  const { params } = await context;
  const { id } = params;
  
  try {
    if (!id) {
      return Response.json(
        { error: 'No ID provided' },
        { status: 400 }
      );
    }
    
    const response = await fetch(`http://localhost:8000/api/query/${id}`, {
      method: 'GET',
    });

    if (!response.ok) {
      throw new Error(`Backend returned ${response.status}`);
    }

    const data = await response.json();
    return Response.json(data);
    
  } catch (error) {
    console.error('Query fetch error:', error);
    return Response.json(
      { error: 'Failed to fetch query' },
      { status: 500 }
    );
  }
}