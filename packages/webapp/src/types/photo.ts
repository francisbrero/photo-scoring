export interface Photo {
  id: string;
  image_path: string;  // Storage path
  original_filename: string | null;  // Original filename when uploaded
  image_url: string | null;  // Signed URL for displaying the image
  final_score: number | null;  // null means not yet scored
  aesthetic_score: number | null;
  technical_score: number | null;
  composition: number;
  subject_strength: number;
  visual_appeal: number;
  sharpness: number;
  exposure: number;
  noise_level: number;
  scene_type?: string;
  lighting?: string;
  subject_position?: string;
  description?: string;
  location_name?: string;
  location_country?: string;
  explanation?: string;
  improvements?: string;
  features_json?: string;
  qwen_aesthetic?: number;
  gpt4o_aesthetic?: number;
  gemini_aesthetic?: number;
}

export interface PhotoFeatures {
  color_palette?: string;
  [key: string]: unknown;
}

export interface Correction {
  image_path: string;
  timestamp: string;
  original_score?: number;
  original_aesthetic?: number;
  original_technical?: number;
  score?: number;
  composition?: number;
  subject?: number;
  appeal?: number;
  notes?: string;
}

export type SortOption =
  | 'score_desc'
  | 'score_asc'
  | 'name'
  | 'aesthetic'
  | 'technical';

export type ScoreLevel =
  | 'excellent'
  | 'strong'
  | 'competent'
  | 'tourist'
  | 'flawed'
  | 'unscored';

export function getScoreLevel(score: number | null): ScoreLevel {
  if (score === null) return 'unscored';
  if (score >= 85) return 'excellent';
  if (score >= 70) return 'strong';
  if (score >= 50) return 'competent';
  if (score >= 30) return 'tourist';
  return 'flawed';
}

export function getScoreLabel(score: number | null): string {
  if (score === null) return 'Not Scored';
  if (score >= 85) return 'Excellent';
  if (score >= 70) return 'Strong';
  if (score >= 50) return 'Competent';
  if (score >= 30) return 'Tourist';
  return 'Flawed';
}

export function isScored(photo: Photo): boolean {
  return photo.final_score !== null;
}
