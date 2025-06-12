// app/api/query/initial/route.ts
import { NextResponse } from "next/server";

const API_URL = "https://plasticlist-production-9df0.up.railway.app";

export async function POST(req: Request) {
  console.log("=== API Route Called ===");

  try {
    // Log request details
    console.log("Request URL:", req.url);
    console.log("Request method:", req.method);
    console.log("Content-Type:", req.headers.get("content-type"));

    // Check if body exists
    const hasBody = req.body !== null;
    console.log("Request has body:", hasBody);

    // Try to read the body
    const rawBody = await req.text();
    console.log("Raw body:", rawBody);
    console.log("Raw body length:", rawBody.length);

    if (!rawBody) {
      console.error("No body received");
      return NextResponse.json({ error: "No body received" }, { status: 400 });
    }

    // Parse JSON
    let parsedBody;
    try {
      parsedBody = JSON.parse(rawBody);
      console.log("Parsed body:", parsedBody);
    } catch (jsonError) {
      console.error("JSON parse error:", jsonError);
      return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
    }

    const { question } = parsedBody;
    console.log("Extracted question:", question);

    if (!question) {
      console.error("No question in body");
      return NextResponse.json({ error: "Question required" }, { status: 400 });
    }

    console.log("Making backend request to:", `${API_URL}/api/query/initial`);

    const response = await fetch(`${API_URL}/api/query/initial`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ question }),
    });

    console.log("Backend response status:", response.status);

    if (!response.ok) {
      const errorText = await response.text();
      console.error("Backend error:", errorText);
      throw new Error(
        `Backend responded with status: ${response.status} - ${errorText}`
      );
    }

    const data = await response.json();
    console.log("Backend success:", data);
    return NextResponse.json(data);
  } catch (error) {
    console.error("Full error in API route:", error);
    return NextResponse.json(
      { error: "Failed to create initial query", details: error.message },
      { status: 500 }
    );
  }
}
