import { NextResponse } from 'next/server';

export async function POST(req: Request) {
  try {
    const { question, conversation_id } = await req.json();
    
    const response = await fetch('http://localhost:8000/api/query/generate-followups', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ question, conversation_id })
    });

    if (!response.ok) {
      throw new Error(`Backend responded with status: ${response.status}`);
    }
    
    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error in followup generation route:', error);
    return NextResponse.json(
      { error: 'Failed to generate followup questions' },
      { status: 500 }
    );
  }
}