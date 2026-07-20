<template>
  <div class="page">
    <div class="page-header">
      <h2>选择操作</h2>
    </div>
    <a-spin :loading="loading">
      <p v-if="task" class="title">
        <b>当前任务：</b>{{ task.title }}
      </p>
      <a-space wrap size="medium">
        <a-button type="outline" @click="act('select')">🔄 切换到此任务</a-button>
        <a-button type="outline" @click="act('progress')">📊 更新任务进度</a-button>
        <a-button type="outline" @click="act('edit')">📝 编辑任务详情</a-button>
        <a-button status="success" @click="act('done')">✅ 完成</a-button>
        <a-button status="danger" @click="act('abandon')">❌ 废弃</a-button>
        <a-button @click="cancelHost">取消</a-button>
      </a-space>
    </a-spin>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { cancelHost, closeHost, getTask } from '@/api/client'

const route = useRoute()
const loading = ref(true)
const task = ref(null)

function act(action) {
  closeHost({ action, task_id: route.params.id })
}

onMounted(async () => {
  try {
    task.value = await getTask(route.params.id)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.title {
  margin: 0 0 16px;
  font-size: 15px;
}
</style>
