<template>
  <!-- HH:mm 紧凑控件：可输入，也可分别调时/分 -->
  <div class="time-spinner" :class="{ disabled }">
    <NumberSpinner v-model="hour" :min="0" :max="23" :disabled="disabled" />
    <span class="colon">:</span>
    <NumberSpinner v-model="minute" :min="0" :max="59" :disabled="disabled" />
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import NumberSpinner from './NumberSpinner.vue'

const model = defineModel({ type: String, default: '17:00' })
const props = defineProps({
  disabled: { type: Boolean, default: false },
})

const hour = ref(17)
const minute = ref(0)

function pad(n) {
  return String(Math.max(0, n)).padStart(2, '0')
}

function parse(v) {
  const m = String(v || '17:00').match(/^(\d{1,2})\s*[:：]\s*(\d{1,2})$/)
  if (!m) return
  hour.value = Math.max(0, Math.min(23, parseInt(m[1], 10)))
  minute.value = Math.max(0, Math.min(59, parseInt(m[2], 10)))
}

function emitOut() {
  model.value = `${pad(hour.value)}:${pad(minute.value)}`
}

watch(
  () => model.value,
  (v) => parse(v),
  { immediate: true },
)

watch([hour, minute], () => emitOut())
</script>

<style scoped>
.time-spinner {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.colon {
  font-weight: 700;
  font-size: 16px;
  color: var(--color-text-2);
}
.disabled {
  opacity: 0.55;
}
</style>
