#!/usr/bin/env node

const schema = require('./marker-schema.v2.json');

const MARKER_KEYS = Object.values(schema.markers);
const MARKER_KEY_SET = new Set(MARKER_KEYS);

class MarkerValidationError extends Error {
  constructor(code, message, details = {}) {
    super(message);
    this.name = 'MarkerValidationError';
    this.code = code;
    this.details = details;
  }
}

function getPattern(name) {
  return new RegExp(schema.patterns[name]);
}

function isBlockquoteLine(line) {
  return line.trimStart().startsWith('>');
}

function isMarkdownFenceLine(line) {
  const trimmed = line.trim();
  return trimmed.startsWith('```') || trimmed.startsWith('~~~');
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function isMarkerStartLine(line) {
  const pattern = new RegExp(`^\\s*${escapeRegExp(schema.block.start)}\\s*$`);
  return pattern.test(line);
}

function isMarkerEndLine(line) {
  const pattern = new RegExp(`^\\s*${escapeRegExp(schema.block.end)}(?:\\s*<\\/[^>]+>)?\\s*$`);
  return pattern.test(line);
}

function stripBlockquotePrefix(line) {
  return line.replace(/^\s*>\s?/, '');
}

function extractBlocksFromLines(lines, options = { ignoreFences: true }) {
  const blocks = [];
  let inFence = false;
  let startLine = -1;
  let currentLines = [];

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];

    if (options.ignoreFences && isMarkdownFenceLine(line)) {
      inFence = !inFence;
      continue;
    }

    if (options.ignoreFences && inFence) {
      continue;
    }

    if (isMarkerStartLine(line)) {
      if (startLine !== -1) {
        throw new MarkerValidationError('AGENT_MARKER_BLOCK_INVALID', 'Nested marker blocks are not allowed');
      }
      startLine = index;
      currentLines = [];
      continue;
    }

    if (isMarkerEndLine(line)) {
      if (startLine === -1) {
        throw new MarkerValidationError('AGENT_MARKER_BLOCK_INVALID', 'Marker block end appears before start');
      }

      blocks.push({
        content: currentLines.join('\n'),
        startLine,
        endLine: index
      });
      startLine = -1;
      currentLines = [];
      continue;
    }

    if (startLine !== -1) {
      currentLines.push(line);
    }
  }

  if (startLine !== -1) {
    throw new MarkerValidationError('AGENT_MARKER_BLOCK_INVALID', 'Marker block end appears before start');
  }

  return blocks;
}

function validateBlockForContext(blockContent, context) {
  const rawMarkers = parseMarkerLines(blockContent);
  const normalized = normalizeMetadata(rawMarkers);
  return validateMetadata(normalized, context);
}

function extractMarkerBlock(body, context = 'any') {
  const content = typeof body === 'string' ? body : '';
  const topLevelLines = content.split(/\r?\n/).filter((line) => !isBlockquoteLine(line));
  const topLevelBlocks = extractBlocksFromLines(topLevelLines, { ignoreFences: true });

  if (topLevelBlocks.length > 1) {
    throw new MarkerValidationError(
      'AGENT_MARKER_BLOCK_DUPLICATE',
      'Multiple marker blocks are not allowed',
      { scope: 'top-level', count: topLevelBlocks.length }
    );
  }

  if (topLevelBlocks.length === 1) {
    return topLevelBlocks[0].content;
  }

  const quotedLines = content
    .split(/\r?\n/)
    .filter((line) => isBlockquoteLine(line))
    .map((line) => stripBlockquotePrefix(line));
  const quotedBlocks = extractBlocksFromLines(quotedLines, { ignoreFences: false });

  if (quotedBlocks.length === 0) {
    throw new MarkerValidationError(
      'AGENT_MARKER_BLOCK_MISSING',
      'Missing marker block boundaries',
      { start: schema.block.start, end: schema.block.end }
    );
  }

  const validBlocks = [];
  let lastValidationError = null;

  for (const block of quotedBlocks) {
    try {
      validateBlockForContext(block.content, context);
      validBlocks.push(block);
    } catch (error) {
      if (error instanceof MarkerValidationError) {
        lastValidationError = error;
        continue;
      }
      throw error;
    }
  }

  if (validBlocks.length > 1) {
    throw new MarkerValidationError(
      'AGENT_MARKER_BLOCK_DUPLICATE',
      'Multiple marker blocks are not allowed',
      { scope: 'quoted', count: validBlocks.length }
    );
  }

  if (validBlocks.length === 1) {
    return validBlocks[0].content;
  }

  if (lastValidationError) {
    throw lastValidationError;
  }

  throw new MarkerValidationError(
    'AGENT_MARKER_BLOCK_MISSING',
    'Missing marker block boundaries',
    { start: schema.block.start, end: schema.block.end }
  );
}

function parseMarkerLines(blockContent) {
  const parsed = {};
  const lines = blockContent.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);

  if (lines.length === 0) {
    throw new MarkerValidationError('AGENT_MARKER_BLOCK_EMPTY', 'Marker block is empty');
  }

  for (const line of lines) {
    const match = line.match(/^([A-Za-z][A-Za-z0-9-]*):\s*(.+)$/);
    if (!match) {
      throw new MarkerValidationError(
        'AGENT_MARKER_LINE_INVALID',
        `Invalid marker line format: ${line}`
      );
    }

    const markerKey = match[1].trim();
    const markerValue = match[2].trim();

    if (!MARKER_KEY_SET.has(markerKey)) {
      throw new MarkerValidationError(
        'AGENT_MARKER_UNKNOWN_FIELD',
        `Unknown marker field: ${markerKey}`,
        { markerKey }
      );
    }

    if (Object.prototype.hasOwnProperty.call(parsed, markerKey)) {
      throw new MarkerValidationError(
        'AGENT_MARKER_DUPLICATE_FIELD',
        `Duplicate marker field: ${markerKey}`,
        { markerKey }
      );
    }

    parsed[markerKey] = markerValue;
  }

  return parsed;
}

function normalizeMetadata(rawMarkers) {
  const normalized = {
    schemaVersion: null,
    parentIssue: null,
    prType: null,
    issueType: null,
    phaseName: null,
    taskKey: null,
    retryCount: null
  };

  const markerNames = schema.markers;

  if (rawMarkers[markerNames.schemaVersion]) {
    normalized.schemaVersion = parseInt(rawMarkers[markerNames.schemaVersion], 10);
  }

  if (rawMarkers[markerNames.parentIssue]) {
    normalized.parentIssue = parseInt(rawMarkers[markerNames.parentIssue], 10);
  }

  if (rawMarkers[markerNames.prType]) {
    normalized.prType = rawMarkers[markerNames.prType];
  }

  if (rawMarkers[markerNames.issueType]) {
    normalized.issueType = rawMarkers[markerNames.issueType];
  }

  if (rawMarkers[markerNames.phaseName]) {
    normalized.phaseName = rawMarkers[markerNames.phaseName];
  }

  if (rawMarkers[markerNames.taskKey]) {
    normalized.taskKey = rawMarkers[markerNames.taskKey];
  }

  if (rawMarkers[markerNames.retryCount]) {
    normalized.retryCount = parseInt(rawMarkers[markerNames.retryCount], 10);
  }

  return normalized;
}

function validateMetadata(metadata, context = 'any') {
  const markerNames = schema.markers;

  if (metadata.schemaVersion !== schema.version) {
    throw new MarkerValidationError(
      'AGENT_SCHEMA_UNSUPPORTED',
      `Unsupported schema version: ${metadata.schemaVersion}`,
      { expected: schema.version, field: markerNames.schemaVersion }
    );
  }

  if (!getPattern('parentIssue').test(String(metadata.parentIssue))) {
    throw new MarkerValidationError(
      'AGENT_MARKER_PARENT_INVALID',
      'Invalid parent issue marker',
      { field: markerNames.parentIssue }
    );
  }

  if (context === 'pr') {
    if (!metadata.prType) {
      throw new MarkerValidationError(
        'AGENT_MARKER_PR_TYPE_MISSING',
        `${markerNames.prType} is required for PR metadata`
      );
    }
    if (metadata.issueType) {
      throw new MarkerValidationError(
        'AGENT_MARKER_CONTEXT_CONFLICT',
        `${markerNames.issueType} is not allowed in PR metadata`
      );
    }
  }

  if (context === 'issue') {
    if (!metadata.issueType) {
      throw new MarkerValidationError(
        'AGENT_MARKER_ISSUE_TYPE_MISSING',
        `${markerNames.issueType} is required for Issue metadata`
      );
    }
    if (metadata.prType) {
      throw new MarkerValidationError(
        'AGENT_MARKER_CONTEXT_CONFLICT',
        `${markerNames.prType} is not allowed in Issue metadata`
      );
    }
  }

  if (metadata.prType && metadata.issueType) {
    throw new MarkerValidationError(
      'AGENT_MARKER_CONTEXT_CONFLICT',
      'PR and Issue type markers cannot coexist'
    );
  }

  if (!metadata.prType && !metadata.issueType) {
    throw new MarkerValidationError(
      'AGENT_MARKER_CONTEXT_MISSING',
      'Either PR type or Issue type marker must be provided'
    );
  }

  if (metadata.prType && !schema.enums.prType.includes(metadata.prType)) {
    throw new MarkerValidationError(
      'AGENT_MARKER_PR_TYPE_INVALID',
      `Invalid PR type: ${metadata.prType}`,
      { allowed: schema.enums.prType }
    );
  }

  if (metadata.issueType && !schema.enums.issueType.includes(metadata.issueType)) {
    throw new MarkerValidationError(
      'AGENT_MARKER_ISSUE_TYPE_INVALID',
      `Invalid Issue type: ${metadata.issueType}`,
      { allowed: schema.enums.issueType }
    );
  }

  if (metadata.phaseName && !schema.enums.phaseName.includes(metadata.phaseName)) {
    throw new MarkerValidationError(
      'AGENT_MARKER_PHASE_INVALID',
      `Invalid phase name: ${metadata.phaseName}`,
      { allowed: schema.enums.phaseName }
    );
  }

  if (metadata.taskKey && !getPattern('taskKey').test(metadata.taskKey)) {
    throw new MarkerValidationError(
      'AGENT_MARKER_TASK_KEY_INVALID',
      `Invalid task key: ${metadata.taskKey}`,
      { pattern: schema.patterns.taskKey }
    );
  }

  if (metadata.retryCount !== null && !getPattern('retryCount').test(String(metadata.retryCount))) {
    throw new MarkerValidationError(
      'AGENT_MARKER_RETRY_COUNT_INVALID',
      `Invalid retry count: ${metadata.retryCount}`,
      { pattern: schema.patterns.retryCount }
    );
  }

  if (metadata.prType === 'spec' || metadata.prType === 'plan') {
    if (!metadata.phaseName) {
      throw new MarkerValidationError('AGENT_MARKER_PHASE_REQUIRED', `${markerNames.phaseName} is required for phase PR`);
    }
    if (metadata.phaseName !== metadata.prType) {
      throw new MarkerValidationError('AGENT_MARKER_PHASE_MISMATCH', 'PR type and phase name must match');
    }
    if (metadata.taskKey) {
      throw new MarkerValidationError('AGENT_MARKER_TASK_KEY_FORBIDDEN', `${markerNames.taskKey} is not allowed for phase PR`);
    }
    if (metadata.retryCount !== null) {
      throw new MarkerValidationError('AGENT_MARKER_RETRY_FORBIDDEN', `${markerNames.retryCount} is not allowed in PR metadata`);
    }
  }

  if (metadata.prType === 'task') {
    if (!metadata.taskKey) {
      throw new MarkerValidationError('AGENT_MARKER_TASK_KEY_REQUIRED', `${markerNames.taskKey} is required for task PR`);
    }
    if (metadata.phaseName) {
      throw new MarkerValidationError('AGENT_MARKER_PHASE_FORBIDDEN', `${markerNames.phaseName} is not allowed for task PR`);
    }
    if (metadata.retryCount !== null) {
      throw new MarkerValidationError('AGENT_MARKER_RETRY_FORBIDDEN', `${markerNames.retryCount} is not allowed in PR metadata`);
    }
  }

  if (metadata.issueType === 'phase') {
    if (!metadata.phaseName) {
      throw new MarkerValidationError('AGENT_MARKER_PHASE_REQUIRED', `${markerNames.phaseName} is required for phase Issue`);
    }
    if (metadata.taskKey) {
      throw new MarkerValidationError('AGENT_MARKER_TASK_KEY_FORBIDDEN', `${markerNames.taskKey} is not allowed for phase Issue`);
    }
  }

  if (metadata.issueType === 'task') {
    if (!metadata.taskKey) {
      throw new MarkerValidationError('AGENT_MARKER_TASK_KEY_REQUIRED', `${markerNames.taskKey} is required for task Issue`);
    }
    if (metadata.phaseName) {
      throw new MarkerValidationError('AGENT_MARKER_PHASE_FORBIDDEN', `${markerNames.phaseName} is not allowed for task Issue`);
    }
    if (metadata.retryCount !== null) {
      throw new MarkerValidationError('AGENT_MARKER_RETRY_FORBIDDEN', `${markerNames.retryCount} is not allowed for task Issue`);
    }
  }

  return metadata;
}

function parseAgentMetadata(body, context = 'any') {
  const block = extractMarkerBlock(body, context);
  const rawMarkers = parseMarkerLines(block);
  const normalized = normalizeMetadata(rawMarkers);
  return validateMetadata(normalized, context);
}

function tryParseAgentMetadata(body, context = 'any') {
  try {
    const metadata = parseAgentMetadata(body, context);
    return { ok: true, metadata, error: null };
  } catch (error) {
    return { ok: false, metadata: null, error };
  }
}

function buildMarkerBlock(metadata, context = 'any') {
  const normalized = validateMetadata({
    schemaVersion: metadata.schemaVersion || schema.version,
    parentIssue: metadata.parentIssue,
    prType: metadata.prType || null,
    issueType: metadata.issueType || null,
    phaseName: metadata.phaseName || null,
    taskKey: metadata.taskKey || null,
    retryCount: metadata.retryCount || null
  }, context);

  const orderedFields = [
    'schemaVersion',
    'parentIssue',
    'prType',
    'issueType',
    'phaseName',
    'taskKey',
    'retryCount'
  ];

  const lines = [schema.block.start];
  for (const field of orderedFields) {
    const value = normalized[field];
    if (value === null || value === undefined || value === '') {
      continue;
    }
    lines.push(`${schema.markers[field]}: ${value}`);
  }
  lines.push(schema.block.end);
  return lines.join('\n');
}

module.exports = {
  MarkerValidationError,
  parseAgentMetadata,
  tryParseAgentMetadata,
  buildMarkerBlock,
  schema
};
