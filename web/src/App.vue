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

onMounted(async () => {
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

onUnmounted(() => unwatch && unwatch())
</script>
