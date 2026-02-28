#!/usr/bin/env node

const core = require('@actions/core');
const fs = require('fs');
const yaml = require('js-yaml');
const { GitHubClient } = require('./lib/github-client');
const { loadConfig } = require('./lib/config-loader');

async function main() {
  try {
    const token = process.env.GITHUB_TOKEN;
    const [owner, repo] = process.env.GITHUB_REPOSITORY.split('/');
    const dryRun = process.env.DRY_RUN === 'true';

    if (!token || !owner || !repo) {
      core.setFailed('Missing required environment variables');
      return;
    }

    const github = new GitHubClient(token, owner, repo);
    const config = loadConfig();

    if (dryRun) {
      core.info('🔍 Running in DRY RUN mode - no changes will be made');
    }

    const labelsConfigPath = '.github/agent/labels.json';
    if (!fs.existsSync(labelsConfigPath)) {
      core.setFailed(`Labels config not found at: ${labelsConfigPath}`);
      return;
    }

    const labelsConfig = JSON.parse(fs.readFileSync(labelsConfigPath, 'utf8'));
    const labelsFromConfig = labelsConfig.labels;
    const locale = process.env.AGENT_LABEL_LOCALE || 'en';
    
    core.info(`Using locale: ${locale}`);
    core.info(`Loaded ${labelsFromConfig.length} labels from config`);

    const labelColors = {};
    const labelDescriptions = {};
    
    for (const label of labelsFromConfig) {
      labelColors[label.name] = label.color;
      labelDescriptions[label.name] = label.descriptions[locale] || label.descriptions['en'];
    }

    const allLabels = new Set();

    function collectLabels(obj) {
      for (const key in obj) {
        if (typeof obj[key] === 'string') {
          allLabels.add(obj[key]);
        } else if (typeof obj[key] === 'object') {
          collectLabels(obj[key]);
        }
      }
    }

    collectLabels(config.labels);

    const existingLabels = await github.listLabels(100);

    const existingLabelMap = new Map(
      existingLabels.map(label => [label.name, label])
    );

    let created = 0;
    let updated = 0;
    let skipped = 0;

    for (const labelName of allLabels) {
      const color = labelColors[labelName] || 'EDEDED';
      const description = labelDescriptions[labelName] || '';

      const existing = existingLabelMap.get(labelName);

      if (!existing) {
        if (dryRun) {
          core.info(`[DRY RUN] Would create label: ${labelName}`);
        } else {
          await github.createLabel(labelName, color, description);
          core.info(`✓ Created label: ${labelName}`);
        }
        created++;
      } else if (existing.color !== color || existing.description !== description) {
        if (dryRun) {
          core.info(`[DRY RUN] Would update label: ${labelName}`);
          if (existing.color !== color) {
            core.info(`  Color: ${existing.color} → ${color}`);
          }
          if (existing.description !== description) {
            core.info(`  Description: "${existing.description}" → "${description}"`);
          }
        } else {
          await github.updateLabel(labelName, {
            color: color,
            description: description
          });
          core.info(`✓ Updated label: ${labelName}`);
        }
        updated++;
      } else {
        core.info(`- Skipped label (already exists): ${labelName}`);
        skipped++;
      }
    }

    const mode = dryRun ? ' (DRY RUN)' : '';
    core.info(`\nSummary${mode}:`);
    core.info(`  Created: ${created}`);
    core.info(`  Updated: ${updated}`);
    core.info(`  Skipped: ${skipped}`);
    core.info(`  Total: ${allLabels.size}`);

    if (dryRun) {
      core.summary
        .addHeading('Label Bootstrap Check (Dry Run)')
        .addRaw('ℹ️ This was a dry run. No labels were created or modified.\n\n')
        .addTable([
          [{data: 'Status', header: true}, {data: 'Count', header: true}],
          ['Would Create', created.toString()],
          ['Would Update', updated.toString()],
          ['Already Correct', skipped.toString()],
          ['Total Labels', allLabels.size.toString()]
        ])
        .write();
    } else {
      core.summary
        .addHeading('Label Bootstrap Complete')
        .addTable([
          [{data: 'Status', header: true}, {data: 'Count', header: true}],
          ['Created', created.toString()],
          ['Updated', updated.toString()],
          ['Skipped', skipped.toString()],
          ['Total', allLabels.size.toString()]
        ])
        .write();
    }
  } catch (error) {
    core.setFailed(error.message);
    process.exit(1);
  }
}

main();
