<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'

type TelemetryPoint = { received_at: string; temperature_c: number; vibration_mm_s: number }
type Message = {
  id: number
  received_at: string
  topic: string
  packet_type: 'PUBLISH'
  device_id: string | null
  qos: number
  retained: boolean
  payload: { kind: 'json' | 'text' | 'base64'; value: string; truncated: boolean }
  telemetry: TelemetryPoint | null
}
type State = {
  broker: { connected: boolean; changed_at: string | null; stats_at: string | null }
  metrics: Record<string, number>
  devices: { active_count: number; active_window_seconds: number }
  iot_publish_count: number
  telemetry_rate: number
  last_message_at: string | null
  messages: Message[]
  telemetry: TelemetryPoint[]
}

const blankState = (): State => ({
  broker: { connected: false, changed_at: null, stats_at: null },
  metrics: {}, devices: { active_count: 0, active_window_seconds: 15 }, iot_publish_count: 0,
  telemetry_rate: 0, last_message_at: null, messages: [], telemetry: [],
})
const state = ref<State>(blankState())
const browserConnected = ref(false)
const loaded = ref(false)
const autoScroll = ref(true)
const topicFilter = ref('')
const selectedMessage = ref<Message | null>(null)
const eventSource = ref<EventSource | null>(null)
const tableBody = ref<HTMLElement | null>(null)

const filteredMessages = computed(() => {
  const filter = topicFilter.value.trim().toLowerCase()
  return filter ? state.value.messages.filter((item) => item.topic.toLowerCase().includes(filter)) : state.value.messages
})
const latestTelemetry = computed(() => state.value.telemetry.at(-1) ?? null)
const metrics = computed(() => state.value.metrics)

function applySnapshot(snapshot: State) {
  state.value = snapshot
  loaded.value = true
  scrollTable()
}

function scrollTable() {
  if (!autoScroll.value) return
  requestAnimationFrame(() => {
    if (tableBody.value) tableBody.value.scrollTop = 0
  })
}

function connectEvents() {
  const source = new EventSource('/api/events')
  eventSource.value = source
  source.onopen = () => { browserConnected.value = true }
  source.onerror = () => { browserConnected.value = false }
  source.addEventListener('snapshot', (event) => {
    applySnapshot(JSON.parse((event as MessageEvent).data) as State)
  })
  source.addEventListener('message', (event) => {
    const item = JSON.parse((event as MessageEvent).data) as Message
    state.value.messages = [item, ...state.value.messages].slice(0, 100)
    state.value.last_message_at = item.received_at
    if (item.telemetry) state.value.telemetry = [...state.value.telemetry, item.telemetry].slice(-120)
    scrollTable()
  })
  source.addEventListener('broker', (event) => {
    const update = JSON.parse((event as MessageEvent).data) as { connected: boolean; changed_at: string | null }
    state.value.broker = { ...state.value.broker, ...update }
  })
  source.addEventListener('metrics', (event) => {
    const update = JSON.parse((event as MessageEvent).data) as { metrics: Record<string, number>; stats_at: string }
    state.value.metrics = update.metrics
    state.value.broker.stats_at = update.stats_at
  })
  source.addEventListener('devices', (event) => {
    state.value.devices = JSON.parse((event as MessageEvent).data) as State['devices']
  })
  source.addEventListener('iot_messages', (event) => {
    state.value.iot_publish_count = (JSON.parse((event as MessageEvent).data) as { count: number }).count
  })
  source.addEventListener('rate', (event) => {
    state.value.telemetry_rate = (JSON.parse((event as MessageEvent).data) as { telemetry_rate: number }).telemetry_rate
  })
}

function formatTime(value: string | null | undefined) {
  if (!value) return 'Chưa có dữ liệu'
  return new Intl.DateTimeFormat('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }).format(new Date(value))
}
function formatNumber(value: number | undefined) {
  return value === undefined ? '—' : new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 1 }).format(value)
}
function formatBytes(value: number | undefined) {
  if (value === undefined) return '—'
  if (value < 1024) return `${formatNumber(value)} B`
  if (value < 1024 ** 2) return `${formatNumber(value / 1024)} KB`
  return `${formatNumber(value / 1024 ** 2)} MB`
}
function formatDuration(seconds: number | undefined) {
  if (seconds === undefined) return '—'
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const remainder = Math.floor(seconds % 60)
  return days ? `${days} ngày ${hours} giờ` : hours ? `${hours} giờ ${minutes} phút` : `${minutes} phút ${remainder} giây`
}
function payloadPreview(message: Message) {
  const value = message.payload.kind === 'base64' ? `base64: ${message.payload.value}` : message.payload.value
  return value.length > 180 ? `${value.slice(0, 180)}…` : value
}
function payloadDetail(message: Message) {
  if (message.payload.kind !== 'json') return message.payload.value
  try { return JSON.stringify(JSON.parse(message.payload.value), null, 2) } catch { return message.payload.value }
}
function chartPath(key: 'temperature_c' | 'vibration_mm_s') {
  const points = state.value.telemetry
  if (!points.length) return ''
  const values = points.map((point) => point[key])
  const min = Math.min(...values)
  const max = Math.max(...values)
  const span = max - min || 1
  return values.map((value, index) => {
    const x = points.length === 1 ? 350 : 16 + (index / (points.length - 1)) * 668
    const y = 150 - ((value - min) / span) * 122
    return `${index ? 'L' : 'M'}${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
}
function chartLabels(key: 'temperature_c' | 'vibration_mm_s') {
  const values = state.value.telemetry.map((point) => point[key])
  if (!values.length) return ['—', '—', '—']
  const min = Math.min(...values)
  const max = Math.max(...values)
  return [max, (max + min) / 2, min].map((value) => value.toFixed(1))
}
function chartLast(key: 'temperature_c' | 'vibration_mm_s') {
  if (!latestTelemetry.value) return '—'
  return formatNumber(latestTelemetry.value[key])
}

onMounted(connectEvents)
onUnmounted(() => eventSource.value?.close())
</script>

<template>
  <main id="top" class="shell">
    <header class="topbar">
      <a class="brand" href="#top" aria-label="MQTT LAB trang chủ">
        <span class="brand-mark"><i></i><i></i><i></i></span>
        <span>MQTT<span class="brand-light"> LAB</span></span>
      </a>
      <div class="header-statuses" aria-label="Trạng thái kết nối">
        <span class="status-pill" :class="browserConnected ? 'online' : 'waiting'">
          <span class="status-indicator"></span>
          <span>DASHBOARD {{ browserConnected ? 'ĐANG TRỰC TUYẾN' : 'ĐANG KẾT NỐI' }}</span>
        </span>
        <span class="status-pill" :class="state.broker.connected ? 'online' : 'offline'">
          <span class="status-indicator"></span>
          <span>MOSQUITTO {{ state.broker.connected ? 'ĐÃ KẾT NỐI' : 'MẤT KẾT NỐI' }}</span>
        </span>
      </div>
    </header>

    <section class="stats-grid" aria-label="Thống kê thiết bị và broker">
      <article class="stat-card accent-cyan">
        <div class="stat-label">THIẾT BỊ ĐANG HOẠT ĐỘNG <span class="stat-symbol">◉</span></div>
        <div class="stat-value">{{ formatNumber(state.devices.active_count) }}<small> thiết bị</small></div>
        <div class="stat-foot">Có telemetry trong {{ state.devices.active_window_seconds }} giây gần nhất</div>
      </article>
      <article class="stat-card accent-violet">
        <div class="stat-label">BROKER UPTIME <span class="stat-symbol">◷</span></div>
        <div class="stat-value compact">{{ formatDuration(metrics.uptime_seconds) }}</div>
        <div class="stat-foot">Mosquitto · MQTT 3.1.1</div>
      </article>
      <article class="stat-card accent-blue">
        <div class="stat-label">IOT PUBLISH ĐÃ NHẬN <span class="stat-symbol">⇩</span></div>
        <div class="stat-value">{{ formatNumber(state.iot_publish_count) }}<small> gói tin</small></div>
      </article>
      <article class="stat-card accent-orange">
        <div class="stat-label">TELEMETRY OBSERVED <span class="stat-symbol">⌁</span></div>
        <div class="stat-value">{{ formatNumber(state.telemetry_rate) }}<small> msg/s</small></div>
        <div class="stat-foot">{{ state.last_message_at ? `Tin cuối · ${formatTime(state.last_message_at)}` : 'Đang chờ bản tin đầu tiên' }}</div>
      </article>
    </section>

    <section class="charts-grid">
      <article class="panel chart-panel">
        <div class="panel-heading">
          <div><div class="panel-kicker"><span class="legend-dot temp-dot"></span> MACHINE-01 · TEMPERATURE</div><h2>Nhiệt độ <span>°C</span></h2></div>
          <div class="chart-current">{{ chartLast('temperature_c') }}<small> °C</small></div>
        </div>
        <div class="chart-area">
          <div class="chart-y-labels"><span>{{ chartLabels('temperature_c')[0] }}</span><span>{{ chartLabels('temperature_c')[1] }}</span><span>{{ chartLabels('temperature_c')[2] }}</span></div>
          <svg viewBox="0 0 700 170" preserveAspectRatio="none" role="img" aria-label="Biểu đồ nhiệt độ theo thời gian">
            <defs><linearGradient id="tempFill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stop-color="var(--teal)" stop-opacity=".18"/><stop offset="100%" stop-color="var(--teal)" stop-opacity="0"/></linearGradient></defs>
            <path class="grid-line" d="M0 28H700 M0 89H700 M0 150H700"/>
            <path v-if="state.telemetry.length > 1" :d="`${chartPath('temperature_c')} L684,150 L16,150 Z`" fill="url(#tempFill)"/>
            <path v-if="state.telemetry.length > 1" class="chart-line temp-line" :d="chartPath('temperature_c')"/>
            <text v-if="!state.telemetry.length" x="350" y="92" text-anchor="middle" class="empty-chart">Đang chờ telemetry từ ESP32</text>
            <circle v-if="latestTelemetry && state.telemetry.length > 1" cx="684" :cy="150 - ((latestTelemetry.temperature_c - Math.min(...state.telemetry.map(p => p.temperature_c))) / (Math.max(...state.telemetry.map(p => p.temperature_c)) - Math.min(...state.telemetry.map(p => p.temperature_c)) || 1)) * 122" r="4" class="chart-point temp-point"/>
          </svg>
        </div>
        <div class="chart-axis"><span>{{ state.telemetry.length ? formatTime(state.telemetry[0].received_at) : '—' }}</span><span>{{ state.telemetry.length }} điểm · {{ formatTime(latestTelemetry?.received_at) }}</span></div>
      </article>
      <article class="panel chart-panel">
        <div class="panel-heading">
          <div><div class="panel-kicker"><span class="legend-dot vibration-dot"></span> MACHINE-01 · VIBRATION</div><h2>Rung động <span>mm/s</span></h2></div>
          <div class="chart-current violet-text">{{ chartLast('vibration_mm_s') }}<small> mm/s</small></div>
        </div>
        <div class="chart-area">
          <div class="chart-y-labels"><span>{{ chartLabels('vibration_mm_s')[0] }}</span><span>{{ chartLabels('vibration_mm_s')[1] }}</span><span>{{ chartLabels('vibration_mm_s')[2] }}</span></div>
          <svg viewBox="0 0 700 170" preserveAspectRatio="none" role="img" aria-label="Biểu đồ rung động theo thời gian">
            <defs><linearGradient id="vibFill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stop-color="var(--violet)" stop-opacity=".18"/><stop offset="100%" stop-color="var(--violet)" stop-opacity="0"/></linearGradient></defs>
            <path class="grid-line" d="M0 28H700 M0 89H700 M0 150H700"/>
            <path v-if="state.telemetry.length > 1" :d="`${chartPath('vibration_mm_s')} L684,150 L16,150 Z`" fill="url(#vibFill)"/>
            <path v-if="state.telemetry.length > 1" class="chart-line vib-line" :d="chartPath('vibration_mm_s')"/>
            <text v-if="!state.telemetry.length" x="350" y="92" text-anchor="middle" class="empty-chart">Đang chờ telemetry từ ESP32</text>
            <circle v-if="latestTelemetry && state.telemetry.length > 1" cx="684" :cy="150 - ((latestTelemetry.vibration_mm_s - Math.min(...state.telemetry.map(p => p.vibration_mm_s))) / (Math.max(...state.telemetry.map(p => p.vibration_mm_s)) - Math.min(...state.telemetry.map(p => p.vibration_mm_s)) || 1)) * 122" r="4" class="chart-point vib-point"/>
          </svg>
        </div>
        <div class="chart-axis"><span>{{ state.telemetry.length ? formatTime(state.telemetry[0].received_at) : '—' }}</span><span>{{ state.telemetry.length }} điểm · {{ formatTime(latestTelemetry?.received_at) }}</span></div>
      </article>
    </section>

    <section class="panel traffic-panel">
      <div class="traffic-heading">
        <div>
          <div class="panel-kicker"><span class="legend-dot temp-dot"></span> MQTT PUBLISH · factory/#</div>
          <h2>Dòng bản tin <span class="count-badge">{{ filteredMessages.length }} PUBLISH</span></h2>
        </div>
        <div class="traffic-controls">
          <label class="filter-box"><span>⌕</span><input v-model="topicFilter" type="search" placeholder="Lọc theo topic…" aria-label="Lọc bản tin theo topic" /></label>
          <label class="scroll-toggle"><input v-model="autoScroll" type="checkbox"/><span class="toggle-track"></span><span>Tự cuộn</span></label>
        </div>
      </div>
      <div class="table-wrap" ref="tableBody">
        <table>
          <thead><tr><th>THỜI GIAN</th><th>LOẠI GÓI</th><th>TOPIC</th><th>QOS</th><th>RETAINED</th><th>PAYLOAD</th><th></th></tr></thead>
          <tbody v-if="filteredMessages.length">
            <tr v-for="message in filteredMessages" :key="message.id" @click="selectedMessage = message" tabindex="0" @keydown.enter="selectedMessage = message">
              <td class="time-cell">{{ formatTime(message.received_at) }}</td>
              <td><span class="packet-chip">{{ message.packet_type }}</span></td>
              <td><code class="topic-chip">{{ message.topic }}</code></td>
              <td><span class="qos-chip">{{ message.qos }}</span></td>
              <td><span class="retained" :class="message.retained ? 'yes' : ''">{{ message.retained ? 'YES' : 'NO' }}</span></td>
              <td><code class="payload-preview">{{ payloadPreview(message) }}<span v-if="message.payload.truncated" class="truncated-mark"> · đã cắt</span></code></td>
              <td class="open-cell">↗</td>
            </tr>
          </tbody>
        </table>
        <div v-if="!filteredMessages.length" class="empty-state">
          <div class="empty-icon">⌁</div>
          <strong>{{ loaded ? 'Chưa có bản tin phù hợp' : 'Đang kết nối tới broker' }}</strong>
          <span>{{ loaded ? 'Khi ESP32 publish dữ liệu, bản tin sẽ xuất hiện tại đây.' : 'Dashboard sẽ tự cập nhật khi kết nối thành công.' }}</span>
        </div>
      </div>
      <div class="table-footer"><span><i class="live-dot"></i> MQTT PUBLISH STREAM</span><span>Nhận gần nhất · {{ formatTime(state.last_message_at) }}</span></div>
    </section>

    <footer><span>MQTT LAB <b>·</b> LIVE MONITOR</span><span>Broker statistics refresh theo chu kỳ Mosquitto</span></footer>

    <div v-if="selectedMessage" class="modal-backdrop" @click.self="selectedMessage = null" @keydown.esc="selectedMessage = null">
      <section class="detail-modal" role="dialog" aria-modal="true" aria-label="Chi tiết bản tin">
        <div class="modal-head"><div><div class="panel-kicker">MQTT PUBLISH · #{{ selectedMessage.id }}</div><h2>Chi tiết bản tin</h2></div><button class="close-button" @click="selectedMessage = null" aria-label="Đóng">×</button></div>
        <div class="detail-meta"><span>MQTT PACKET</span><code>{{ selectedMessage.packet_type }}</code><span>DEVICE ID</span><code>{{ selectedMessage.device_id || 'Không có trong payload' }}</code><span>TOPIC</span><code>{{ selectedMessage.topic }}</code><span>THỜI GIAN NHẬN</span><code>{{ formatTime(selectedMessage.received_at) }}</code><span>QOS / RETAINED</span><code>{{ selectedMessage.qos }} / {{ selectedMessage.retained ? 'yes' : 'no' }}</code><span>PAYLOAD TYPE</span><code>{{ selectedMessage.payload.kind }}{{ selectedMessage.payload.truncated ? ' · truncated at 64 KiB' : '' }}</code></div>
        <pre class="detail-payload">{{ payloadDetail(selectedMessage) }}</pre>
      </section>
    </div>
  </main>
</template>
