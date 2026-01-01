/**
 * Cloud API client for Photo Scoring.
 * Handles communication with the cloud backend for inference, sync, and billing.
 */

const CLOUD_API_URL = import.meta.env.VITE_CLOUD_API_URL || 'https://api.photoscoring.app';

interface CloudApiOptions {
  authToken?: string;
}

class CloudApiClient {
  private baseUrl: string;
  private authToken: string | null = null;

  constructor(baseUrl: string = CLOUD_API_URL) {
    this.baseUrl = baseUrl;
  }

  setAuthToken(token: string | null): void {
    this.authToken = token;
  }

  private async fetch<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    if (this.authToken) {
      headers['Authorization'] = `Bearer ${this.authToken}`;
    }

    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  /**
   * Get current user info and credits
   */
  async getMe(): Promise<{
    user: { id: string; email: string };
    credits: number;
  }> {
    return this.fetch('/auth/me');
  }

  /**
   * Get available credit packages
   */
  async getPlans(): Promise<{
    plans: Array<{
      id: string;
      credits: number;
      price: number;
      name: string;
    }>;
  }> {
    return this.fetch('/billing/plans');
  }

  /**
   * Create a checkout session for purchasing credits
   */
  async createCheckout(planId: string): Promise<{ url: string }> {
    return this.fetch('/billing/checkout', {
      method: 'POST',
      body: JSON.stringify({ plan_id: planId }),
    });
  }

  /**
   * Run inference through the cloud (costs 1 credit)
   */
  async analyze(imageData: string, imageHash: string): Promise<{
    attributes: {
      image_id: string;
      composition: number;
      subject_strength: number;
      visual_appeal: number;
      sharpness: number;
      exposure_balance: number;
      noise_level: number;
    };
    scores: {
      aesthetic_score: number;
      technical_score: number;
      final_score: number;
    };
    credits_remaining: number;
    cached: boolean;
  }> {
    return this.fetch('/inference/analyze', {
      method: 'POST',
      body: JSON.stringify({
        image_data: imageData,
        image_hash: imageHash,
      }),
    });
  }

  /**
   * Sync local attributes to cloud
   */
  async syncAttributes(
    attributes: Array<{
      image_id: string;
      attributes: Record<string, number>;
      metadata?: Record<string, unknown>;
      scored_at: string;
    }>
  ): Promise<{ synced: number }> {
    return this.fetch('/sync/attributes', {
      method: 'POST',
      body: JSON.stringify({ attributes }),
    });
  }

  /**
   * Get synced attributes from cloud
   */
  async getAttributes(since?: string): Promise<{
    attributes: Array<{
      image_id: string;
      attributes: Record<string, number>;
      metadata?: Record<string, unknown>;
      scored_at: string;
    }>;
  }> {
    const params = since ? `?since=${encodeURIComponent(since)}` : '';
    return this.fetch(`/sync/attributes${params}`);
  }
}

export const cloudApi = new CloudApiClient();
export type { CloudApiOptions };
