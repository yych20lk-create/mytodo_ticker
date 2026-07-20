/**
 * 主题：与 Python zentray/ui/theme.py 一致
 * mode: light | dark | system
 */

export function resolveEffectiveTheme(mode) {
  const m = (mode || 'system').toLowerCase()
  if (m === 'light' || m === 'dark') return m
  // system
  try {
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return 'dark'
    }
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
      return 'light'
    }
  } catch (_) {}
  return 'dark'
}

/**
 * 应用 Arco + 页面 CSS 变量
 * @param {string} mode light|dark|system
 * @returns {string} 实际 light|dark
 */
export function applyTheme(mode) {
  const effective = resolveEffectiveTheme(mode)
  const root = document.body
  if (effective === 'dark') {
    root.setAttribute('arco-theme', 'dark')
    root.classList.add('theme-dark')
    root.classList.remove('theme-light')
  } else {
    root.removeAttribute('arco-theme')
    root.classList.add('theme-light')
    root.classList.remove('theme-dark')
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
