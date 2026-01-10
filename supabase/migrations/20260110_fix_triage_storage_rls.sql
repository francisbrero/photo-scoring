-- Fix triage storage RLS policy to allow service role access
-- Service role needs to download triage files for processing

-- Add policy for service role to access all triage files
CREATE POLICY "Service role can access triage files"
ON storage.objects
FOR SELECT
TO service_role
USING (
    bucket_id = 'photos' AND
    (storage.foldername(name))[1] = 'triage'
);
