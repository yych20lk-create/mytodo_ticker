<template>
  <div class="page">
    <div class="page-header">
      <h2>📋 任务列表</h2>
      <a-space>
        <a-button type="primary" @click="$router.push({ path: '/tasks/new', query: { from: 'list' } })">新建</a-button>
        <a-button @click="$router.push({ path: '/periodic', query: { from: 'list' } })">🔁 周期任务</a-button>
        <a-button @click="cancelHost">关闭</a-button>
      </a-space>
    </div>

    <div class="two-col">
      <a-card title="活跃任务" :bordered="true">
        <a-spin :loading="loading" style="width: 100%">
          <a-list :data="tasks" :bordered="false">
            <template #item="{ item }">
              <a-list-item
                class="task-item"
                :class="{ active: item.id === selectedId }"
                @click="selectedId = item.id"
              >
                <a-list-item-meta
                  :title="item.title"
                  :description="`${item.priority} · ${item.progress || 0}% · ${item.category || ''}`"
                />
              </a-list-item>
            </template>
          </a-list>
          <a-empty v-if="!loading && !tasks.length" description="暂无活跃任务" />
        </a-spin>
      </a-card>

      <a-card title="操作" :bordered="true">
        <template v-if="current">
          <p class="title">{{ current.title }}</p>
          <p class="meta">
            分类: {{ current.category }}　优先级: {{ current.priority }}　进度:
            {{ current.progress || 0 }}%
            <br v-if="current.deadline" />
            <span v-if="current.deadline">截止: {{ current.deadline }}</span>
          </p>
          <a-space direction="vertical" fill style="width: 100%">
            <a-button long type="outline" @click="onSelect">🔄 切换到此任务</a-button>
            <a-button long type="outline" @click="goProgress">📊 更新进度</a-button>
            <a-button long type="outline" @click="goEdit">📝 编辑查看</a-button>
            <a-space>
              <a-button type="primary" status="success" @click="onDone">✅ 完成</a-button>
              <a-button status="danger" @click="onAbandon">❌ 废弃</a-button>
            </a-space>
          </a-space>
        </template>
        <a-empty v-else description="请选择左侧任务" />
      </a-card>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Message, Modal } from '@arco-design/web-vue'
import {
  abandonTask,
  cancelHost,
  closeHost,
  listTasks,
  markDone,
  selectTask,
} from '@/api/client'

const route = useRoute()
const router = useRouter()
const loading = ref(false)

watch(() => route.path, (newPath) => {
  if (newPath === '/tasks') {
    reload()
  }
})
const tasks = ref([])
const selectedId = ref(null)

const current = computed(() => tasks.value.find((t) => t.id === selectedId.value) || null)

async function reload() {
  loading.value = true
  try {
    tasks.value = await listTasks()
    if (!selectedId.value && tasks.value.length) {
      selectedId.value = tasks.value[0].id
    }
  } catch (e) {
    Message.error(e?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

async function onSelect() {
  if (!current.value) return
  await selectTask(current.value.id)
  Message.success('已切换')
  closeHost({ action: 'select', id: current.value.id })
}

function goProgress() {
  if (!current.value) return
  router.push({ path: `/tasks/${current.value.id}/progress`, query: { from: 'list' } })
}

function goEdit() {
  if (!current.value) return
  router.push({ path: `/tasks/${current.value.id}/edit`, query: { from: 'list' } })
}

async function onDone() {
  if (!current.value) return
  await markDone(current.value.id)
  Message.success('已完成')
  closeHost({ action: 'done', id: current.value.id })
}

function onAbandon() {
  if (!current.value) return
  Modal.confirm({
    title: '确认废弃',
    content: `确定废弃「${current.value.title}」？`,
    onOk: async () => {
      await abandonTask(current.value.id)
      Message.success('已废弃')
      closeHost({ action: 'abandon', id: current.value.id })
    },
  })
}

onMounted(reload)
</script>

<style scoped>
.task-item {
  cursor: pointer;
  border-radius: 8px;
  padding: 4px 8px;
}
.task-item.active {
  background: var(--color-primary-light-1, #e8f3ff);
}
.title {
  font-weight: 600;
  margin: 0 0 8px;
}
.meta {
  color: var(--color-text-3);
  font-size: 13px;
  margin: 0 0 16px;
}
</style>
