// app/api/query/followup/route.ts
import { NextResponse } from "next/server";

const API_URL = "https://plasticlist-production-9df0.up.railway.app";

export async function POST(req: Request) {
  try {
    const { question, conversation_id } = await req.json();

    if (!conversation_id) {
      return NextResponse.json(
        { error: "Conversation ID is required for follow-up queries" },
        { status: 400 }
      );
    }

    const response = await fetch(`${API_URL}/api/query/followup`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ question, conversation_id }),
    });

    if (!response.ok) {
      throw new Error(`Backend responded with status: ${response.status}`);
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error in followup query route:", error);
    // Check if it's a connection error
    if (error instanceof TypeError && error.message.includes("fetch failed")) {
      return NextResponse.json(
        { error: "Backend service unavailable" },
        { status: 503 }
      );
    }
    return NextResponse.json(
      { error: "Failed to create follow-up query" },
      { status: 500 }
    );
  }
}
