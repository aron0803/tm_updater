import { describe, it, expect, beforeEach, vi } from 'vitest'
import { reactive } from 'vue'
import { mount } from '@vue/test-utils'
import ActionPanel from '../ActionPanel.vue'

describe('ActionPanel.vue', () => {
  let store

  beforeEach(() => {
    store = reactive({
      packages: [],
      isUpdating: false,
      isScanning: false,
      isLaunching: false,
      updateComplete: false,
      updateResult: null,
      config: {},
      logs: [],
      showVersionModal: false,
      pendingVersionInstall: null,
      versionsMap: {},
      selectedVersions: {},
    })
    window.pywebview = {
      api: {
        run_update: vi.fn().mockResolvedValue({}),
        launch_app: vi.fn().mockResolvedValue({ success: true }),
        check_for_updates: vi.fn().mockResolvedValue({}),
      },
    }
  })

  function mountPanel() {
    return mount(ActionPanel, { global: { provide: { store } } })
  }

  // -------------------------------------------------------------------
  // Update All button
  // -------------------------------------------------------------------

  it('test_update_button_disabled_when_is_updating', () => {
    store.packages = [{ name: 'pkg-a', installed: '1.0.0', available: '2.0.0', status: 'update_available' }]
    store.isUpdating = true

    const wrapper = mountPanel()
    const btn = wrapper.find('.btn-primary')
    expect(btn.attributes('disabled')).toBeDefined()
  })

  it('test_update_button_enabled_when_no_updates_available', () => {
    store.packages = [{ name: 'pkg-a', installed: '1.0.0', available: '1.0.0', status: 'up_to_date' }]

    const wrapper = mountPanel()
    const btn = wrapper.find('.btn-primary')
    expect(btn.attributes('disabled')).toBeUndefined()
  })

  it('test_update_button_enabled_when_updates_available', () => {
    store.packages = [{ name: 'pkg-a', installed: '1.0.0', available: '2.0.0', status: 'update_available' }]

    const wrapper = mountPanel()
    const btn = wrapper.find('.btn-primary')
    expect(btn.attributes('disabled')).toBeUndefined()
  })

  it('test_update_button_enabled_when_package_not_installed', () => {
    store.packages = [{ name: 'pkg-a', installed: null, available: '1.0.0', status: 'not_installed' }]

    const wrapper = mountPanel()
    const btn = wrapper.find('.btn-primary')
    expect(btn.attributes('disabled')).toBeUndefined()
  })

  it('test_clicking_update_sets_is_updating', async () => {
    store.packages = [{ name: 'pkg-a', installed: '1.0.0', available: '2.0.0', status: 'update_available' }]
    window.pywebview.api.run_update = vi.fn(() => new Promise(() => {}))

    const wrapper = mountPanel()
    await wrapper.find('.btn-primary').trigger('click')

    expect(store.isUpdating).toBe(true)
  })

  it('test_clicking_update_calls_run_update_api', async () => {
    store.packages = [{ name: 'pkg-a', installed: '1.0.0', available: '2.0.0', status: 'update_available' }]

    const wrapper = mountPanel()
    await wrapper.find('.btn-primary').trigger('click')
    await new Promise((r) => setTimeout(r, 0))

    expect(window.pywebview.api.run_update).toHaveBeenCalled()
  })

  // -------------------------------------------------------------------
  // Check for Updates mode (no updates available)
  // -------------------------------------------------------------------

  it('test_button_shows_check_for_updates_when_no_updates', () => {
    store.packages = [{ name: 'pkg-a', installed: '1.0.0', available: '1.0.0', status: 'up_to_date' }]

    const wrapper = mountPanel()
    expect(wrapper.find('.btn-primary').text()).toContain('Check for Updates')
  })

  it('test_button_shows_checking_when_is_scanning', () => {
    store.isScanning = true

    const wrapper = mountPanel()
    expect(wrapper.find('.btn-primary').text()).toContain('Checking...')
  })

  it('test_button_disabled_when_is_scanning', () => {
    store.isScanning = true

    const wrapper = mountPanel()
    expect(wrapper.find('.btn-primary').attributes('disabled')).toBeDefined()
  })

  it('test_clicking_check_for_updates_sets_is_scanning', async () => {
    store.packages = [{ name: 'pkg-a', installed: '1.0.0', available: '1.0.0', status: 'up_to_date' }]
    window.pywebview.api.check_for_updates = vi.fn(() => new Promise(() => {}))

    const wrapper = mountPanel()
    await wrapper.find('.btn-primary').trigger('click')

    expect(store.isScanning).toBe(true)
  })

  it('test_clicking_check_for_updates_calls_api', async () => {
    store.packages = [{ name: 'pkg-a', installed: '1.0.0', available: '1.0.0', status: 'up_to_date' }]

    const wrapper = mountPanel()
    await wrapper.find('.btn-primary').trigger('click')
    await new Promise((r) => setTimeout(r, 0))

    expect(window.pywebview.api.check_for_updates).toHaveBeenCalled()
    expect(window.pywebview.api.run_update).not.toHaveBeenCalled()
  })

  it('test_button_disabled_when_empty_packages', () => {
    // No packages at all — should show Check for Updates, not disabled
    const wrapper = mountPanel()
    expect(wrapper.find('.btn-primary').attributes('disabled')).toBeUndefined()
    expect(wrapper.find('.btn-primary').text()).toContain('Check for Updates')
  })

  // -------------------------------------------------------------------
  // Install Specified button
  // -------------------------------------------------------------------

  it('test_install_specified_button_shown_when_version_specified', () => {
    store.packages = [{ name: 'pkg-a', installed: '2.4.9', available: '2.4.4', status: 'up_to_date' }]
    store.selectedVersions = { 'pkg-a': '2.4.4' }

    const wrapper = mountPanel()
    const btn = wrapper.find('.btn-version')
    expect(btn.exists()).toBe(true)
    expect(btn.text()).toContain('Install Specified (1)')
  })

  it('test_clicking_install_specified_opens_modal', async () => {
    store.packages = [{ name: 'pkg-a', installed: '2.4.9', available: '2.4.4', status: 'up_to_date' }]
    store.selectedVersions = { 'pkg-a': '2.4.4' }

    const wrapper = mountPanel()
    await wrapper.find('.btn-version').trigger('click')

    expect(store.showVersionModal).toBe(true)
    expect(store.pendingVersionInstall).toEqual({
      packageName: 'pkg-a',
      version: '2.4.4',
      installedVersion: '2.4.9',
    })
  })

  // -------------------------------------------------------------------
  // Status bar
  // -------------------------------------------------------------------

  it('test_status_bar_hidden_when_no_result', () => {
    const wrapper = mountPanel()
    expect(wrapper.find('.status-bar').exists()).toBe(false)
  })

  it('test_status_bar_shows_updated_count', async () => {
    store.updateResult = { total: 3, updated: 2, failed: 1 }

    const wrapper = mountPanel()
    expect(wrapper.find('.status-bar').exists()).toBe(true)
    expect(wrapper.text()).toContain('2')
  })
})
