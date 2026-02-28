# Task: Generate Execution Plan (执行计划)

Create a detailed execution plan with task breakdown.

## Requirements:
1. Create YAML: `{{planYamlDir}}/issue-{{epicNumber}}.yaml`
2. Create Markdown: `{{planMdDir}}/issue-{{epicNumber}}.md`
3. Follow template: `auto-agent/docs/PLAN_TEMPLATE.md`
4. Include task breakdown with risk levels (`l1`/`l2`/`l3`)
5. Write in Chinese (中文)

## Model Selection

- Requirement/spec preferred model: `{{requirementModel}}`
- Default task fallback model: `{{defaultModel}}`
- Available model options and capabilities:
{{modelCatalogText}}
- Each task in YAML MUST include a `model` field selected from the list above.

## Task Count Control:

- Task count control from parent Epic request.
- Read task-count preferences from parent Epic description fields:
  - `计划任务数（期望）` (form id: `plan-task-target`)
  - `最大任务条数` (form id: `plan-task-max`)
- Desired task count default: 5
- Maximum task count default: 8
- If values are missing, invalid, or `target > max`, fallback to defaults.
- The generated tasks array length MUST be <= maximum task count.
- Keep the task count close to desired task count while preserving delivery quality.

## YAML Contract (STRICT):

- YAML keys MUST be machine keys in English.
- Do NOT use aliases such as `dependencies`, `acceptance_criteria`, `risk_level`.
- Do NOT use Chinese keys such as `依赖`, `验收标准`, `风险等级`.
- Required root field: `tasks`.
- Required task fields: `id`, `title`, `level`, `deps`, `acceptance`, `model`.
- Allowed task levels: `l1`, `l2`, `l3`.
- `deps` MUST be an array of task ids. Use `[]` when no dependency exists.
- Runtime fields (`status`, `issue`, `pr`) are managed by agent state and MUST NOT appear in plan YAML.

Minimum valid YAML example:

```yaml
tasks:
  - id: task-setup-env
    title: "初始化项目环境"
    level: l1
    deps: []
    acceptance: "项目结构创建完成并可安装依赖"
    model: "auto"
    notes: "可选"
```

Before commit and PR, you MUST run validation and fix all errors until it passes:

```bash
node .github/scripts/validate-plan.js --file {{planYamlDir}}/issue-{{epicNumber}}.yaml --strict --format copilot
```

If validation fails, do NOT commit. Fix YAML and rerun validation.

## PR Requirements:
1. Title: "[Plan] Epic #{{epicNumber}}: <description>"
2. Body must include:
   ```
   <!-- agent-markers:start -->
   Agent-Schema-Version: 2
   Agent-Parent-Issue: {{epicNumber}}
   Agent-PR-Type: plan
   Agent-Phase-Name: plan
   <!-- agent-markers:end -->
   ```
3. Target branch: {{baseBranch}}
