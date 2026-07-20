<template>
  <div class="page">
    <div class="page-header">
      <h2>🔁 周期任务管理</h2>
      <a-space>
        <a-button type="primary" @click="onNew">➕ 新建周期任务</a-button>
        <a-button @click="cancelHost">关闭</a-button>
      </a-space>
    </div>

    <a-table
      :loading="loading"
      :data="items"
      :columns="columns"
      :pagination="false"
      row-key="template_id"
      :bordered="{ cell: true }"
    >
      <template #period="{ record }">
        每{{ record.interval || 1 }}{{ unit(record.periodicity) }}
      </template>
      <template #life="{ record }">
        {{ record.long_term !== false ? '长期' : record.schedule_end_date || '—' }}
      </template>
      <template #ops="{ record }">
        <a-space>
          <a-button size="mini" @click="onEdit(record)">编辑</a-button>
          <a-button size="mini" status="danger" @click="onDelete(record)">删除</a-button>
        </a-space>
      </template>
    </a-table>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Message, Modal } from '@arco-design/web-vue'
import { cancelHost, deleteTemplate, listTemplates } from '@/api/client'

const router = useRouter()
const loading = ref(false)
const items = ref([])

const columns = [
  { title: '标题', dataIndex: 'base_title' },
  { title: '周期', slotName: 'period', width: 120 },
  { title: '有效期', slotName: 'life', width: 140 },
  { title: '操作', slotName: 'ops', width: 180 },
]

function unit(p) {
  return { daily: '天', weekly: '周', monthly: '月' }[p] || '天'
}

async function reload() {
  loading.value = true
  try {
    items.value = await listTemplates()
  } catch (e) {
    Message.error(e?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

function onNew() {
  router.push({ path: '/tasks/new', query: { mode: 'periodic' } })
}

function onEdit(record) {
  router.push({ path: `/tasks/${record.template_id}/edit`, query: { template: '1' } })
}

function onDelete(record) {
  Modal.confirm({
    title: '删除周期模板',
    content: `确定删除「${record.base_title}」？已生成的实例不会自动删除。`,
    onOk: async () => {
      await deleteTemplate(record.template_id)
      Message.success('已删除')
      reload()
    },
  })
}

onMounted(reload)
</script>
