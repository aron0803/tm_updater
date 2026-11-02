<template>
  <div class="package-table" @scroll="closeContextMenu">
    <div class="table-header">
      <span class="col-name">Package</span>
      <span class="col-installed">Installed</span>
      <span class="col-available">Available</span>
      <span class="col-status">Status</span>
    </div>
    <div class="table-body">
      <div
        v-for="pkg in packages"
        :key="pkg.name"
        class="table-row"
        :class="rowClass(pkg)"
        @contextmenu.prevent="openContextMenu($event, pkg)"
      >
        <span class="col-name">{{ pkg.name }}</span>
        <span class="col-installed">{{ pkg.installed || '-' }}</span>
        <span class="col-available">
          <select
            :id="`version-${pkg.name}`"
            v-model="store.selectedVersions[pkg.name]"
            :disabled="store.isUpdating"
            @change="onVersionSelect(pkg)"
          >
            <option
              v-for="ver in (store.versionsMap[pkg.name] || [])"
              :key="ver"
              :value="ver"
            >{{ ver }}</option>
            <option v-if="!store.versionsMap[pkg.name] || store.versionsMap[pkg.name].length === 0" :value="null">-</option>
          </select>
        </span>
        <span class="col-status" :class="statusClass(pkg)">
          <template v-if="isActiveOperating(pkg)">
            <span class="spinner-mini"></span>
            <span class="status-label status-operating">{{ operatingText(pkg) }}</span>
          </template>
          <template v-else>
            <span class="status-label">{{ statusText(pkg) }}</span>
            <button
              v-if="getEffectiveStatus(pkg) === 'version_specified'"
              class="btn-install-mini"
              :disabled="store.isUpdating"
              title="Install this version"
              @click.stop="triggerVersionInstall(pkg)"
            >
              Install
            </button>
          </template>
        </span>
      </div>
      <div v-if="packages.length === 0" class="table-empty">
        No packages loaded
      </div>
    </div>

    <!-- Context Menu -->
    <div
      v-if="contextMenu.visible"
      class="context-menu"
      :style="{ top: `${contextMenu.y}px`, left: `${contextMenu.x}px` }"
      @click.stop
    >
      <div class="context-menu-header">
        {{ contextMenu.pkg?.name }}
      </div>
      <div
        class="context-menu-item"
        :class="{ disabled: !canInstall(contextMenu.pkg) || store.isUpdating }"
        @click="handleContextMenuInstall"
      >
        <span class="menu-icon">⬇</span>
        <span>{{ contextMenu.pkg?.installed ? '重新安裝 (Reinstall)' : '安裝 (Install)' }}</span>
      </div>
      <div
        class="context-menu-item menu-item-danger"
        :class="{ disabled: !contextMenu.pkg?.installed || store.isUpdating }"
        @click="handleContextMenuUninstall"
      >
        <span class="menu-icon">🗑</span>
        <span>移除 (Uninstall)</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { inject, computed, reactive, onMounted, onUnmounted } from 'vue'

const store = inject('store')
const packages = computed(() => store.packages)

const contextMenu = reactive({
  visible: false,
  x: 0,
  y: 0,
  pkg: null,
})

function openContextMenu(event, pkg) {
  if (!pkg) return
  const menuWidth = 200
  const menuHeight = 120
  const x = Math.min(event.clientX, window.innerWidth - menuWidth - 8)
  const y = Math.min(event.clientY, window.innerHeight - menuHeight - 8)
  contextMenu.visible = true
  contextMenu.x = Math.max(8, x)
  contextMenu.y = Math.max(8, y)
  contextMenu.pkg = pkg
}

function closeContextMenu() {
  contextMenu.visible = false
  contextMenu.pkg = null
}

function onKeyDown(e) {
  if (e.key === 'Escape') closeContextMenu()
}

onMounted(() => {
  window.addEventListener('click', closeContextMenu)
  window.addEventListener('keydown', onKeyDown)
})

onUnmounted(() => {
  window.removeEventListener('click', closeContextMenu)
  window.removeEventListener('keydown', onKeyDown)
})

function canInstall(pkg) {
  if (!pkg) return false
  const versions = store.versionsMap[pkg.name]
  return Boolean(versions && versions.length > 0)
}

function handleContextMenuInstall() {
  const pkg = contextMenu.pkg
  closeContextMenu()
  if (!pkg || !canInstall(pkg) || store.isUpdating) return
  const selected = store.selectedVersions[pkg.name] || (store.versionsMap[pkg.name] && store.versionsMap[pkg.name][0])
  store.pendingVersionInstall = {
    packageName: pkg.name,
    version: selected || pkg.installed,
    installedVersion: pkg.installed,
  }
  store.showVersionModal = true
}

function handleContextMenuUninstall() {
  const pkg = contextMenu.pkg
  closeContextMenu()
  if (!pkg || !pkg.installed || store.isUpdating) return
  store.pendingUninstall = {
    packageName: pkg.name,
    installedVersion: pkg.installed,
  }
  store.showUninstallModal = true
}

function isActiveOperating(pkg) {
  return Boolean(
    store.isUpdating &&
    store.activeOperation &&
    store.activeOperation.packageName === pkg.name
  )
}

function operatingText(pkg) {
  if (!store.activeOperation) return '處理中...'
  const { type, version } = store.activeOperation
  if (type === 'uninstall') return '移除中...'
  if (type === 'reinstall') return `重新安裝中...`
  return `安裝中...`
}

function triggerVersionInstall(pkg) {
  const selected = store.selectedVersions[pkg.name]
  if (selected && selected !== pkg.installed) {
    store.pendingVersionInstall = {
      packageName: pkg.name,
      version: selected,
      installedVersion: pkg.installed,
    }
    store.showVersionModal = true
    console.log('[PackageTable] Triggering install modal from button:', pkg.name, pkg.installed, '->', selected)
  }
}

function onVersionSelect(pkg) {
  const selected = store.selectedVersions[pkg.name]
  console.log('[PackageTable] Version selected:', selected, 'for', pkg.name, '(installed:', pkg.installed, ')')

  if (selected && selected !== pkg.installed) {
    triggerVersionInstall(pkg)
  }
}

function getEffectiveStatus(pkg) {
  const selected = store.selectedVersions[pkg.name]
  if (pkg.status === 'up_to_date' && selected && selected !== pkg.installed) {
    return 'version_specified'
  }
  return pkg.status
}

function rowClass(pkg) {
  const status = getEffectiveStatus(pkg)
  return {
    'row-update': status === 'update_available',
    'row-missing': status === 'not_installed',
    'row-specified': status === 'version_specified',
    'row-operating': isActiveOperating(pkg),
    'row-refreshing': store.isUpdating && !isActiveOperating(pkg),
  }
}

function statusClass(pkg) {
  const status = getEffectiveStatus(pkg)
  return {
    'status-ok': status === 'up_to_date',
    'status-update': status === 'update_available',
    'status-missing': status === 'not_installed' || status === 'not_in_source',
    'status-specified': status === 'version_specified',
  }
}

function statusText(pkg) {
  const map = {
    up_to_date: 'Up to date',
    update_available: '▲ Update',
    not_in_source: 'Not in source',
    not_installed: 'Not installed',
    version_specified: '⬇ Version specified',
  }
  return map[getEffectiveStatus(pkg)] || getEffectiveStatus(pkg)
}
</script>

<style scoped>
.package-table {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}

.table-header {
  display: flex;
  background: #e3f2fd;
  padding: 8px 12px;
  font-weight: 600;
  color: var(--accent-blue);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 2px solid var(--accent-blue);
}

.table-body {
  flex: 1;
  overflow-y: auto;
}

.table-row {
  display: flex;
  padding: 8px 12px;
  border-bottom: 1px solid var(--border-color);
  transition: background 0.15s, background-color 0.5s ease;
  user-select: none;
}

.row-operating {
  background-color: #e3f2fd !important;
  animation: operating-pulse 1.2s infinite ease-in-out;
}

@keyframes operating-pulse {
  0%   { background-color: #e3f2fd; }
  50%  { background-color: #bbdefb; }
  100% { background-color: #e3f2fd; }
}

.row-refreshing {
  background-color: #e8f5e9;
  animation: refresh-pulse 0.8s ease-out;
}

@keyframes refresh-pulse {
  0%   { background-color: #c8e6c9; }
  100% { background-color: #e8f5e9; }
}

.table-row:hover {
  background: #f0f4f8;
}

.row-update {
  background: var(--row-highlight);
}

.row-missing {
  background: #fff3e0;
}

.row-specified {
  background: #f3e5f5;
}

.col-name { flex: 2; font-weight: 500; }
.col-installed { flex: 1; }
.col-available { flex: 1; display: flex; align-items: center; }
.col-status {
  flex: 1.2;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  font-weight: 500;
  gap: 8px;
}

.spinner-mini {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 2px solid rgba(25, 118, 210, 0.2);
  border-top-color: var(--accent-blue, #1976d2);
  border-radius: 50%;
  animation: spin-mini 0.7s linear infinite;
  flex-shrink: 0;
}

@keyframes spin-mini {
  to { transform: rotate(360deg); }
}

.status-operating {
  color: var(--accent-blue, #1976d2);
  font-weight: 600;
  font-size: 11px;
}

.status-label {
  white-space: nowrap;
}

.btn-install-mini {
  padding: 2px 10px;
  border: none;
  border-radius: 3px;
  background-color: #8e24aa;
  color: white;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.15s, opacity 0.15s;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.15);
}

.btn-install-mini:hover:not(:disabled) {
  background-color: #6a1b9a;
}

.btn-install-mini:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.col-available select {
  width: 100%;
  padding: 3px 6px;
  border: 1px solid var(--border-color);
  border-radius: 3px;
  font-size: 12px;
  font-family: var(--font-family);
  background: white;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
  color: var(--text-primary);
}

.col-available select:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: #f5f5f5;
}

.col-available select:hover:not(:disabled) {
  background: #f9f9f9;
  border-color: var(--accent-blue);
}

.status-ok { color: var(--accent-green); }
.status-update { color: #e65100; }
.status-missing { color: var(--text-secondary); }
.status-specified { color: #6a1b9a; }

.table-empty {
  padding: 40px;
  text-align: center;
  color: var(--text-secondary);
}

/* Context Menu */
.context-menu {
  position: fixed;
  z-index: 2000;
  background: white;
  border: 1px solid #d0d7de;
  border-radius: 6px;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.18);
  min-width: 185px;
  padding: 4px 0;
  font-size: 12px;
  user-select: none;
}

.context-menu-header {
  padding: 6px 12px;
  font-weight: 600;
  color: #57606a;
  font-size: 11px;
  border-bottom: 1px solid #eaeef2;
  margin-bottom: 2px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.context-menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 12px;
  cursor: pointer;
  color: #24292f;
  transition: background-color 0.1s;
}

.context-menu-item:hover:not(.disabled) {
  background-color: #f0f4f8;
}

.context-menu-item.disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.menu-item-danger {
  color: #cf222e;
}

.menu-item-danger:hover:not(.disabled) {
  background-color: #ffebe9;
}

.menu-icon {
  font-size: 13px;
  width: 16px;
  display: inline-flex;
  justify-content: center;
}
</style>
