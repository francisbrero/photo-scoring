/**
 * Direct file upload to Supabase Storage.
 * Bypasses Vercel's 4.5MB body size limit by uploading directly to storage.
 */

import { supabase } from './supabase';

const BUCKET_NAME = 'photos';
const CHUNK_SIZE = 5; // Upload 5 files concurrently

export interface UploadedFile {
  originalName: string;
  storagePath: string;
  size: number;
}

export interface UploadProgress {
  uploaded: number;
  total: number;
  currentFile: string;
}

/**
 * Upload multiple files to Supabase Storage with progress tracking.
 * Files are uploaded directly to Supabase, bypassing Vercel.
 */
export async function uploadFilesToStorage(
  files: File[],
  userId: string,
  jobId: string,
  onProgress?: (progress: UploadProgress) => void
): Promise<UploadedFile[]> {
  const uploaded: UploadedFile[] = [];
  const basePath = `triage/${userId}/${jobId}`;

  // Process files in chunks to avoid overwhelming the connection
  for (let i = 0; i < files.length; i += CHUNK_SIZE) {
    const chunk = files.slice(i, i + CHUNK_SIZE);

    const uploadPromises = chunk.map(async (file, chunkIndex) => {
      const globalIndex = i + chunkIndex;

      // Generate unique filename
      const ext = file.name.split('.').pop() || 'jpg';
      const uniqueName = `${crypto.randomUUID()}.${ext}`;
      const storagePath = `${basePath}/${uniqueName}`;

      // Report progress
      if (onProgress) {
        onProgress({
          uploaded: globalIndex,
          total: files.length,
          currentFile: file.name,
        });
      }

      // Upload to Supabase Storage
      const { error } = await supabase.storage
        .from(BUCKET_NAME)
        .upload(storagePath, file, {
          contentType: file.type || 'image/jpeg',
          upsert: false,
        });

      if (error) {
        console.error(`Failed to upload ${file.name}:`, error);
        throw new Error(`Failed to upload ${file.name}: ${error.message}`);
      }

      return {
        originalName: file.name,
        storagePath,
        size: file.size,
      };
    });

    const results = await Promise.all(uploadPromises);
    uploaded.push(...results);
  }

  // Final progress update
  if (onProgress) {
    onProgress({
      uploaded: files.length,
      total: files.length,
      currentFile: 'Complete',
    });
  }

  return uploaded;
}

/**
 * Delete uploaded files from storage (for cleanup on error).
 */
export async function deleteUploadedFiles(
  storagePaths: string[]
): Promise<void> {
  if (storagePaths.length === 0) return;

  const { error } = await supabase.storage
    .from(BUCKET_NAME)
    .remove(storagePaths);

  if (error) {
    console.error('Failed to clean up files:', error);
  }
}
