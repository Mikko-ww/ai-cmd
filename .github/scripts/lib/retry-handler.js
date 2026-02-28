#!/usr/bin/env node

const core = require('@actions/core');
const { PHASES, PHASE_STATUS } = require('./phase-manager');
const { buildMarkerBlock } = require('./marker-parser');

const MAX_RETRIES = 3;

function canRetry(state, phase) {
  if (!state.phases || !state.phases[phase]) {
    return false;
  }
  
  const phaseData = state.phases[phase];
  const retryCount = phaseData.retry_count || 0;
  
  return retryCount < MAX_RETRIES && phaseData.status === PHASE_STATUS.FAILED;
}

function getRetryCount(state, phase) {
  if (!state.phases || !state.phases[phase]) {
    return 0;
  }
  
  return state.phases[phase].retry_count || 0;
}

async function createRetryIssue(github, epicIssue, phase, failedIssue, reason) {
  const retryCount = getRetryCount(epicIssue.state, phase) + 1;
  const phaseDisplayName = getPhaseDisplayName(phase);

  const markerBlock = buildMarkerBlock({
    parentIssue: epicIssue.number,
    issueType: 'phase',
    phaseName: phase,
    retryCount
  }, 'issue');
  
  const title = `[Retry ${retryCount}/${MAX_RETRIES}] ${phaseDisplayName} - Issue #${epicIssue.number}`;
  
  const body = [
    `## 🔄 Retry Attempt ${retryCount}/${MAX_RETRIES}`,
    '',
    `**Parent Issue:** #${epicIssue.number}`,
    `**Phase:** ${phaseDisplayName}`,
    `**Failed Issue:** #${failedIssue}`,
    '',
    '### Failure Reason',
    '',
    reason || 'No specific reason provided',
    '',
    '### Instructions',
    '',
    'This is an automatic retry. Please review the failure reason above and:',
    '1. Check if the previous attempt had any issues',
    '2. Review the parent issue requirements',
    '3. Generate the required deliverable',
    '',
    '---',
    '',
    markerBlock
  ].join('\n');
  
  const labels = [
    `agent:phase:${phase}`
  ];
  
  const newIssue = await github.createIssue(title, body, labels);
  
  core.info(`Created retry issue #${newIssue.number} for phase ${phase} (attempt ${retryCount}/${MAX_RETRIES})`);
  
  return newIssue.number;
}

function getPhaseDisplayName(phase) {
  const names = {
    [PHASES.SPEC]: '规格说明',
    [PHASES.PLAN]: '执行计划',
    [PHASES.EXECUTION]: '任务执行'
  };
  
  return names[phase] || phase;
}

function incrementRetryCount(state, phase) {
  if (!state.phases || !state.phases[phase]) {
    return state;
  }
  
  state.phases[phase].retry_count = (state.phases[phase].retry_count || 0) + 1;
  const baseRevision = Number.isInteger(state.revision) && state.revision > 0 ? state.revision : 0;
  state.revision = baseRevision + 1;
  state.updated_at = new Date().toISOString();
  
  return state;
}

function hasExceededMaxRetries(state, phase) {
  const retryCount = getRetryCount(state, phase);
  return retryCount >= MAX_RETRIES;
}

module.exports = {
  MAX_RETRIES,
  canRetry,
  getRetryCount,
  createRetryIssue,
  incrementRetryCount,
  hasExceededMaxRetries
};
