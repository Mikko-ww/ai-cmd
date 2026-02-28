#!/usr/bin/env node

const DEFAULT_MODEL_CATALOG = Object.freeze([
  Object.freeze({
    name: 'Auto',
    capability: 'Copilot auto-selects the best model based on availability and helps reduce rate limiting'
  }),
  Object.freeze({
    name: 'Claude Opus 4.6',
    capability: 'Strongest Anthropic model for complex agentic coding, long-running tasks, and large-codebase review/debugging'
  }),
  Object.freeze({
    name: 'Claude Sonnet 4.6',
    capability: 'Upgraded coding and computer-use performance with stronger long-context reasoning and planning'
  }),
  Object.freeze({
    name: 'GPT-5.3-Codex',
    capability: 'OpenAI\'s most capable agentic coding model, optimized for long-running tool-use workflows with high context'
  })
]);

function buildCustomInstructions(lines) {
  return lines.filter(line => line !== '').join('\n');
}

function formatComment(lines) {
  return lines.filter(line => line !== '').join('\n');
}

function parsePositiveIntegerStrict(name, value) {
  const normalized = String(value || '').trim();
  if (!/^[1-9][0-9]*$/.test(normalized)) {
    throw new Error(`${name} must be a positive integer, got: ${value}`);
  }

  const parsed = Number(normalized);
  if (!Number.isSafeInteger(parsed)) {
    throw new Error(`${name} exceeds safe integer range: ${value}`);
  }

  return parsed;
}

function normalizeModelName(model) {
  const normalized = String(model || '').trim();
  if (!normalized) {
    return '';
  }

  if (normalized.toLowerCase() === 'auto') {
    return '';
  }

  return normalized;
}

function displayModelName(model) {
  return normalizeModelName(model) || 'auto';
}

function isNonEmptyString(value) {
  return typeof value === 'string' && value.trim().length > 0;
}

function toModelCatalogEntry(entry) {
  if (!entry || typeof entry !== 'object') {
    return null;
  }

  if (!isNonEmptyString(entry.name) || !isNonEmptyString(entry.capability)) {
    return null;
  }

  return {
    name: entry.name.trim(),
    capability: entry.capability.trim()
  };
}

function resolveModelCatalog(config = {}) {
  const configuredCatalog = config?.copilot?.model_catalog;
  if (!Array.isArray(configuredCatalog)) {
    return DEFAULT_MODEL_CATALOG.map((entry) => ({ ...entry }));
  }

  const normalizedCatalog = configuredCatalog
    .map((entry) => toModelCatalogEntry(entry))
    .filter((entry) => entry !== null);

  if (normalizedCatalog.length === 0) {
    return DEFAULT_MODEL_CATALOG.map((entry) => ({ ...entry }));
  }

  return normalizedCatalog;
}

function formatModelCatalogForPrompt(catalog) {
  return (catalog || [])
    .map((entry) => `- ${entry.name}: ${entry.capability}`)
    .join('\n');
}

module.exports = {
  buildCustomInstructions,
  formatComment,
  parsePositiveIntegerStrict,
  normalizeModelName,
  displayModelName,
  resolveModelCatalog,
  formatModelCatalogForPrompt,
  DEFAULT_MODEL_CATALOG
};
