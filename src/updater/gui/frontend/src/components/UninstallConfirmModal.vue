<template>
  <div v-if="store.showUninstallModal" class="modal-overlay">
    <div class="modal-dialog">
      <h2 class="danger-title">Uninstall Package?</h2>
      <p v-if="store.pendingUninstall">
        確定要從環境中解除安裝 <strong>{{ store.pendingUninstall.packageName }}</strong>
        <span v-if="store.pendingUninstall.installedVersion"> (v{{ store.pendingUninstall.installedVersion }})</span> 嗎？<br>
        此操作將會完全移除該套件。
      </p>
      <div class="modal-buttons">
        <button class="btn btn-cancel" :disabled="store.isUpdating" @click="cancelUninstall">
          Cancel
        </button>
        <button class="btn btn-danger" :disabled="store.isUpdating" @click="confirmUninstall">
          Uninstall
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { inject } from 'vue'

const store = inject('store')

function cancelUninstall() {
  store.showUninstallModal = false
  store.pendingUninstall = null
}

async function confirmUninstall() {
  if (!store.pendingUninstall) return

  const { packageName, installedVersion } = store.pendingUninstall

  // Register active background operation
  store.activeOperation = {
    packageName,
    type: 'uninstall',
    version: installedVersion,
  }

  // Lock UI for background updating
  store.isUpdating = true

  // Immediately close modal so user is not blocked and can see progress & spinner
  store.showUninstallModal = false

  if (window.pywebview) {
    try {
      await window.pywebview.api.uninstall_package(packageName)
    } catch (err) {
      console.error('[UninstallConfirmModal] uninstall_package call failed:', err)
      store.isUpdating = false
      store.activeOperation = null
      store.pendingUninstall = null
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
}

.danger-title {
  color: #d32f2f;
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

.btn-danger {
  background: #d32f2f;
  color: white;
}

.btn-danger:hover:not(:disabled) {
  background: #b71c1c;
}
</style>
