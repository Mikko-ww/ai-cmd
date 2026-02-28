#!/usr/bin/env node

const core = require('@actions/core');
const { PHASES, initializePhases } = require('./phase-manager');

const STATE_VERSION = '1.0.0';

function parseVersion(version) {
  if (typeof version !== 'string') {
    return null;
  }

  const match = version.trim().match(/^(\d+)\.(\d+)\.(\d+)$/);
  if (!match) {
    return null;
  }

  return {
    major: parseInt(match[1], 10),
    minor: parseInt(match[2], 10),
    patch: parseInt(match[3], 10)
  };
}

function isSupportedVersion(version) {
  const expected = parseVersion(STATE_VERSION);
  const actual = parseVersion(version);

  if (!expected || !actual) {
    return false;
  }

  if (actual.major !== expected.major) {
    return false;
  }

  if (actual.minor !== expected.minor) {
    return false;
  }

  return actual.patch >= expected.patch;
}

function normalizeRevision(revision) {
  if (!Number.isFinite(revision) && typeof revision !== 'string') {
    return null;
  }

  const parsed = parseInt(revision, 10);
  if (!Number.isInteger(parsed) || parsed < 1) {
    return null;
  }

  return parsed;
}

function compareStateEntries(a, b) {
  const revisionA = normalizeRevision(a.state.revision) || 0;
  const revisionB = normalizeRevision(b.state.revision) || 0;
  if (revisionA !== revisionB) {
    return revisionB - revisionA;
  }

  const createdAtA = Date.parse(a.createdAt || '');
  const createdAtB = Date.parse(b.createdAt || '');
  if (Number.isFinite(createdAtA) && Number.isFinite(createdAtB) && createdAtA !== createdAtB) {
    return createdAtB - createdAtA;
  }

  const commentIdA = Number.isFinite(a.commentId) ? a.commentId : 0;
  const commentIdB = Number.isFinite(b.commentId) ? b.commentId : 0;
  return commentIdB - commentIdA;
}

function serializeState(state) {
  const orderedState = {
    VERSION: state.VERSION,
    revision: state.revision,
    state_id: state.state_id,
    parent_issue: state.parent_issue,
    current_phase: state.current_phase,
    phases: state.phases,
    plan_path: state.plan_path,
    cursor_task_id: state.cursor_task_id,
    tasks: state.tasks,
    paused: state.paused,
    created_at: state.created_at,
    updated_at: state.updated_at
  };

  for (const [key, value] of Object.entries(state)) {
    if (!Object.prototype.hasOwnProperty.call(orderedState, key)) {
      orderedState[key] = value;
    }
  }

  return orderedState;
}

async function getLatestState(github, issueNumber, stateMarker) {
  try {
    const comments = await github.listComments(issueNumber);
    
    const stateComments = comments
      .filter(c => c.body && c.body.includes(stateMarker))
      .map((comment) => {
        const state = parseStateFromComment(comment.body, stateMarker);
        if (!state) {
          return null;
        }

        return {
          state,
          commentId: comment.id,
          createdAt: comment.created_at
        };
      })
      .filter(entry => entry !== null);
    
    if (stateComments.length === 0) {
      return null;
    }
    
    stateComments.sort(compareStateEntries);
    const latestState = stateComments[0].state;

    return assertStateVersion(latestState);
  } catch (error) {
    core.error(`Failed to get latest state: ${error.message}`);
    throw error;
  }
}

async function createStateComment(github, issueNumber, state, stateMarker) {
  try {
    const validatedState = assertStateVersion(state);
    const serializedState = serializeState(validatedState);
    const lines = [
      stateMarker,
      '```json',
      JSON.stringify(serializedState, null, 2),
      '```',
      '',
      `Agent State Updated (VERSION ${serializedState.VERSION}, revision ${serializedState.revision})`,
      ''
    ];
    
    if (serializedState.current_phase) {
      lines.push(`Current Phase: \`${serializedState.current_phase}\``);
    }
    
    if (serializedState.cursor_task_id) {
      lines.push(`Current Task: \`${serializedState.cursor_task_id}\``);
    }
    
    lines.push('', '_This comment tracks execution state. Do not edit manually._');
    
    const body = lines.filter(line => line !== '').join('\n');
    return await github.createComment(issueNumber, body);
  } catch (error) {
    core.error(`Failed to create state comment: ${error.message}`);
    throw error;
  }
}

function parseStateFromComment(commentBody, stateMarker) {
  if (!commentBody || !commentBody.includes(stateMarker)) {
    return null;
  }
  
  try {
    const jsonMatch = commentBody.match(/```json\n([\s\S]*?)\n```/);
    if (jsonMatch && jsonMatch[1]) {
      return JSON.parse(jsonMatch[1]);
    }
  } catch (error) {
    core.warning(`Failed to parse state from comment: ${error.message}`);
  }
  
  return null;
}

function assertStateVersion(state) {
  if (!state) {
    return null;
  }

  if (!isSupportedVersion(state.VERSION)) {
    throw new Error(
      `Unsupported state version: ${state.VERSION}. Expected major/minor ${STATE_VERSION.split('.').slice(0, 2).join('.')} and patch >= ${STATE_VERSION.split('.')[2]}. ` +
      'This release does not support old state formats. Please start a new Epic issue.'
    );
  }

  const revision = normalizeRevision(state.revision);
  if (!revision) {
    throw new Error(
      `Invalid state revision: ${state.revision}. Expected a positive integer starting from 1.`
    );
  }

  state.revision = revision;
  return state;
}

function createInitialState(issueNumber, owner, repo) {
  return {
    VERSION: STATE_VERSION,
    revision: 1,
    state_id: 'agent-state:' + owner + '/' + repo + ':' + issueNumber,
    parent_issue: issueNumber,
    current_phase: PHASES.SPEC,
    phases: initializePhases(),
    plan_path: null,
    cursor_task_id: null,
    tasks: {},
    paused: false,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  };
}

class StateManager {
  constructor(github, issueNumber) {
    this.github = github;
    this.issueNumber = issueNumber;
    this.state = null;
    this.stateMarker = '<!-- agent-state:json -->';
  }

  async load() {
    this.state = await getLatestState(this.github, this.issueNumber, this.stateMarker);
    if (!this.state) {
      throw new Error(`No state found for issue #${this.issueNumber}`);
    }
    return this.state;
  }

  async save() {
    if (!this.state) {
      throw new Error('No state to save. Call load() first.');
    }
    assertStateVersion(this.state);
    this.state.updated_at = new Date().toISOString();
    this.state = serializeState(this.state);
    await createStateComment(this.github, this.issueNumber, this.state, this.stateMarker);
  }
}

module.exports = {
  STATE_VERSION,
  parseVersion,
  isSupportedVersion,
  normalizeRevision,
  serializeState,
  getLatestState,
  createStateComment,
  parseStateFromComment,
  assertStateVersion,
  createInitialState,
  StateManager
};
