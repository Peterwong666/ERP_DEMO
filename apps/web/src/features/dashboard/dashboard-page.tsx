import { useEffect, useState } from 'react'
import {
  Area,
  AreaChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { api } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import type { DashboardData } from './types'

const DEFECT_COLORS = [
  '#ef4444',
  '#f97316',
  '#eab308',
  '#22c55e',
  '#3b82f6',
  '#94a3b8',
]

const METRIC_CARDS: Array<{
  label: string
  field: keyof DashboardData
  unit: string
  accent?: boolean
}> = [
  { label: '待收货 PO', field: 'open_po_count', unit: '笔' },
  { label: '待质检', field: 'pending_qc_count', unit: '批' },
  { label: '今日入库', field: 'inbound_today_qty', unit: '件', accent: true },
  { label: '可用库存', field: 'available_sku_count', unit: 'SKU' },
  { label: '质检良率', field: 'qc_pass_rate', unit: '%', accent: true },
  { label: '低库存预警', field: 'low_stock_count', unit: '个 SKU' },
  { label: '补货建议', field: 'suggestion_count', unit: '个 SKU' },
  { label: '不良总数', field: 'defect_total_today', unit: '件' },
]

function formatValue(value: number | string): string {
  return typeof value === 'number' ? value.toLocaleString('zh-CN') : value
}

function trendLabels(anchorDate: string): string[] {
  const anchor = new Date(`${anchorDate}T00:00:00`)
  const labels: string[] = []
  for (let offset = 6; offset >= 0; offset -= 1) {
    const day = new Date(anchor)
    day.setDate(day.getDate() - offset)
    labels.push(`${day.getMonth() + 1}/${day.getDate()}`)
  }
  return labels
}

function MetricCards({ data }: { data: DashboardData }) {
  return (
    <div className='grid grid-cols-2 gap-4 md:grid-cols-4'>
      {METRIC_CARDS.map((card) => (
        <Card
          key={card.label}
          className={card.accent ? 'border-primary/30' : undefined}
        >
          <CardContent className='p-4'>
            <p className='text-sm text-muted-foreground'>{card.label}</p>
            <p className='mt-2 font-mono text-2xl font-semibold tracking-tight'>
              {formatValue(data[card.field] as number)}
              <span className='ml-1 text-sm font-normal text-muted-foreground'>
                {card.unit}
              </span>
            </p>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

function InboundTrend({ data }: { data: DashboardData }) {
  const labels = trendLabels(data.anchor_date)
  const chartData = data.inbound_last_7d.map((qty, index) => ({
    label: labels[index],
    qty,
  }))
  return (
    <Card>
      <CardHeader>
        <CardTitle className='text-base'>近 7 日入库趋势（件）</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width='100%' height={260}>
          <AreaChart
            data={chartData}
            margin={{ top: 8, right: 16, bottom: 0, left: 0 }}
          >
            <defs>
              <linearGradient id='inboundFill' x1='0' y1='0' x2='0' y2='1'>
                <stop offset='0%' stopColor='#155dfc' stopOpacity={0.25} />
                <stop offset='100%' stopColor='#155dfc' stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <XAxis
              dataKey='label'
              fontSize={12}
              tickLine={false}
              axisLine={false}
            />
            <YAxis fontSize={12} tickLine={false} axisLine={false} width={48} />
            <Tooltip
              formatter={(value) => [formatValue(value as number), '入库量']}
              labelStyle={{ fontFamily: 'Inter' }}
            />
            <Area
              type='monotone'
              dataKey='qty'
              stroke='#155dfc'
              strokeWidth={2}
              fill='url(#inboundFill)'
            />
          </AreaChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}

function DefectDonut({ data }: { data: DashboardData }) {
  const chartData = data.defect_shares.map((share) => ({
    name: share.reason_label,
    value: share.qty,
  }))
  return (
    <Card>
      <CardHeader>
        <CardTitle className='text-base'>今日不良原因分布</CardTitle>
      </CardHeader>
      <CardContent className='flex flex-col items-center gap-4 sm:flex-row sm:flex-wrap'>
        <div className='relative h-[220px] w-[220px] shrink-0'>
          <ResponsiveContainer width='100%' height='100%'>
            <PieChart>
              <Pie
                data={chartData}
                dataKey='value'
                nameKey='name'
                innerRadius={68}
                outerRadius={92}
                paddingAngle={2}
                strokeWidth={0}
              >
                {chartData.map((entry, index) => (
                  <Cell key={entry.name} fill={DEFECT_COLORS[index]} />
                ))}
              </Pie>
              <Tooltip formatter={(value) => [`${value} 件`, '数量']} />
            </PieChart>
          </ResponsiveContainer>
          <div className='pointer-events-none absolute inset-0 flex flex-col items-center justify-center'>
            <span className='font-mono text-2xl font-semibold'>
              {data.defect_total_today}
            </span>
            <span className='text-xs text-muted-foreground'>不良总数</span>
          </div>
        </div>
        <ul className='min-w-[200px] flex-1 space-y-2 text-sm'>
          {data.defect_shares.map((share, index) => (
            <li
              key={share.reason_code}
              className='flex items-center justify-between gap-2'
            >
              <span className='flex items-center gap-2 whitespace-nowrap'>
                <span
                  className='inline-block h-2.5 w-2.5 rounded-full'
                  style={{ backgroundColor: DEFECT_COLORS[index] }}
                />
                {share.reason_label}
              </span>
              <span className='font-mono whitespace-nowrap text-muted-foreground'>
                {share.qty} 件 ·{' '}
                {((share.qty / data.defect_total_today) * 100).toFixed(1)}%
              </span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  )
}

export function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .get<DashboardData>('/api/dashboard')
      .then((response) => setData(response.data))
      .catch(() =>
        setError('看板数据加载失败，请确认 API 已启动且已执行 make seed')
      )
  }, [])

  if (error) {
    return (
      <Card>
        <CardContent className='p-6 text-sm text-destructive'>
          {error}
        </CardContent>
      </Card>
    )
  }

  if (!data) {
    return (
      <div className='space-y-4'>
        <Skeleton className='h-24 w-full' />
        <Skeleton className='h-72 w-full' />
      </div>
    )
  }

  return (
    <div className='space-y-4'>
      <div>
        <h1 className='text-xl font-semibold tracking-tight'>供应链数据看板</h1>
        <p className='text-sm text-muted-foreground'>
          PeterWong演示项目 · 数据截至 {data.anchor_date}
        </p>
      </div>
      <MetricCards data={data} />
      <div className='grid gap-4 lg:grid-cols-5'>
        <div className='lg:col-span-3'>
          <InboundTrend data={data} />
        </div>
        <div className='lg:col-span-2'>
          <DefectDonut data={data} />
        </div>
      </div>
    </div>
  )
}
