import { describe, it, expect, beforeEach, vi } from 'vitest'
import { reactive } from 'vue'
import { mount } from '@vue/test-utils'
import TargetBar from '../TargetBar.vue'

describe('TargetBar.vue', () => {
  let store
  let reloadTarget

  beforeEach(() => {
    store = reactive({
      packages: [],
      logs: [],
      config: {},
      target: {
        project: 'D:\\Work\\ProjA',
        venv: 'D:\\Work\\ProjA\\venv',
        source: '\\\\pnt52\\packages',
        source_origin: 'project',
        source_error: '',
        config: 'D:\\Work\\ProjA',
        config_origin: 'project',
        error: '',
      },
    })
    reloadTarget = vi.fn().mockResolvedValue({})
    window.pywebview = {
      api: {
        set_target: vi.fn(),
        choose_target_folder: vi.fn(),
        set_source: vi.fn(),
        choose_source_folder: vi.fn(),
      },
    }
  })

  function mountBar() {
    return mount(TargetBar, { global: { provide: { store, reloadTarget } } })
  }

  it('test_shows_resolved_project_and_venv', () => {
    const wrapper = mountBar()
    expect(wrapper.text()).toContain('D:\\Work\\ProjA')
    expect(wrapper.text()).toContain('venv:')
    expect(wrapper.find('.target-error').exists()).toBe(false)
  })

  it('test_apply_switches_target_and_reloads', async () => {
    window.pywebview.api.set_target.mockResolvedValue({
      error: null,
      target: {
        project: 'D:\\Work\\ProjB',
        venv: 'D:\\Work\\ProjB\\.venv',
        source: '\\\\pnt52\\packages',
        config: 'D:\\Work\\ProjB',
        config_origin: 'project',
        error: '',
      },
    })
    const wrapper = mountBar()
    const input = wrapper.get('input.target-input')
    await input.setValue('D:\\Work\\ProjB')
    await wrapper.get('button.btn-small').trigger('click')

    expect(window.pywebview.api.set_target).toHaveBeenCalledWith('D:\\Work\\ProjB')
    expect(store.target.project).toBe('D:\\Work\\ProjB')
    expect(reloadTarget).toHaveBeenCalled()
  })

  it('test_apply_keeps_old_target_and_shows_error_on_bad_path', async () => {
    window.pywebview.api.set_target.mockResolvedValue({
      error: '--project path not found: D:\\nope',
      target: store.target,
    })
    const wrapper = mountBar()
    await wrapper.get('input.target-input').setValue('D:\\nope')
    await wrapper.get('button.btn-small').trigger('click')

    expect(store.target.project).toBe('D:\\Work\\ProjA')
    expect(wrapper.get('.target-error').text()).toContain('not found')
    expect(reloadTarget).not.toHaveBeenCalled()
  })

  it('test_browse_cancelling_changes_nothing', async () => {
    window.pywebview.api.choose_target_folder.mockResolvedValue({ cancelled: true })
    const wrapper = mountBar()
    await wrapper.get('.btn-browse').trigger('click')

    expect(window.pywebview.api.choose_target_folder).toHaveBeenCalled()
    expect(store.target.project).toBe('D:\\Work\\ProjA')
    expect(reloadTarget).not.toHaveBeenCalled()
  })

  it('test_browse_reports_unavailable_dialog_with_actionable_hint', async () => {
    // 1.5.0 regression: the backend swallowed an AttributeError and the button
    // looked dead.  A failed dialog must carry a reason (spec section 3).
    window.pywebview.api.choose_target_folder.mockResolvedValue({
      cancelled: true,
      reason: "AttributeError: module 'webview' has no attribute 'create_file_dialog'",
      target: store.target,
    })
    const wrapper = mountBar()
    await wrapper.get('.btn-browse').trigger('click')

    expect(wrapper.get('.target-error').text()).toContain('無法開啟資料夾對話框')
    expect(wrapper.get('.target-error').text()).toContain('create_file_dialog')
    expect(wrapper.get('.target-error').text()).toContain('套用')
    expect(store.target.project).toBe('D:\\Work\\ProjA')
    expect(reloadTarget).not.toHaveBeenCalled()
  })

  it('test_browse_selecting_folder_switches_target', async () => {
    window.pywebview.api.choose_target_folder.mockResolvedValue({
      error: null,
      target: {
        project: 'D:\\Work\\ProjC',
        venv: 'D:\\Work\\ProjC\\venv',
        source: '\\\\pnt52\\packages',
        config: 'D:\\Work\\ProjC',
        config_origin: 'builtin',
        error: '',
      },
    })
    const wrapper = mountBar()
    await wrapper.get('.btn-browse').trigger('click')

    expect(store.target.project).toBe('D:\\Work\\ProjC')
    expect(reloadTarget).toHaveBeenCalled()
  })

  it('test_toml_parse_error_is_surfaced_with_encoding', () => {
    store.target = {
      project: 'D:\\Work\\ProjE',
      venv: 'D:\\Work\\ProjE\\venv',
      source: '\\\\pnt52\\packages',
      config: 'D:\\Work\\ProjE',
      config_origin: 'project',
      error: '',
      config_error: 'updater.toml 無法解析，已改用內建預設值：Invalid statement',
      encoding: 'cp950',
    }
    const wrapper = mountBar()
    expect(wrapper.get('.target-error.warn').text()).toContain('無法解析')
    expect(wrapper.get('.target-error.warn').text()).toContain('cp950')
  })

  it('test_missing_venv_shows_backend_error_message', () => {
    store.target = {
      project: 'D:\\Work\\ProjD',
      venv: '',
      source: '\\\\pnt52\\packages',
      config: 'D:\\Work\\ProjD',
      config_origin: 'project',
      error: '找不到 venv，請指定正確的專案資料夾',
    }
    const wrapper = mountBar()
    expect(wrapper.get('.target-error').text()).toContain('找不到 venv')
  })

  it('test_each_path_gets_its_own_row', () => {
    // 1.5.0 的單列排版會讓三條長路徑糊在一起（spec §3.1）
    const rows = mountBar().findAll('.target-row')
    const projRow = rows.find((r) => r.text().includes('專案'))
    const venvRow = rows.find((r) => r.text().includes('venv:'))
    const srcRow = rows.find((r) => r.text().includes('source:'))

    expect(projRow.text()).toContain('D:\\Work\\ProjA')
    expect(projRow.text()).not.toContain('venv')
    expect(venvRow.text()).toContain('D:\\Work\\ProjA\\venv')
    expect(venvRow.text()).not.toContain('pnt52')
    expect(srcRow.text()).toContain('\\\\pnt52\\packages')
  })

  it('test_set_source_switches_the_packages_folder_and_rescans', async () => {
    window.pywebview.api.set_source.mockResolvedValue({
      error: null,
      target: { ...store.target, source: 'D:\\whl', source_origin: 'gui', source_error: '' },
    })
    const wrapper = mountBar()
    await wrapper.get('.source-input').setValue('D:\\whl')
    await wrapper.get('.btn-apply-source').trigger('click')

    expect(window.pywebview.api.set_source).toHaveBeenCalledWith('D:\\whl')
    expect(store.target.source).toBe('D:\\whl')
    expect(reloadTarget).toHaveBeenCalled()
  })

  it('test_set_source_shows_error_and_keeps_old_source', async () => {
    window.pywebview.api.set_source.mockResolvedValue({
      error: '來源目錄不可用: D:\\nope',
      target: store.target,
    })
    const wrapper = mountBar()
    await wrapper.get('.source-input').setValue('D:\\nope')
    await wrapper.get('.btn-apply-source').trigger('click')

    expect(wrapper.get('.target-error').text()).toContain('來源目錄不可用')
    expect(store.target.source).toBe('\\\\pnt52\\packages')
    expect(reloadTarget).not.toHaveBeenCalled()
  })

  it('test_browse_source_uses_the_folder_dialog', async () => {
    window.pywebview.api.choose_source_folder.mockResolvedValue({
      error: null,
      target: { ...store.target, source: 'E:\\whl', source_origin: 'gui' },
    })
    const wrapper = mountBar()
    await wrapper.get('.btn-browse-source').trigger('click')

    expect(window.pywebview.api.choose_source_folder).toHaveBeenCalled()
    expect(store.target.source).toBe('E:\\whl')
    expect(reloadTarget).toHaveBeenCalled()
  })

  it('test_unusable_source_from_backend_is_shown_in_the_bar', () => {
    store.target = {
      ...store.target,
      source_error: '來源目錄不可用: \\\\pnt52\\packages',
    }
    const wrapper = mountBar()

    expect(wrapper.get('.target-error').text()).toContain('來源目錄不可用')
  })
})
