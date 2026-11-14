/** Types for the optional AI assistance features. */

export interface AiSettings {
  enabled: boolean;
  provider: "anthropic" | "bedrock" | "vertex" | "foundry";
  model: string;
  region: string | null;
  project_id: string | null;
  resource: string | null;
  api_key_set: boolean;
  redact_identifiers: boolean;
  updated_at: string | null;
  updated_by: string | null;
  missing_configuration: string | null;
  providers: Record<string, string>;
}

export interface AiPreview {
  document_title: string;
  provider: string;
  provider_label: string;
  model: string;
  sections: { id: string; heading: string; characters: number; preview: string }[];
  selected_section_ids: string[];
  redact: boolean;
  redaction_count: number;
  requirements: { citation: string; title: string }[];
  system_prompt: string;
  user_prompt: string;
}

export type AiVerdict = "addressed" | "partly_addressed" | "not_addressed";

export interface AiAssessment {
  id: string;
  interaction_id: string;
  document_id: string | null;
  document_title: string;
  citation: string;
  requirement_title: string;
  verdict: AiVerdict;
  evidence: string | null;
  evidence_verified: boolean;
  reasoning: string;
  created_at: string;
}

export interface AiInteractionSummary {
  id: string;
  created_at: string;
  user_name: string;
  purpose: string;
  run_id: string | null;
  document_title: string | null;
  provider: string;
  model_requested: string;
  model_used: string | null;
  fallback_used: boolean;
  status: "success" | "refused" | "error";
  error: string | null;
  redacted: boolean;
  redaction_count: number;
  sections_sent: { heading: string; characters: number }[];
  input_tokens: number | null;
  output_tokens: number | null;
  duration_ms: number | null;
}

export interface AiInteractionDetail extends AiInteractionSummary {
  system_prompt: string;
  user_prompt: string;
  response_text: string | null;
  request_id: string | null;
}

export const VERDICT_LABELS: Record<AiVerdict, string> = {
  addressed: "Addressed",
  partly_addressed: "Partly addressed",
  not_addressed: "Not addressed",
};

export const PROVIDER_FIELDS: Record<AiSettings["provider"], { apiKey: boolean; region: boolean; project: boolean; resource: boolean; note: string }> = {
  anthropic: {
    apiKey: true,
    region: false,
    project: false,
    resource: false,
    note: "Sent to Anthropic. Use an organization API key under your enterprise agreement (no training on your data; ask about zero data retention).",
  },
  bedrock: {
    apiKey: false,
    region: true,
    project: false,
    resource: false,
    note: "Stays in your own AWS account and region. Uses this server's AWS credentials (IAM role or environment); Claude must be enabled in Bedrock.",
  },
  vertex: {
    apiKey: false,
    region: true,
    project: true,
    resource: false,
    note: "Stays in your own Google Cloud project. Uses this server's Google Cloud credentials (application default credentials).",
  },
  foundry: {
    apiKey: true,
    region: false,
    project: false,
    resource: true,
    note: "Runs through your Microsoft Foundry (Azure) resource and deployment. The model name is your deployment name.",
  },
};
