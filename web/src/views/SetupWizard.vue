<template>
  <div class="page">
    <div class="page-header">
      <h2>🚀 欢迎使用 ZenTray</h2>
      <a-tag>初始配置</a-tag>
    </div>
    <p class="sub">核心功能已就绪！以下为可选配置，全部可跳过。</p>

    <a-steps :current="step" style="margin-bottom: 20px">
      <a-step title="欢迎" />
      <a-step title="通知" />
      <a-step title="AI" />
      <a-step title="完成" />
    </a-steps>

    <div v-show="step === 0" class="step-body">
      <a-result status="success" title="安装完成" subtitle="托盘常驻 · 任务轮播 · 番茄专注。可配置推送与 AI 复盘。" />
    </div>

    <div v-show="step === 1" class="step-body">
      <a-form :model="form" layout="vertical" style="max-width: 480px">
        <a-form-item label="WxPusher App Token（可选）">
          <a-input v-model="form.wx_token" placeholder="AT_..." />
        </a-form-item>
        <a-form-item label="WxPusher UID（可选）">
          <a-input v-model="form.wx_uid" placeholder="UID_..." />
        </a-form-item>
        <a-alert type="info">留空即可跳过，之后可在设置中填写。</a-alert>
      </a-form>
    </div>

    <div v-show="step === 2" class="step-body">
      <a-form :model="form" layout="vertical" style="max-width: 480px">
        <a-form-item label="AI API Key（可选）">
          <a-input-password v-model="form.ai_key" />
        </a-form-item>
        <a-form-item label="API Base URL">
          <a-input v-model="form.ai_base" placeholder="https://api.openai.com/v1" />
        </a-form-item>
        <a-form-item label="模型">
          <a-input v-model="form.ai_model" placeholder="gpt-4o" />
        </a-form-item>
      </a-form>
    </div>

    <div v-show="step === 3" class="step-body">
      <a-result status="success" title="配置完成" subtitle="点击完成开始使用。可随时在托盘 → 设置中修改。" />
    </div>

    <div class="page-footer">
      <a-button @click="skipAll">⏭️ 跳过全部</a-button>
      <a-space>
        <a-button v-if="step > 0" @click="step--">← 上一步</a-button>
        <a-button v-if="step < 3" type="primary" @click="step++">下一步 →</a-button>
        <a-button v-else type="primary" :loading="saving" @click="finish">完成</a-button>
      </a-space>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import { closeHost, completeSetup } from '@/api/client'

const step = ref(0)
const saving = ref(false)
const form = reactive({
  wx_token: '',
  wx_uid: '',
  ai_key: '',
  ai_base: '',
  ai_model: '',
})

async function finish(skip = false) {
  saving.value = true
  try {
    await completeSetup(skip ? {} : { ...form })
    Message.success('已完成')
    closeHost({ action: 'setup_done' })
  } catch (e) {
    Message.error(e?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

function skipAll() {
  finish(true)
}
</script>

<style scoped>
.sub {
  color: var(--color-text-3);
  margin: -8px 0 16px;
}
.step-body {
  min-height: 200px;
}
</style>
