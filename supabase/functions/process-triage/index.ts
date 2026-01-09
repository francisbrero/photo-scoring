// Supabase Edge Function: process-triage
// This function processes triage jobs in the background.
// It is triggered by a database webhook when a job transitions to 'processing'.
// The actual processing happens on the Render API (same pattern as process-scoring-queue).

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers":
    "authorization, x-client-info, apikey, content-type",
};

interface TriageJob {
  id: string;
  user_id: string;
  status: string;
  phase: string;
  target: string;
  criteria: string;
  passes: number;
  total_input: number;
}

interface WebhookPayload {
  type: "INSERT" | "UPDATE" | "DELETE";
  table: string;
  record: TriageJob;
  old_record?: TriageJob;
}

// Call the FastAPI internal endpoint to process the triage job
async function processTriageViaApi(
  jobId: string,
  userId: string,
  apiBaseUrl: string,
  internalApiKey: string
): Promise<{ success: boolean; error?: string }> {
  try {
    const response = await fetch(
      `${apiBaseUrl}/api/triage/internal/process?x-internal-key=${encodeURIComponent(internalApiKey)}`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          job_id: jobId,
          user_id: userId,
        }),
      }
    );

    const data = await response.json();

    if (!response.ok) {
      return {
        success: false,
        error: data.detail || `HTTP ${response.status}: ${response.statusText}`,
      };
    }

    return { success: data.success !== false, error: data.error };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : "Unknown error",
    };
  }
}

Deno.serve(async (req) => {
  // Handle CORS preflight
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    // Get environment variables
    const supabaseUrl = Deno.env.get("SUPABASE_URL");
    const supabaseServiceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
    const apiBaseUrl =
      Deno.env.get("API_BASE_URL") || "https://photo-scoring-api.onrender.com";
    const internalApiKey =
      Deno.env.get("INTERNAL_API_KEY") || supabaseServiceKey;

    if (!supabaseUrl || !supabaseServiceKey) {
      throw new Error("Missing required environment variables");
    }

    if (!internalApiKey) {
      throw new Error("Missing internal API key");
    }

    // Parse request body
    let payload: WebhookPayload | null = null;
    if (req.method === "POST") {
      try {
        payload = await req.json();
      } catch {
        // Not JSON body
      }
    }

    // Validate webhook payload
    if (!payload || payload.table !== "triage_jobs") {
      return new Response(
        JSON.stringify({ error: "Invalid webhook payload" }),
        {
          headers: { ...corsHeaders, "Content-Type": "application/json" },
          status: 400,
        }
      );
    }

    const job = payload.record;
    const oldRecord = payload.old_record;

    // Only process jobs that just transitioned to processing/grid_generation
    if (job.status !== "processing" || job.phase !== "grid_generation") {
      return new Response(
        JSON.stringify({ message: "Job not ready for processing" }),
        {
          headers: { ...corsHeaders, "Content-Type": "application/json" },
          status: 200,
        }
      );
    }

    // Prevent double-processing
    if (
      oldRecord &&
      oldRecord.status === "processing" &&
      oldRecord.phase === "grid_generation"
    ) {
      return new Response(
        JSON.stringify({ message: "Job already being processed" }),
        {
          headers: { ...corsHeaders, "Content-Type": "application/json" },
          status: 200,
        }
      );
    }

    console.log(`Processing triage job: ${job.id}`);

    // Call the Render API to process the job
    const result = await processTriageViaApi(
      job.id,
      job.user_id,
      apiBaseUrl,
      internalApiKey
    );

    if (result.success) {
      console.log(`Triage job ${job.id} processing started`);
    } else {
      console.error(`Triage job ${job.id} failed to start: ${result.error}`);
    }

    return new Response(
      JSON.stringify({
        message: result.success ? "Processing started" : "Processing failed",
        job_id: job.id,
        success: result.success,
        error: result.error,
      }),
      {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
        status: result.success ? 200 : 500,
      }
    );
  } catch (error) {
    console.error("Error processing triage:", error);
    return new Response(
      JSON.stringify({
        error: error instanceof Error ? error.message : "Unknown error",
      }),
      {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
        status: 500,
      }
    );
  }
});
