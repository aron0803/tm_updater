<template>
  <div v-if="store.showVersionModal" class="modal-overlay">
    <div class="modal-dialog">
      <h2>{{ isReinstall ? 'Reinstall Package?' : 'Install Different Version?' }}</h2>
      <p v-if="store.pendingVersionInstall">
        <template v-if="isReinstall">
          <strong>{{ store.pendingVersionInstall.packageName }}</strong>:
          重新安裝 <strong>v{{ store.pendingVersionInstall.version }}</strong><br>
          此操作將先乾淨解除安裝既有版本，再由來源 wheel 重新安裝。
        </template>
        <template v-else>
          <strong>{{ store.pendingVersionInstall.packageName }}</strong>:
          {{ store.pendingVersionInstall.installedVersion || 'not installed' }}
          &rarr; <strong>{{ store.pendingVersionInstall.version }}</strong><br>
          This will uninstall the current version first.
        </template>
      </p>
      <div class="modal-buttons">
        <button class="btn btn-cancel" :disabled="store.isUpdating" @click="cancelInstall">
          Cancel
        </button>
        <button class="btn btn-confirm" :disabled="store.isUpdating" @click="confirmInstall">
          {{ isReinstall ? 'Reinstall' : 'Install' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { inject, computed } from 'vue'

const store = inject('store')

const isReinstall = computed(() => {
  if (!store.pendingVersionInstall) return false
  const { version, installedVersion } = store.pendingVersionInstall
  return Boolean(installedVersion && version === installedVersion)
})

function cancelInstall() {
  if (store.pendingVersionInstall) {
    const { packageName, installedVersion } = store.pendingVersionInstall
    store.selectedVersions[packageName] = installedVersion || null
    console.log('[VersionConfirmModal] Cancelled, reset selectedVersions[' + packageName + '] to', installedVersion)
  }
  store.showVersionModal = false
  store.pendingVersionInstall = null
}

async function confirmInstall() {
  if (!store.pendingVersionInstall) return

  const { packageName, version, installedVersion } = store.pendingVersionInstall
  const reinstall = Boolean(installedVersion && version === installedVersion)

  // Register active background operation
  store.activeOperation = {
    packageName,
    type: reinstall ? 'reinstall' : 'install',
    version,
  }

  // Lock the UI for background updating
  store.isUpdating = true

  // Immediately close modal so user is not blocked and can see progress & spinner
  store.showVersionModal = false

  if (window.pywebview) {
    try {
      await window.pywebview.api.install_versioned_package(packageName, version)
    } catch (err) {
      console.error('[VersionConfirmModal] install_versioned_package call failed:', err)
      store.isUpdating = false
      store.activeOperation = null
      store.pendingVersionInstall = null
    }
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-dialog {
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
  padding: 24px;
  min-width: 320px;
  max-width: 500px;
}

.modal-dialog h2 {
  margin: 0 0 12px 0;
  font-size: 16px;
  font-weight: 600;
  color: #333;
}

.modal-dialog p {
  margin: 0 0 20px 0;
  font-size: 14px;
  color: #555;
  line-height: 1.5;
}

.modal-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.btn {
  padding: 8px 16px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: background 0.15s;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-cancel {
  background: #f0f0f0;
  color: #666;
}

.btn-cancel:hover:not(:disabled) {
  background: #e4e4e4;
}

.btn-confirm {
  background: var(--accent-blue, #1976d2);
  color: white;
}

.btn-confirm:hover:not(:disabled) {
  background: #1565c0;
}
</style>
