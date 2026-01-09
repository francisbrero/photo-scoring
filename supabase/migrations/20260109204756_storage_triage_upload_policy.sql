-- Migration: Add storage policy for triage uploads
-- Allow authenticated users to upload to their own triage folder

-- Policy: Allow authenticated users to upload files to their triage folder
-- Path pattern: triage/{user_id}/{job_id}/{filename}
CREATE POLICY "Users can upload to own triage folder"
ON storage.objects
FOR INSERT
TO authenticated
WITH CHECK (
    bucket_id = 'photos' AND
    (storage.foldername(name))[1] = 'triage' AND
    (storage.foldername(name))[2] = auth.uid()::text
);

-- Policy: Allow authenticated users to read their own triage files
CREATE POLICY "Users can read own triage files"
ON storage.objects
FOR SELECT
TO authenticated
USING (
    bucket_id = 'photos' AND
    (storage.foldername(name))[1] = 'triage' AND
    (storage.foldername(name))[2] = auth.uid()::text
);

-- Policy: Allow authenticated users to delete their own triage files
CREATE POLICY "Users can delete own triage files"
ON storage.objects
FOR DELETE
TO authenticated
USING (
    bucket_id = 'photos' AND
    (storage.foldername(name))[1] = 'triage' AND
    (storage.foldername(name))[2] = auth.uid()::text
);
