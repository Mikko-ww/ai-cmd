#!/usr/bin/env node

const core = require('@actions/core');
const fs = require('fs');
const path = require('path');
const { loadPlanOrFail, formatValidationError, PlanValidationError } = require('./lib/plan-contract');

function parseArgs(argv) {
  const args = {
    file: '',
    mode: 'strict',
    format: 'text',
    report: ''
  };

  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--file') {
      args.file = argv[index + 1] || '';
      index += 1;
    } else if (token === '--mode') {
      args.mode = argv[index + 1] || 'strict';
      index += 1;
    } else if (token === '--strict') {
      args.mode = 'strict';
    } else if (token === '--format') {
      args.format = argv[index + 1] || 'text';
      index += 1;
    } else if (token === '--report') {
      args.report = argv[index + 1] || '';
      index += 1;
    }
  }

  return args;
}

function writeReport(reportPath, payload) {
  if (!reportPath) {
    return;
  }

  const dir = path.dirname(reportPath);
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(reportPath, `${JSON.stringify(payload, null, 2)}\n`);
}

function renderFailure(errorPayload, format) {
  if (format === 'json') {
    return JSON.stringify(errorPayload, null, 2);
  }

  if (format === 'copilot') {
    return [
      'Plan validation failed.',
      `- Code: ${errorPayload.code}`,
      `- Path: ${errorPayload.path}`,
      `- Message: ${errorPayload.message}`,
      errorPayload.hint ? `- Hint: ${errorPayload.hint}` : ''
    ].filter(Boolean).join('\n');
  }

  return `${errorPayload.code} at ${errorPayload.path}: ${errorPayload.message}${errorPayload.hint ? ` (${errorPayload.hint})` : ''}`;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));

  if (!args.file) {
    core.setFailed('Missing required argument: --file <plan-yaml-path>');
    process.exit(1);
  }

  try {
    const plan = loadPlanOrFail(args.file, { mode: args.mode });
    const summary = {
      ok: true,
      file: args.file,
      mode: args.mode,
      taskCount: plan.tasks.length
    };

    writeReport(args.report, summary);

    core.setOutput('valid', 'true');
    core.setOutput('task_count', String(plan.tasks.length));
    core.info(`Plan validation passed: ${args.file} (${plan.tasks.length} tasks)`);

    if (args.format === 'json') {
      core.info(JSON.stringify(summary, null, 2));
    } else if (args.format === 'copilot') {
      core.info(`Plan validation passed. File: ${args.file}. Tasks: ${plan.tasks.length}.`);
    }
  } catch (error) {
    const payload = formatValidationError(error);
    writeReport(args.report, payload);

    core.setOutput('valid', 'false');
    core.setOutput('error_code', payload.code || 'PLAN_UNKNOWN_ERROR');
    core.setOutput('error_path', payload.path || '/');

    const rendered = renderFailure(payload, args.format);

    if (!(error instanceof PlanValidationError)) {
      core.error(error.stack || error.message);
    }

    core.setFailed(rendered);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = {
  parseArgs,
  renderFailure,
  main
};
