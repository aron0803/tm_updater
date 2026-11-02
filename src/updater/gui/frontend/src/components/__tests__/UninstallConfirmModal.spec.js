import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { reactive } from 'vue'
import UninstallConfirmModal from '../UninstallConfirmModal.vue'

describe('UninstallConfirmModal.vue', () => {
  let store

  beforeEach(() => {
    store = reactive({
      showUninstallModal: false,
      pendingUninstall: null,
      activeOperation: null,
      isUpdating: false,
    })

    window.pywebview = {
      api: {
        uninstall_package: vi.fn(() => Promise.resolve({ success: true })),
      },
    }
  })

  it('test_modal_hidden_by_default', () => {
    const wrapper = mount(UninstallConfirmModal, {
      global: { provide: { store } },
    })
    expect(wrapper.find('.modal-overlay').exists()).toBe(false)
  })

  it('test_modal_shows_when_flag_true', () => {
    store.showUninstallModal = true
    store.pendingUninstall = { packageName: 'test-pkg', installedVersion: '1.2.0' }

    const wrapper = mount(UninstallConfirmModal, {
      global: { provide: { store } },
    })
    expect(wrapper.find('.modal-overlay').exists()).toBe(true)
    expect(wrapper.text()).toContain('test-pkg')
    expect(wrapper.text()).toContain('1.2.0')
  })

  it('test_cancel_button_closes_modal', async () => {
    store.showUninstallModal = true
    store.pendingUninstall = { packageName: 'test-pkg', installedVersion: '1.2.0' }

    const wrapper = mount(UninstallConfirmModal, {
      global: { provide: { store } },
    })

    await wrapper.find('.btn-cancel').trigger('click')

    expect(store.showUninstallModal).toBe(false)
    expect(store.pendingUninstall).toBe(null)
  })

  it('test_confirm_uninstall_dismisses_immediately_and_calls_api', async () => {
    store.showUninstallModal = true
    store.pendingUninstall = { packageName: 'test-pkg', installedVersion: '1.2.0' }

    const wrapper = mount(UninstallConfirmModal, {
      global: { provide: { store } },
    })

    await wrapper.find('.btn-danger').trigger('click')

    expect(store.showUninstallModal).toBe(false)
    expect(store.isUpdating).toBe(true)
    expect(store.activeOperation).toEqual({
      packageName: 'test-pkg',
      type: 'uninstall',
      version: '1.2.0',
    })
    expect(window.pywebview.api.uninstall_package).toHaveBeenCalledWith('test-pkg')
  })
})
