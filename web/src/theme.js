/**
 * 主题：与 Python zentray/ui/theme.py 一致
 * mode: light | dark | system
 */

export function resolveEffectiveTheme(mode) {
  const m = (mode || 'system').toLowerCase()
  if (m === 'light' || m === 'dark' || m === 'oled-dark' || m === 'slate-dark') {
    return m
  }
  // system
  try {
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return 'slate-dark'
    }
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
      return 'light'
    }
  } catch (_) {}
  return 'slate-dark'
}

/**
 * 应用 Arco + 页面 CSS 变量
 * @param {string} mode light | dark | oled-dark | slate-dark | system
 * @returns {string} 实际生效的 mode
 */
export function applyTheme(mode) {
  const effective = resolveEffectiveTheme(mode)
  const root = document.body

  // 清除旧主题 class
  root.classList.remove('theme-light', 'theme-dark', 'theme-slate-dark', 'theme-oled-dark')

  if (effective === 'light') {
    root.removeAttribute('arco-theme')
    root.classList.add('theme-light')
  } else if (effective === 'oled-dark') {
    root.setAttribute('arco-theme', 'dark')
    root.classList.add('theme-dark', 'theme-oled-dark')
  } else {
    // dark or slate-dark
    root.setAttribute('arco-theme', 'dark')
    root.classList.add('theme-dark', 'theme-slate-dark')
  }

  root.dataset.themeMode = mode || 'system'
  root.dataset.themeEffective = effective
  return effective
}

/** 监听系统主题变化（仅 mode=system 时生效） */
export function watchSystemTheme(getMode, onChange) {
  if (!window.matchMedia) return () => {}
  const mq = window.matchMedia('(prefers-color-scheme: dark)')
  const handler = () => {
    const mode = typeof getMode === 'function' ? getMode() : getMode
    if ((mode || 'system').toLowerCase() === 'system') {
      const eff = applyTheme('system')
      onChange && onChange(eff)
    }
  }
  if (mq.addEventListener) mq.addEventListener('change', handler)
  else if (mq.addListener) mq.addListener(handler)
  return () => {
    if (mq.removeEventListener) mq.removeEventListener('change', handler)
    else if (mq.removeListener) mq.removeListener(handler)
  }
}
