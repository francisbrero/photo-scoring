// Supabase Edge Function: process-scoring-queue
// This function processes photos from the scoring queue in the background.
// It is triggered by pg_notify when new jobs are added to the queue,
// or can be invoked directly via HTTP to process pending jobs.

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers":
    "authorization, x-client-info, apikey, content-type",
};

interface ScoringJob {
  id: string;
  user_id: string;
  photo_id: string;
  status: string;
  priority: number;
  created_at: string;
  retry_count: number;
}

// Call the FastAPI internal endpoint to process the photo
async function processPhotoViaApi(
  photoId: string,
  userId: string,
  apiBaseUrl: string,
  internalApiKey: string
): Promise<{ success: boolean; error?: string; finalScore?: number }> {
  try {
    const response = await fetch(
      `${apiBaseUrl}/api/photos/internal/process-queue?x-internal-key=${encodeURIComponent(internalApiKey)}`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          photo_id: photoId,
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

    if (data.success) {
      return { success: true, finalScore: data.final_score };
    } else {
      return { success: false, error: data.error || "Unknown error" };
    }
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : "Unknown error",
    };
  }
}

// Process a single job from the queue
async function processJob(
  supabase: ReturnType<typeof createClient>,
  job: ScoringJob,
  apiBaseUrl: string,
  internalApiKey: string
): Promise<{ success: boolean; error?: string }> {
  console.log(`Processing job ${job.id} for photo ${job.photo_id}`);

  // Process the photo via the FastAPI backend
  const result = await processPhotoViaApi(
    job.photo_id,
    job.user_id,
    apiBaseUrl,
    internalApiKey
  );

  if (result.success) {
    console.log(
      `Job ${job.id} completed successfully, score: ${result.finalScore}`
    );
  } else {
    console.error(`Job ${job.id} failed: ${result.error}`);
  }

  return result;
}

// Process all pending jobs in the queue
async function processPendingJobs(
  supabase: ReturnType<typeof createClient>,
  apiBaseUrl: string,
  internalApiKey: string,
  limit: number = 10
): Promise<{ processed: number; succeeded: number; failed: number }> {
  // Get pending jobs ordered by priority and created_at
  const { data: jobs, error } = await supabase
    .from("scoring_queue")
    .select("*")
    .eq("status", "pending")
    .order("priority", { ascending: false })
    .order("created_at", { ascending: true })
    .limit(limit);

  if (error || !jobs || jobs.length === 0) {
    console.log("No pending jobs found");
    return { processed: 0, succeeded: 0, failed: 0 };
  }

  console.log(`Found ${jobs.length} pending jobs`);

  let succeeded = 0;
  let failed = 0;

  for (const job of jobs) {
    const result = await processJob(supabase, job, apiBaseUrl, internalApiKey);
    if (result.success) {
      succeeded++;
    } else {
      failed++;
    }
  }

  return { processed: jobs.length, succeeded, failed };
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
    // API_BASE_URL should point to the FastAPI backend
    // For production, this would be something like https://api.photo-scoring.example.com
    // For local development, use http://localhost:8000 or the appropriate host
    const apiBaseUrl = Deno.env.get("API_BASE_URL") || "http://localhost:8000";
    // Internal API key for authenticating with the FastAPI backend
    // If not set, defaults to the service role key
    const internalApiKey =
      Deno.env.get("INTERNAL_API_KEY") || supabaseServiceKey;

    if (!supabaseUrl || !supabaseServiceKey) {
      throw new Error("Missing required environment variables");
    }

    if (!internalApiKey) {
      throw new Error("Missing internal API key");
    }

    // Create Supabase client with service role
    const supabase = createClient(supabaseUrl, supabaseServiceKey);

    // Parse request body for notification payload (from pg_notify trigger or webhook)
    let notificationPayload: {
      id?: string;
      photo_id?: string;
      user_id?: string;
    } | null = null;

    if (req.method === "POST") {
      try {
        const body = await req.json();
        // Check if this is from a database webhook trigger
        if (body.record) {
          notificationPayload = body.record;
        } else if (body.id || body.photo_id) {
          notificationPayload = body;
        }
      } catch {
        // Not JSON body, that's fine - process all pending jobs
      }
    }

    // If we have a specific job from notification, process just that one
    if (notificationPayload?.photo_id) {
      console.log(
        `Processing specific job for photo: ${notificationPayload.photo_id}`
      );

      const { data: job, error: jobError } = await supabase
        .from("scoring_queue")
        .select("*")
        .eq("photo_id", notificationPayload.photo_id)
        .eq("status", "pending")
        .single();

      if (job && !jobError) {
        const result = await processJob(
          supabase,
          job,
          apiBaseUrl,
          internalApiKey
        );
        return new Response(
          JSON.stringify({
            message: result.success
              ? "Job processed successfully"
              : "Job failed",
            job_id: job.id,
            photo_id: job.photo_id,
            success: result.success,
            error: result.error,
          }),
          {
            headers: { ...corsHeaders, "Content-Type": "application/json" },
            status: result.success ? 200 : 500,
          }
        );
      } else {
        // Job not found or already processed
        return new Response(
          JSON.stringify({
            message: "Job not found or already processed",
            photo_id: notificationPayload.photo_id,
          }),
          {
            headers: { ...corsHeaders, "Content-Type": "application/json" },
            status: 404,
          }
        );
      }
    }

    // Otherwise, process all pending jobs
    console.log("Processing all pending jobs");
    const results = await processPendingJobs(
      supabase,
      apiBaseUrl,
      internalApiKey
    );

    return new Response(
      JSON.stringify({
        message: "Queue processing complete",
        ...results,
      }),
      {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
        status: 200,
      }
    );
  } catch (error) {
    console.error("Error processing queue:", error);
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
