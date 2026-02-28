// Phase constants
const PHASE_LABELS = {
  SPEC: 'agent:phase:spec',
  PLAN: 'agent:phase:plan'
};

const PHASES = ['spec', 'plan', 'execution'];

const PHASE_EMOJIS = {
  spec: '📐',
  plan: '🗺️',
  execution: '⚙️'
};

const PHASE_DISPLAY_NAMES = {
  spec: '规格说明',
  plan: '执行计划',
  execution: '任务执行'
};

module.exports = {
  PHASE_LABELS,
  PHASES,
  PHASE_EMOJIS,
  PHASE_DISPLAY_NAMES
};
