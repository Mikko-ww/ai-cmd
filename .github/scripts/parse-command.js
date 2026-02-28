#!/usr/bin/env node

const core = require('@actions/core');

async function main() {
  try {
    const commentBody = process.env.COMMENT_BODY;

    if (!commentBody) {
      core.setFailed('Missing COMMENT_BODY environment variable');
      return;
    }

    const comment = commentBody.trim();
    const commandLine = comment.split('\n')[0].trim();

    let command = null;
    if (commandLine === '/approve-task') command = 'approve-task';
    else if (commandLine === '/pause') command = 'pause';
    else if (commandLine === '/resume') command = 'resume';
    else if (commandLine === '/retry') command = 'retry';
    else if (commandLine === '/skip-phase') command = 'skip-phase';
    else if (commandLine === '/cancel-phase') command = 'cancel-phase';
    else if (commandLine === '/reopen') command = 'reopen';
    else if (commandLine === '/abort') command = 'abort';

    core.setOutput('command', command || '');
    core.info(`✓ Parsed command: ${command || 'none'}`);
  } catch (error) {
    core.setFailed(error.message);
    process.exit(1);
  }
}

main();
