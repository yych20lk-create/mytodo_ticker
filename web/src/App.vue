<template>
  <a-config-provider :update-at-scroll="true">
    <router-view />
  </a-config-provider>
</template>

<script setup>
import { onMounted, onUnmounted, provide, ref } from 'vue'
import { applyTheme, watchSystemTheme } from './theme'
import { getSettings } from './api/client'

const themeMode = ref('system')
const themeEffective = ref('dark')

provide('themeMode', themeMode)
provide('themeEffective', themeEffective)
provide('setThemeMode', (mode) => {
  themeMode.value = mode || 'system'
  themeEffective.value = applyTheme(themeMode.value)
})

let unwatch = () => {}

// 窗口无边框全域拖拽桥接支持
let isDragging = false
let startScreenX = 0
let startScreenY = 0

function handleMouseDown(e) {
  // 忽略按钮、输入框、可编辑控件及交互组件
  if (e.target && e.target.closest('button, input, textarea, a, .arco-btn, .arco-input-wrapper, .arco-select, .arco-picker, .arco-checkbox, .arco-radio, .arco-dropdown, .arco-modal')) {
    return
  }
  isDragging = true
  startScreenX = e.screenX
  startScreenY = e.screenY
  // 优先通知 Python 触发 OS 原生 Wayland/X11 窗口拖拽
  window.location.href = 'zentray://start_drag'
}

function handleMouseMove(e) {
  if (!isDragging) return
  const dx = e.screenX - startScreenX
  const dy = e.screenY - startScreenY
  if (dx !== 0 || dy !== 0) {
    startScreenX = e.screenX
    startScreenY = e.screenY
    window.location.href = `zentray://move?dx=${dx}&dy=${dy}`
  }
}

function handleMouseUp() {
  isDragging = false
}

onMounted(async () => {
  window.addEventListener('mousedown', handleMouseDown)
  window.addEventListener('mousemove', handleMouseMove)
  window.addEventListener('mouseup', handleMouseUp)

  try {
    const s = await getSettings()
    themeMode.value = s?.appearance?.theme || 'system'
  } catch (_) {
    themeMode.value = 'system'
  }
  themeEffective.value = applyTheme(themeMode.value)
  unwatch = watchSystemTheme(
    () => themeMode.value,
    (eff) => {
      themeEffective.value = eff
    },
  )
})

onUnmounted(() => {
  window.removeEventListener('mousedown', handleMouseDown)
  window.removeEventListener('mousemove', handleMouseMove)
  window.removeEventListener('mouseup', handleMouseUp)
  if (unwatch) unwatch()
})
</script>
