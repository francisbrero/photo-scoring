export interface ImageRecord {
  image_id: string;
  file_path: string;
  filename: string;
  relative_path: string;
}

export interface Attributes {
  image_id: string;
  composition: number;
  subject_strength: number;
  visual_appeal: number;
  sharpness: number;
  exposure_balance: number;
  noise_level: number;
  model_name?: string;
  model_version?: string;
}

export interface ScoreResult {
  image_id: string;
  image_path: string;
  final_score: number;
  aesthetic_score: number;
  technical_score: number;
  attributes: Attributes;
  explanation: string;
  improvements: string[];
  description: string;
  cached: boolean;
}

export interface PhotoWithScore extends ImageRecord {
  score?: ScoreResult;
  thumbnail?: string;
  isScoring?: boolean;
}
