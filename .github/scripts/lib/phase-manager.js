#!/usr/bin/env node

const core = require('@actions/core');

/**
 * Phase Manager
 * 
 * Manages phase state transitions for the new architecture:
 * Epic Issue → Requirement Issue → Spec Issue → Plan Issue → Task Issues
 * 
 * Each phase has its own Issue that gets assigned to Copilot.
 * This eliminates the need to reopen Issues.
 */

const PHASES = {
  SPEC: 'spec',
  PLAN: 'plan',
  EXECUTION: 'execution'
};

const PHASE_ORDER = [
  PHASES.SPEC,
  PHASES.PLAN,
  PHASES.EXECUTION
];

const PHASE_STATUS = {
  PENDING: 'pending',
  IN_PROGRESS: 'in-progress',
  DONE: 'done',
  FAILED: 'failed',
  SKIPPED: 'skipped',
  CANCELLED: 'cancelled'
};

/**
 * Get the current active phase from state
 * @param {Object} state - Agent state object
 * @returns {string} Current phase name
 */
function getCurrentPhase(state) {
  if (!state.phases) {
    return PHASES.SPEC;
  }
  
  return state.current_phase || PHASES.SPEC;
}

/**
 * Check if a phase can be started
 * @param {Object} state - Agent state object
 * @param {string} phase - Phase to check
 * @returns {boolean} True if phase can start
 */
function canStartPhase(state, phase) {
  if (!state.phases) {
    return phase === PHASES.SPEC;
  }
  
  const phaseIndex = PHASE_ORDER.indexOf(phase);
  if (phaseIndex === -1) {
    return false;
  }
  
  // First phase can always start
  if (phaseIndex === 0) {
    return true;
  }
  
  // Check if previous phase is done
  const previousPhase = PHASE_ORDER[phaseIndex - 1];
  const previousPhaseData = state.phases[previousPhase];
  
  return previousPhaseData && previousPhaseData.status === PHASE_STATUS.DONE;
}

/**
 * Update phase status in state
 * @param {Object} state - Agent state object
 * @param {string} phase - Phase to update
 * @param {string} status - New status
 * @param {Object} data - Additional data to merge
 * @returns {Object} Updated state
 */
function updatePhaseStatus(state, phase, status, data = {}) {
  if (!state.phases) {
    state.phases = initializePhases();
  }
  
  if (!state.phases[phase]) {
    state.phases[phase] = {
      status: PHASE_STATUS.PENDING,
      issue_number: null,
      pr_number: null,
      retry_count: 0,
      started_at: null,
      completed_at: null
    };
  }
  
  state.phases[phase].status = status;
  
  // Update timestamps
  if (status === PHASE_STATUS.IN_PROGRESS && !state.phases[phase].started_at) {
    state.phases[phase].started_at = new Date().toISOString();
  }
  
  if (status === PHASE_STATUS.DONE || status === PHASE_STATUS.FAILED) {
    state.phases[phase].completed_at = new Date().toISOString();
  }
  
  // Merge additional data
  Object.assign(state.phases[phase], data);
  
  if (status === PHASE_STATUS.IN_PROGRESS) {
    state.current_phase = phase;
  }
  
  // Phase transitions are state mutations and must advance revision.
  const baseRevision = Number.isInteger(state.revision) && state.revision > 0 ? state.revision : 0;
  state.revision = baseRevision + 1;
  state.updated_at = new Date().toISOString();
  
  return state;
}

/**
 * Get phase Issue number
 * @param {Object} state - Agent state object
 * @param {string} phase - Phase name
 * @returns {number|null} Issue number or null
 */
function getPhaseIssue(state, phase) {
  if (!state.phases || !state.phases[phase]) {
    return null;
  }
  
  return state.phases[phase].issue_number;
}

/**
 * Check if phase is complete
 * @param {Object} state - Agent state object
 * @param {string} phase - Phase name
 * @returns {boolean} True if phase is done
 */
function isPhaseComplete(state, phase) {
  if (!state.phases || !state.phases[phase]) {
    return false;
  }
  
  return state.phases[phase].status === PHASE_STATUS.DONE;
}

/**
 * Get next phase in sequence
 * @param {string} currentPhase - Current phase name
 * @returns {string|null} Next phase name or null if at end
 */
function getNextPhase(currentPhase) {
  const currentIndex = PHASE_ORDER.indexOf(currentPhase);
  if (currentIndex === -1 || currentIndex === PHASE_ORDER.length - 1) {
    return null;
  }
  
  return PHASE_ORDER[currentIndex + 1];
}

/**
 * Initialize phases structure
 * @returns {Object} Phases object
 */
function initializePhases() {
  const phases = {};
  
  for (const phase of PHASE_ORDER) {
    phases[phase] = {
      status: PHASE_STATUS.PENDING,
      issue_number: null,
      pr_number: null,
      retry_count: 0,
      started_at: null,
      completed_at: null
    };
  }
  
  return phases;
}

/**
 * Get phase progress percentage
 * @param {Object} state - Agent state object
 * @returns {number} Progress percentage (0-100)
 */
function getPhaseProgress(state) {
  if (!state.phases) {
    return 0;
  }
  
  let completedPhases = 0;
  for (const phase of PHASE_ORDER) {
    if (state.phases[phase] && state.phases[phase].status === PHASE_STATUS.DONE) {
      completedPhases++;
    }
  }
  
  return Math.round((completedPhases / PHASE_ORDER.length) * 100);
}

/**
 * Get phase display name (Chinese)
 * @param {string} phase - Phase name
 * @returns {string} Display name
 */
function getPhaseDisplayName(phase) {
  const names = {
    [PHASES.SPEC]: '规格说明',
    [PHASES.PLAN]: '执行计划',
    [PHASES.EXECUTION]: '任务执行'
  };
  
  return names[phase] || phase;
}

module.exports = {
  PHASES,
  PHASE_ORDER,
  PHASE_STATUS,
  getCurrentPhase,
  canStartPhase,
  updatePhaseStatus,
  getPhaseIssue,
  isPhaseComplete,
  getNextPhase,
  initializePhases,
  getPhaseProgress,
  getPhaseDisplayName
};
