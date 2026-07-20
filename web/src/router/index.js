import { createRouter, createWebHashHistory } from 'vue-router'
import TaskList from '@/views/TaskList.vue'
import TaskForm from '@/views/TaskForm.vue'
import Progress from '@/views/Progress.vue'
import Settings from '@/views/Settings.vue'
import Periodic from '@/views/Periodic.vue'
import Home from '@/views/Home.vue'
import Reminder from '@/views/Reminder.vue'
import QuickAdd from '@/views/QuickAdd.vue'
import SetupWizard from '@/views/SetupWizard.vue'
import TaskAction from '@/views/TaskAction.vue'
import History from '@/views/History.vue'

const routes = [
  { path: '/', name: 'home', component: Home },
  { path: '/tasks', name: 'tasks', component: TaskList },
  { path: '/tasks/new', name: 'task-new', component: TaskForm },
  { path: '/tasks/:id/edit', name: 'task-edit', component: TaskForm, props: true },
  { path: '/tasks/:id/progress', name: 'task-progress', component: Progress, props: true },
  { path: '/tasks/:id/action', name: 'task-action', component: TaskAction, props: true },
  { path: '/periodic', name: 'periodic', component: Periodic },
  { path: '/history', name: 'history', component: History },
  { path: '/settings', name: 'settings', component: Settings },
  { path: '/reminder/:id', name: 'reminder', component: Reminder, props: true },
  { path: '/quick-add', name: 'quick-add', component: QuickAdd },
  { path: '/setup', name: 'setup', component: SetupWizard },
]

export default createRouter({
  history: createWebHashHistory(),
  routes,
})
