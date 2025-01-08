// app/api/query/[id]/route.ts
import { NextRequest, NextResponse } from 'next/server';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function GET(
  request: NextRequest,
  context: { params: { id: string } }
) {
  // Properly await the params
  const { id } = await context.params;

  try {
    const response = await fetch(`${API_URL}/api/query/${id}`, {
      cache: 'no-store'
    });

    if (!response.ok) {
      throw new Error(`Backend returned ${response.status}`);
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching query:', error);
    return NextResponse.json(
      { error: 'Failed to fetch query results' },
      { status: 500 }
    );
  }
}