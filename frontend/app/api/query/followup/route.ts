// app/api/query/followup/route.ts
import { NextResponse } from 'next/server';

export async function POST(req: Request) {
  try {
    const { question, conversation_id } = await req.json();
    
    if (!conversation_id) {
      return NextResponse.json(
        { error: 'Conversation ID is required for follow-up queries' },
        { status: 400 }
      );
    }

    const response = await fetch('http://localhost:8000/api/query/followup', {
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
    console.error('Error in followup query route:', error);
    return NextResponse.json(
      { error: 'Failed to create follow-up query' },
      { status: 500 }
    );
  }
}