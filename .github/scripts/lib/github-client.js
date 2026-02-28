#!/usr/bin/env node

const { Octokit } = require('@octokit/rest');
const core = require('@actions/core');

class GitHubClient {
  constructor(token, owner, repo) {
    this._octokit = new Octokit({ auth: token });
    this.owner = owner;
    this.repo = repo;
  }

  async getIssue(issueNumber) {
    try {
      const { data } = await this._octokit.rest.issues.get({
        owner: this.owner,
        repo: this.repo,
        issue_number: issueNumber
      });
      return data;
    } catch (error) {
      core.error(`Failed to get issue #${issueNumber}: ${error.message}`);
      throw error;
    }
  }

  async createComment(issueNumber, body) {
    try {
      const { data } = await this._octokit.rest.issues.createComment({
        owner: this.owner,
        repo: this.repo,
        issue_number: issueNumber,
        body
      });
      return data;
    } catch (error) {
      core.error(`Failed to create comment on issue #${issueNumber}: ${error.message}`);
      throw error;
    }
  }

  async addLabels(issueNumber, labels) {
    try {
      const { data } = await this._octokit.rest.issues.addLabels({
        owner: this.owner,
        repo: this.repo,
        issue_number: issueNumber,
        labels
      });
      return data;
    } catch (error) {
      core.error(`Failed to add labels to issue #${issueNumber}: ${error.message}`);
      throw error;
    }
  }

  async removeLabel(issueNumber, label) {
    try {
      await this._octokit.rest.issues.removeLabel({
        owner: this.owner,
        repo: this.repo,
        issue_number: issueNumber,
        name: label
      });
    } catch (error) {
      if (error.status !== 404) {
        core.error(`Failed to remove label from issue #${issueNumber}: ${error.message}`);
        throw error;
      }
    }
  }

  async updateIssue(issueNumber, updates) {
    try {
      const { data } = await this._octokit.rest.issues.update({
        owner: this.owner,
        repo: this.repo,
        issue_number: issueNumber,
        ...updates
      });
      return data;
    } catch (error) {
      core.error(`Failed to update issue #${issueNumber}: ${error.message}`);
      throw error;
    }
  }

  async createPR(title, head, base, body) {
    try {
      const { data } = await this._octokit.rest.pulls.create({
        owner: this.owner,
        repo: this.repo,
        title,
        head,
        base,
        body
      });
      return data;
    } catch (error) {
      core.error(`Failed to create PR: ${error.message}`);
      throw error;
    }
  }

  async mergePR(prNumber, mergeMethod = 'squash') {
    try {
      const { data } = await this._octokit.rest.pulls.merge({
        owner: this.owner,
        repo: this.repo,
        pull_number: prNumber,
        merge_method: mergeMethod
      });
      return data;
    } catch (error) {
      core.error(`Failed to merge PR #${prNumber}: ${error.message}`);
      throw error;
    }
  }

  async listComments(issueNumber, perPage = 100) {
    try {
      const comments = await this._octokit.paginate(
        this._octokit.rest.issues.listComments,
        {
          owner: this.owner,
          repo: this.repo,
          issue_number: issueNumber,
          per_page: perPage
        }
      );
      return comments;
    } catch (error) {
      core.error(`Failed to list comments for issue #${issueNumber}: ${error.message}`);
      throw error;
    }
  }

  async getPR(prNumber) {
    try {
      const { data } = await this._octokit.rest.pulls.get({
        owner: this.owner,
        repo: this.repo,
        pull_number: prNumber
      });
      return data;
    } catch (error) {
      core.error(`Failed to get PR #${prNumber}: ${error.message}`);
      throw error;
    }
  }

  async listPRFiles(prNumber, perPage = 100) {
    try {
      const files = await this._octokit.paginate(
        this._octokit.rest.pulls.listFiles,
        {
          owner: this.owner,
          repo: this.repo,
          pull_number: prNumber,
          per_page: perPage
        }
      );
      return files;
    } catch (error) {
      core.error(`Failed to list files for PR #${prNumber}: ${error.message}`);
      throw error;
    }
  }

  async createWorkflowDispatch(workflowId, ref, inputs = {}) {
    try {
      await this._octokit.rest.actions.createWorkflowDispatch({
        owner: this.owner,
        repo: this.repo,
        workflow_id: workflowId,
        ref,
        inputs
      });
    } catch (error) {
      core.error(`Failed to dispatch workflow ${workflowId}: ${error.message}`);
      throw error;
    }
  }

  async createCheckRun(name, headSha, status, output = {}) {
    try {
      const { data } = await this._octokit.rest.checks.create({
        owner: this.owner,
        repo: this.repo,
        name,
        head_sha: headSha,
        status,
        started_at: new Date().toISOString(),
        output
      });
      return data;
    } catch (error) {
      core.error(`Failed to create check run: ${error.message}`);
      throw error;
    }
  }

  async updateCheckRun(checkRunId, status, conclusion, output = {}) {
    try {
      const params = {
        owner: this.owner,
        repo: this.repo,
        check_run_id: checkRunId,
        status
      };

      if (status === 'completed') {
        params.conclusion = conclusion;
        params.completed_at = new Date().toISOString();
      }

      if (output && Object.keys(output).length > 0) {
        params.output = output;
      }

      const { data } = await this._octokit.rest.checks.update(params);
      return data;
    } catch (error) {
      core.error(`Failed to update check run #${checkRunId}: ${error.message}`);
      throw error;
    }
  }

  // ============================================================================
  // NEW METHODS - Wave 2: Core Implementation
  // ============================================================================

  // Issue Operations
  // ----------------------------------------------------------------------------

  async listIssues(filters = {}) {
    try {
      const issues = await this._octokit.paginate(
        this._octokit.rest.issues.listForRepo,
        {
          owner: this.owner,
          repo: this.repo,
          per_page: 100,
          ...filters
        }
      );
      return issues;
    } catch (error) {
      core.error(`Failed to list issues: ${error.message}`);
      throw error;
    }
  }

  async createIssue(title, body, labels = [], assignees = []) {
    try {
      const { data } = await this._octokit.rest.issues.create({
        owner: this.owner,
        repo: this.repo,
        title,
        body,
        labels,
        assignees
      });
      return data;
    } catch (error) {
      core.error(`Failed to create issue: ${error.message}`);
      throw error;
    }
  }

  // PR Operations
  // ----------------------------------------------------------------------------

  async listPRs(filters = {}) {
    try {
      const prs = await this._octokit.paginate(
        this._octokit.rest.pulls.list,
        {
          owner: this.owner,
          repo: this.repo,
          per_page: 100,
          ...filters
        });
      return prs;
    } catch (error) {
      core.error(`Failed to list PRs: ${error.message}`);
      throw error;
    }
  }

  // Label Operations
  // ----------------------------------------------------------------------------

  async listLabels(perPage = 100) {
    try {
      const labels = await this._octokit.paginate(
        this._octokit.rest.issues.listLabelsForRepo,
        {
          owner: this.owner,
          repo: this.repo,
          per_page: perPage
        }
      );
      return labels;
    } catch (error) {
      core.error(`Failed to list labels: ${error.message}`);
      throw error;
    }
  }

  async createLabel(name, color, description = '') {
    try {
      const { data } = await this._octokit.rest.issues.createLabel({
        owner: this.owner,
        repo: this.repo,
        name,
        color,
        description
      });
      return data;
    } catch (error) {
      core.error(`Failed to create label "${name}": ${error.message}`);
      throw error;
    }
  }

  async updateLabel(name, updates = {}) {
    try {
      const params = {
        owner: this.owner,
        repo: this.repo,
        name
      };

      if (updates.newName) {
        params.new_name = updates.newName;
      }
      if (updates.color) {
        params.color = updates.color;
      }
      if (updates.description !== undefined) {
        params.description = updates.description;
      }

      const { data } = await this._octokit.rest.issues.updateLabel(params);
      return data;
    } catch (error) {
      core.error(`Failed to update label "${name}": ${error.message}`);
      throw error;
    }
  }

  async deleteLabel(name) {
    try {
      await this._octokit.rest.issues.deleteLabel({
        owner: this.owner,
        repo: this.repo,
        name
      });
    } catch (error) {
      if (error.status !== 404) {
        core.error(`Failed to delete label "${name}": ${error.message}`);
        throw error;
      }
    }
  }

  // Check Run Operations
  // ----------------------------------------------------------------------------

  async listCheckRuns(ref, checkName = null) {
    try {
      const params = {
        owner: this.owner,
        repo: this.repo,
        ref,
        per_page: 100
      };

      if (checkName) {
        params.check_name = checkName;
      }

      const checkRuns = await this._octokit.paginate(
        this._octokit.rest.checks.listForRef,
        params
      );
      return checkRuns;
    } catch (error) {
      core.error(`Failed to list check runs for ref ${ref}: ${error.message}`);
      throw error;
    }
  }

  // Git Data API Operations
  // ----------------------------------------------------------------------------

  async getRef(ref) {
    try {
      const { data } = await this._octokit.rest.git.getRef({
        owner: this.owner,
        repo: this.repo,
        ref
      });
      return data;
    } catch (error) {
      core.error(`Failed to get ref ${ref}: ${error.message}`);
      throw error;
    }
  }

  async createRef(ref, sha) {
    try {
      const { data } = await this._octokit.rest.git.createRef({
        owner: this.owner,
        repo: this.repo,
        ref,
        sha
      });
      return data;
    } catch (error) {
      core.error(`Failed to create ref ${ref}: ${error.message}`);
      throw error;
    }
  }

  async updateRef(ref, sha, force = false) {
    try {
      const { data } = await this._octokit.rest.git.updateRef({
        owner: this.owner,
        repo: this.repo,
        ref,
        sha,
        force
      });
      return data;
    } catch (error) {
      core.error(`Failed to update ref ${ref}: ${error.message}`);
      throw error;
    }
  }

  async createBlob(content, encoding = 'utf-8') {
    try {
      const { data } = await this._octokit.rest.git.createBlob({
        owner: this.owner,
        repo: this.repo,
        content,
        encoding
      });
      return data;
    } catch (error) {
      core.error(`Failed to create blob: ${error.message}`);
      throw error;
    }
  }

  async getTree(treeSha, recursive = false) {
    try {
      const { data } = await this._octokit.rest.git.getTree({
        owner: this.owner,
        repo: this.repo,
        tree_sha: treeSha,
        recursive: recursive ? 'true' : undefined
      });
      return data;
    } catch (error) {
      core.error(`Failed to get tree ${treeSha}: ${error.message}`);
      throw error;
    }
  }

  async createTree(tree, baseTree = null) {
    try {
      const params = {
        owner: this.owner,
        repo: this.repo,
        tree
      };

      if (baseTree) {
        params.base_tree = baseTree;
      }

      const { data } = await this._octokit.rest.git.createTree(params);
      return data;
    } catch (error) {
      core.error(`Failed to create tree: ${error.message}`);
      throw error;
    }
  }

  async createCommit(message, tree, parents) {
    try {
      const { data } = await this._octokit.rest.git.createCommit({
        owner: this.owner,
        repo: this.repo,
        message,
        tree,
        parents
      });
      return data;
    } catch (error) {
      core.error(`Failed to create commit: ${error.message}`);
      throw error;
    }
  }

  /**
   * High-level method to commit files to branch using Git Data API
   * Abstracts the 7-step process: getRef → createBlob (for each file) → 
   * getTree → createTree → createCommit → updateRef
   * 
   * @param {string} branch - Branch name (e.g., 'main', 'feature/new-feature')
   * @param {string} message - Commit message
   * @param {Array<{path: string, content: string, encoding?: string}>} files - Files to commit
   * @param {string} baseBranch - Base branch to create from (optional, defaults to branch)
   * @returns {Promise<Object>} Commit data
   */
  async commitFiles(branch, message, files, baseBranch = null) {
    try {
      // Step 1: Get the reference to base branch
      const refName = baseBranch || branch;
      const ref = await this.getRef(`heads/${refName}`);
      const baseSha = ref.object.sha;

      // Step 2: Get the base tree
      const baseCommit = await this._octokit.rest.git.getCommit({
        owner: this.owner,
        repo: this.repo,
        commit_sha: baseSha
      });
      const baseTreeSha = baseCommit.data.tree.sha;

      // Step 3: Create blobs for each file
      const blobs = await Promise.all(
        files.map(async (file) => {
          const blob = await this.createBlob(file.content, file.encoding || 'utf-8');
          return {
            path: file.path,
            mode: '100644',
            type: 'blob',
            sha: blob.sha
          };
        })
      );

      // Step 4: Create a new tree with the blobs
      const tree = await this.createTree(blobs, baseTreeSha);

      // Step 5: Create a new commit
      const commit = await this.createCommit(message, tree.sha, [baseSha]);

      // Step 6: Update the branch reference
      // If baseBranch is different from branch, create a new ref
      if (baseBranch && baseBranch !== branch) {
        await this.createRef(`refs/heads/${branch}`, commit.sha);
      } else {
        await this.updateRef(`heads/${branch}`, commit.sha);
      }

      return commit;
    } catch (error) {
      core.error(`Failed to commit files to branch ${branch}: ${error.message}`);
      throw error;
    }
  }

  // Repository Operations
  // ----------------------------------------------------------------------------

  async getRepo() {
    try {
      const { data } = await this._octokit.rest.repos.get({
        owner: this.owner,
        repo: this.repo
      });
      return data;
    } catch (error) {
      core.error(`Failed to get repository: ${error.message}`);
      throw error;
    }
  }

  async updateRepo(updates = {}) {
    try {
      const { data } = await this._octokit.rest.repos.update({
        owner: this.owner,
        repo: this.repo,
        ...updates
      });
      return data;
    } catch (error) {
      core.error(`Failed to update repository: ${error.message}`);
      throw error;
    }
  }

  // Secrets Operations
  // ----------------------------------------------------------------------------

  async getRepoPublicKey() {
    try {
      const { data } = await this._octokit.rest.actions.getRepoPublicKey({
        owner: this.owner,
        repo: this.repo
      });
      return data;
    } catch (error) {
      core.error(`Failed to get repository public key: ${error.message}`);
      throw error;
    }
  }

  async createOrUpdateRepoSecret(name, encryptedValue, keyId) {
    try {
      await this._octokit.rest.actions.createOrUpdateRepoSecret({
        owner: this.owner,
        repo: this.repo,
        secret_name: name,
        encrypted_value: encryptedValue,
        key_id: keyId
      });
    } catch (error) {
      core.error(`Failed to create/update secret "${name}": ${error.message}`);
      throw error;
    }
  }

  // Utility
  // ----------------------------------------------------------------------------

  /**
   * Expose octokit.paginate for advanced use cases
   * @param {Function} method - Octokit method to paginate
   * @param {Object} params - Parameters for the method
   * @returns {Promise<Array>} Paginated results
   */
  async paginate(method, params) {
    try {
      return await this._octokit.paginate(method, params);
    } catch (error) {
      core.error(`Failed to paginate: ${error.message}`);
      throw error;
    }
  }
}

module.exports = { GitHubClient };
