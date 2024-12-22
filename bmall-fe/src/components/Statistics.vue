<template>
  <div class="statistics">
    <div class="header">
      <h2>数据统计</h2>
      <el-button type="primary" @click="fetchData">
        刷新
      </el-button>
    </div>

    <el-card class="trend-chart">
      <template #header>
        <div class="card-header">
          <span>最近一小时趋势</span>
          <el-radio-group v-model="chartMetric" size="small">
            <el-radio-button :value="'items_count'">商品数</el-radio-button>
            <el-radio-button :value="'skus_count'">SKU数</el-radio-button>
            <el-radio-button :value="'users_count'">用户数</el-radio-button>
          </el-radio-group>
        </div>
      </template>
      <div class="chart-container">
        <v-chart class="chart" :option="chartOption" autoresize />
      </div>
    </el-card>

    <el-tabs v-model="activePeriod">
      <el-tab-pane 
        v-for="(stats, period) in statistics" 
        :key="period"
        :label="period"
        :name="period"
      >
        <div class="stats-cards">
          <el-card class="stats-card">
            <template #header>
              <div class="card-header">
                <span>新增商品</span>
              </div>
            </template>
            <div class="stats-number">{{ stats.new_items }}</div>
          </el-card>

          <el-card class="stats-card">
            <template #header>
              <div class="card-header">
                <span>新增SKU</span>
              </div>
            </template>
            <div class="stats-number">{{ stats.new_skus }}</div>
          </el-card>

          <el-card class="stats-card">
            <template #header>
              <div class="card-header">
                <span>已售商品</span>
              </div>
            </template>
            <div class="stats-number success">{{ stats.sold_items }}</div>
          </el-card>

          <el-card class="stats-card">
            <template #header>
              <div class="card-header">
                <span>新增封禁</span>
              </div>
            </template>
            <div class="stats-number danger">{{ stats.new_blacklist }}</div>
          </el-card>
        </div>

        <el-card class="active-users">
          <template #header>
            <div class="card-header">
              <span>活跃用户 TOP5</span>
            </div>
          </template>
          <el-table :data="stats.active_users" style="width: 100%">
            <el-table-column label="用户信息" width="200">
              <template #default="{ row }">
                <div class="user-info">
                  <span class="user-name">
                    {{ row.uname }}
                    <el-tag 
                      v-if="row.is_blacklisted" 
                      type="danger" 
                      size="small"
                    >
                      黑名单
                    </el-tag>
                  </span>
                  <el-link 
                    :href="`https://space.bilibili.com/${row.uid}`"
                    target="_blank"
                    type="primary"
                    class="user-uid"
                  >
                    UID: {{ row.uid }}
                  </el-link>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="listing_count" label="上架数量" width="100" sortable />
            <el-table-column prop="sku_count" label="商品种类" width="100" sortable />
            <el-table-column label="上架时间" width="300">
              <template #default="{ row }">
                <div>首次: {{ formatDate(row.first_listing) }}</div>
                <div>最近: {{ formatDate(row.last_listing) }}</div>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="200">
              <template #default="{ row }">
                <el-tooltip 
                  v-if="row.is_blacklisted"
                  :content="row.blacklist_reason"
                  placement="top"
                >
                  <el-tag type="danger">已封禁</el-tag>
                </el-tooltip>
                <el-tag v-else type="success">正常</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { apiClient } from '../api/client'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { toBeijingTime, toShortBeijingTime } from '../utils/date'

// 注册 ECharts 组件
use([
  CanvasRenderer,
  LineChart,
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent
])

interface ActiveUser {
  uid: string
  uname: string
  listing_count: number
  sku_count: number
  first_listing: string
  last_listing: string
  is_blacklisted: boolean
  blacklist_reason: string | null
}

interface PeriodStats {
  new_items: number
  new_skus: number
  new_blacklist: number
  sold_items: number
  active_users: ActiveUser[]
}

interface TrendData {
  time: string
  items_count: number
  skus_count: number
  users_count: number
}

const statistics = ref<Record<string, PeriodStats>>({})
const trendData = ref<TrendData[]>([])
const activePeriod = ref('1小时')
const loading = ref(false)
const chartMetric = ref<'items_count' | 'skus_count' | 'users_count'>('items_count')

const metricLabels = {
  items_count: '商品数',
  skus_count: 'SKU数',
  users_count: '用户数'
}

const chartOption = computed(() => {
  return {
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const data = params[0]
        return `${data.name}<br/>${metricLabels[chartMetric.value]}: ${data.value}`
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: trendData.value.map(item => item.time),
      axisLabel: {
        interval: 'auto',
        rotate: 45
      }
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      splitLine: {
        show: true,
        lineStyle: {
          type: 'dashed'
        }
      }
    },
    series: [
      {
        name: metricLabels[chartMetric.value],
        type: 'line',
        data: trendData.value.map(item => item[chartMetric.value]),
        smooth: true,
        showSymbol: true,
        symbolSize: 6,
        areaStyle: {
          opacity: 0.2,
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [{
              offset: 0,
              color: 'rgba(64, 158, 255, 0.2)'
            }, {
              offset: 1,
              color: 'rgba(64, 158, 255, 0)'
            }]
          }
        },
        lineStyle: {
          width: 3,
          color: '#409EFF'
        }
      }
    ]
  }
})

const fetchData = async () => {
  loading.value = true
  try {
    const response = await apiClient.get('/statistics')
    statistics.value = response.data
    
    const trendResponse = await apiClient.get('/statistics/trend')
    trendData.value = trendResponse.data
  } catch (error) {
    ElMessage.error('获取统计数据失败')
  } finally {
    loading.value = false
  }
}

const formatDate = (dateStr: string, short = false) => {
  return short ? toShortBeijingTime(dateStr) : toBeijingTime(dateStr) as string
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.statistics {
  padding: 20px 0;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

h2 {
  margin: 0;
  font-size: 24px;
  color: #303133;
}

.stats-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  margin-bottom: 20px;
}

.stats-card {
  text-align: center;
}

.stats-number {
  font-size: 36px;
  font-weight: bold;
  color: #409EFF;
}

.stats-number.success {
  color: #67C23A;
}

.stats-number.danger {
  color: #F56C6C;
}

.active-users {
  margin-top: 20px;
}

.user-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.user-name {
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 8px;
}

.user-uid {
  font-size: 12px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.trend-chart {
  margin-bottom: 20px;
}

.chart-container {
  height: 300px;
}

.chart {
  height: 100%;
}
</style> 