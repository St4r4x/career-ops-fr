import type { LlmProviderName } from "@/lib/types";

export const ALL_LLM_PROVIDERS: LlmProviderName[] = [
  "huggingface",
  "ollama_cloud",
  "openai",
  "anthropic",
  "groq",
];

const LLM_PROVIDER_LABELS: Record<LlmProviderName, string> = {
  huggingface: "Hugging Face",
  ollama_cloud: "Ollama Cloud",
  openai: "OpenAI",
  anthropic: "Anthropic (Claude)",
  groq: "Groq",
};

export function llmProviderLabel(provider: LlmProviderName): string {
  return LLM_PROVIDER_LABELS[provider];
}
