#!/usr/bin/env node

const core = require('@actions/core');
const { PHASE_ORDER, PHASE_STATUS, getPhaseDisplayName, getPhaseProgress } = require('./phase-manager');

async function updateEpicProgress(github, epicIssueNumber, state) {
  const issue = await github.getIssue(epicIssueNumber);
  
  const progressSection = renderProgressSection(state);
  const updatedBody = replaceProgressSection(issue.body, progressSection);
  
  await github.updateIssue(epicIssueNumber, { body: updatedBody });
  
  core.info(`Updated Epic Issue #${epicIssueNumber} progress`);
}

function renderProgressSection(state) {
  const progressBar = renderProgressBar(state);
  const tasklist = renderTasklist(state);
  const phaseTable = renderPhaseTable(state);
  
  return [
    '<!-- agent-progress:start -->',
    '',
    '## 📊 Progress',
    '',
    progressBar,
    '',
    tasklist,
    '',
    phaseTable,
    '',
    '<!-- agent-progress:end -->'
  ].join('\n');
}

function renderProgressBar(state) {
  const progress = getPhaseProgress(state);
  const filled = Math.floor(progress / 5);
  const empty = 20 - filled;
  
  const bar = '█'.repeat(filled) + '░'.repeat(empty);
  
  return `**Progress:** ${progress}% [${bar}]`;
}

function renderTasklist(state) {
  if (!state.phases) {
    return '';
  }
  
  const items = PHASE_ORDER.map(phase => {
    const phaseData = state.phases[phase];
    const displayName = getPhaseDisplayName(phase);
    const status = phaseData ? phaseData.status : PHASE_STATUS.PENDING;
    const issueNumber = phaseData ? phaseData.issue_number : null;
    
    let checkbox = '- [ ]';
    let statusEmoji = '⏳';
    
    if (status === PHASE_STATUS.DONE) {
      checkbox = '- [x]';
      statusEmoji = '✅';
    } else if (status === PHASE_STATUS.IN_PROGRESS) {
      checkbox = '- [ ]';
      statusEmoji = '🔄';
    } else if (status === PHASE_STATUS.FAILED) {
      checkbox = '- [ ]';
      statusEmoji = '❌';
    }
    
    const issueLink = issueNumber ? ` (#${issueNumber})` : '';
    
    return `${checkbox} ${statusEmoji} ${displayName}${issueLink}`;
  });
  
  return items.join('\n');
}

function renderPhaseTable(state) {
  if (!state.phases) {
    return '';
  }
  
  const rows = ['| Phase | Status | Issue | PR | Retry |', '|-------|--------|-------|----|----|'];
  
  for (const phase of PHASE_ORDER) {
    const phaseData = state.phases[phase];
    const displayName = getPhaseDisplayName(phase);
    
    if (!phaseData) {
      rows.push(`| ${displayName} | ⏳ Pending | - | - | - |`);
      continue;
    }
    
    const statusEmoji = getStatusEmoji(phaseData.status);
    const statusText = `${statusEmoji} ${phaseData.status}`;
    const issueLink = phaseData.issue_number ? `#${phaseData.issue_number}` : '-';
    const prLink = phaseData.pr_number ? `#${phaseData.pr_number}` : '-';
    const retryCount = phaseData.retry_count || 0;
    const retryText = retryCount > 0 ? `${retryCount}/3` : '-';
    
    rows.push(`| ${displayName} | ${statusText} | ${issueLink} | ${prLink} | ${retryText} |`);
  }
  
  return rows.join('\n');
}

function getStatusEmoji(status) {
  const emojis = {
    [PHASE_STATUS.PENDING]: '⏳',
    [PHASE_STATUS.IN_PROGRESS]: '🔄',
    [PHASE_STATUS.DONE]: '✅',
    [PHASE_STATUS.FAILED]: '❌'
  };
  
  return emojis[status] || '❓';
}

function replaceProgressSection(body, newProgressSection) {
  const startMarker = '<!-- agent-progress:start -->';
  const endMarker = '<!-- agent-progress:end -->';
  
  if (!body) {
    return newProgressSection;
  }
  
  const startIndex = body.indexOf(startMarker);
  const endIndex = body.indexOf(endMarker);
  
  if (startIndex === -1 || endIndex === -1) {
    return body + '\n\n' + newProgressSection;
  }
  
  const before = body.substring(0, startIndex);
  const after = body.substring(endIndex + endMarker.length);
  
  return before + newProgressSection + after;
}

module.exports = {
  updateEpicProgress,
  renderProgressBar,
  renderTasklist,
  renderPhaseTable
};
