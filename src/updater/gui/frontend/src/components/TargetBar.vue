<template>
  <div class="target-bar">
    <div class="target-info">
      <div class="target-row">
        <span class="target-label">專案:</span>
        <span class="target-path" :title="store.target.project || ''">
          {{ store.target.project || '（未解析）' }}
          <span v-if="store.target.project_saved" class="target-meta">（已保存）</span>
        </span>
      </div>
      <div class="target-row">
        <span class="target-label">venv:</span>
        <span class="target-path" :title="store.target.venv || ''">
          {{ store.target.venv || '未找到' }}
        </span>
      </div>
      <div class="target-row">
        <span class="target-label">source:</span>
        <span class="target-path" :title="sourceTitle">
          {{ store.target.source || '（未設定）' }}
          <span v-if="store.target.source_origin" class="target-meta">
            （{{ store.target.source_origin }}）
          </span>
        </span>
      </div>
      <div v-if="store.target.config_origin" class="target-row">
        <span class="target-label">設定:</span>
        <span
          class="target-origin"
          :class="store.target.config_origin === 'project' ? 'from-project' : 'from-exe'"
          :title="store.target.config"
        >
          {{ store.target.config_origin }} — {{ store.target.config }}
        </span>
      </div>
    </div>

    <div class="target-controls">
      <div class="control-row">
        <span class="control-label">專案資料夾</span>
        <input
          v-model="draft"
          class="target-input"
          type="text"
          placeholder="要更新的專案資料夾"
          :title="draft"
          @keyup.enter="apply"
        />
        <button class="btn btn-small btn-apply" :disabled="busy || !draft" @click="apply">
          套用
        </button>
        <button class="btn btn-small btn-browse" :disabled="busy" @click="browse">
          瀏覽…
        </button>
        <button
          class="btn btn-small btn-reset-target"
          :disabled="busy || !store.target.project_saved"
          title="清除已保存的專案資料夾，改回自動解析（updater_state.toml）"
          @click="resetTarget"
        >
          還原自動
        </button>
      </div>
      <div class="control-row">
        <span class="control-label">packages 來源</span>
        <input
          v-model="sourceDraft"
          class="source-input"
          type="text"
          placeholder="放 .whl 的資料夾"
          :title="sourceDraft"
          @keyup.enter="applySource"
        />
        <button
          class="btn btn-small btn-apply-source"
          :disabled="busy || !sourceDraft"
          @click="applySource"
        >
          套用
        </button>
        <button class="btn btn-small btn-browse-source" :disabled="busy" @click="browseSource">
          瀏覽…
        </button>
        <button
          class="btn btn-small btn-reset-source"
          :disabled="busy || !store.target.source_saved"
          title="清除已保存的 packages 來源，改回自動解析（toml → updater 上一層 → 內建）"
          @click="resetSource"
        >
          還原自動
        </button>
      </div>
    </div>

    <div v-if="error" class="target-error">{{ error }}</div>
    <div v-if="store.target.error" class="target-error">{{ store.target.error }}</div>
    <div v-if="store.target.source_error" class="target-error">
      {{ store.target.source_error }}
    </div>
    <div v-if="store.target.config_error" class="target-error warn">
      {{ store.target.config_error }}
      <span v-if="store.target.encoding" class="target-meta">
        （編碼: {{ store.target.encoding }}）
      </span>
    </div>
  </div>
</template>

<script setup>
import { computed, inject, ref, watch } from 'vue'

const store = inject('store')
const reloadTarget = inject('reloadTarget')

const draft = ref('')
const sourceDraft = ref('')
const busy = ref(false)
const error = ref('')

const sourceTitle = computed(
  () => `${store.target.source || ''}\n由 ${store.target.source_origin || '未知'} 提供`
)

// Prefill once the backend reports the resolved target (arrives after mount).
watch(
  () => store.target.project,
  (project) => {
    if (!draft.value && project) draft.value = project
  },
  { immediate: true }
)
watch(
  () => store.target.source,
  (source) => {
    if (!sourceDraft.value && source) sourceDraft.value = source
  },
  { immediate: true }
)

async function applyPath(path, apiMethod, onApplied) {
  if (!window.pywebview) return
  busy.value = true
  error.value = ''
  try {
    const result = await window.pywebview.api[apiMethod](path)
    if (result.error) {
      error.value = result.error
      return
    }
    store.target = result.target
    onApplied(result.target)
    if (reloadTarget) await reloadTarget()
  } catch (err) {
    error.value = String(err)
  } finally {
    busy.value = false
  }
}

function apply() {
  if (draft.value.trim()) {
    applyPath(draft.value.trim(), 'set_target', (target) => {
      draft.value = target.project
    })
  }
}

function applySource() {
  if (sourceDraft.value.trim()) {
    applyPath(sourceDraft.value.trim(), 'set_source', (target) => {
      sourceDraft.value = target.source
    })
  }
}

// A dialog the backend could not open reports a reason (spec section 3); a plain
// user cancel stays silent.
function handleCancelled(result) {
  if (result.reason) {
    error.value = `無法開啟資料夾對話框：${result.reason}；請手動輸入路徑後按「套用」`
  }
}

async function pickFolder(apiMethod, onApplied) {
  if (!window.pywebview) return
  busy.value = true
  error.value = ''
  try {
    const result = await window.pywebview.api[apiMethod]()
    if (result.cancelled) {
      handleCancelled(result)
      return
    }
    if (result.error) {
      error.value = result.error
      return
    }
    store.target = result.target
    onApplied(result.target)
    if (reloadTarget) await reloadTarget()
  } catch (err) {
    error.value = String(err)
  } finally {
    busy.value = false
  }
}

function browse() {
  pickFolder('choose_target_folder', (target) => {
    draft.value = target.project
  })
}

function browseSource() {
  pickFolder('choose_source_folder', (target) => {
    sourceDraft.value = target.source
  })
}

// 還原自動: drop the saved choice so the automatic chain takes over again
// (spec section 3.3.5).  The drafts follow the newly resolved values.
async function clearOverride(apiMethod, onCleared) {
  if (!window.pywebview) return
  busy.value = true
  error.value = ''
  try {
    const result = await window.pywebview.api[apiMethod]()
    if (result.error) {
      error.value = result.error
      return
    }
    store.target = result.target
    onCleared(result.target)
    if (reloadTarget) await reloadTarget()
  } catch (err) {
    error.value = String(err)
  } finally {
    busy.value = false
  }
}

function resetTarget() {
  clearOverride('clear_target', (target) => {
    draft.value = target.project || ''
  })
}

function resetSource() {
  clearOverride('clear_source', (target) => {
    sourceDraft.value = target.source || ''
  })
}
</script>

<style scoped>
/* Spec: docs/specs/gui_folder_dialog_spec.md section 3.1 - one row per path.
   A grid (info | controls) with each path in its own label/value row: three long
   paths must never run into each other, not even at the window's minimum width. */
.target-bar {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: start;
  gap: 8px 16px;
  padding: 8px 20px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border-color);
  font-size: 12px;
}

.target-info {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.target-row {
  display: grid;
  grid-template-columns: 56px minmax(0, 1fr);
  align-items: baseline;
  gap: 8px;
  min-width: 0;
}

.target-label {
  color: var(--text-secondary);
  font-weight: 600;
  white-space: nowrap;
}

.target-path {
  font-family: var(--font-mono);
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}

.target-meta {
  font-family: var(--font-mono);
  color: var(--text-secondary);
  white-space: nowrap;
}

.target-origin {
  padding: 1px 6px;
  border-radius: 3px;
  font-size: 11px;
  justify-self: start;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.from-project {
  background: var(--accent-green);
  color: #fff;
}

.from-exe {
  background: var(--accent-orange);
  color: #fff;
}

.target-controls {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.control-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.control-label {
  color: var(--text-secondary);
  font-size: 11px;
  width: 92px;
  white-space: nowrap;
}

.target-input,
.source-input {
  width: 300px;
  max-width: 34vw;
  padding: 4px 6px;
  border: 1px solid var(--border-color);
  border-radius: 3px;
  font-family: var(--font-mono);
  font-size: 12px;
}

.btn-small {
  padding: 4px 10px;
  font-size: 12px;
  border: 1px solid var(--border-color);
  border-radius: 3px;
  background: var(--bg-primary);
  cursor: pointer;
}

.btn-browse,
.btn-browse-source {
  background: var(--accent-blue);
  color: #fff;
  border-color: var(--accent-blue);
}

/* secondary: only enabled when updater_state.toml actually holds a choice */
.btn-reset-target,
.btn-reset-source {
  color: var(--text-secondary);
}

.btn-reset-target:disabled,
.btn-reset-source:disabled {
  opacity: 0.4;
  cursor: default;
}

.target-error {
  grid-column: 1 / -1;
  color: var(--accent-red);
  font-size: 12px;
}

.target-error.warn {
  color: var(--accent-orange);
}
</style>
