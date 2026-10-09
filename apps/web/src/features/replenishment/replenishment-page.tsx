import { useEffect, useState } from 'react'
import { isAxiosError } from 'axios'
import { api } from '@/lib/api'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  URGENCY_LABELS,
  type ReplenishmentSuggestion,
  type Urgency,
} from './types'

type BadgeVariant = 'destructive' | 'secondary' | 'outline'

function urgencyVariant(urgency: Urgency): BadgeVariant {
  if (urgency === 'emergency') return 'destructive'
  if (urgency === 'suggest') return 'secondary'
  return 'outline'
}

function errorMessage(error: unknown, fallback: string): string {
  if (isAxiosError(error) && typeof error.response?.data?.detail === 'string') {
    return error.response.data.detail
  }
  return fallback
}

export function ReplenishmentPage() {
  const [suggestions, setSuggestions] = useState<ReplenishmentSuggestion[]>([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)

  const loadSuggestions = () => {
    api
      .get<ReplenishmentSuggestion[]>('/api/replenishment')
      .then((response) => {
        setSuggestions(response.data)
        setLoadError(null)
      })
      .catch((error) =>
        setLoadError(errorMessage(error, '数据加载失败，请确认 API 已启动'))
      )
      .finally(() => setLoading(false))
  }

  useEffect(loadSuggestions, [])

  const generate = () => {
    setGenerating(true)
    setLoadError(null)
    api
      .post<ReplenishmentSuggestion[]>('/api/replenishment/generate')
      .then((response) => setSuggestions(response.data))
      .catch((error) => setLoadError(errorMessage(error, '补货建议生成失败')))
      .finally(() => setGenerating(false))
  }

  const emergencyCount = suggestions.filter(
    (row) => row.urgency === 'emergency'
  ).length
  const suggestCount = suggestions.filter(
    (row) => row.urgency === 'suggest'
  ).length

  return (
    <div className='space-y-4'>
      <div className='flex items-start justify-between gap-4'>
        <div>
          <h1 className='text-xl font-semibold tracking-tight'>补货管理</h1>
          <p className='text-sm text-muted-foreground'>
            基于近 7 日销量与在途量计算可售天数，按紧急/建议/正常三档给出补货量
          </p>
        </div>
        <Button onClick={generate} disabled={generating}>
          {generating ? '生成中…' : '生成补货建议'}
        </Button>
      </div>

      {loadError && (
        <Card>
          <CardContent className='p-4 text-sm text-destructive'>
            {loadError}
          </CardContent>
        </Card>
      )}

      {suggestions.length > 0 && (
        <div className='flex gap-2 text-sm'>
          <Badge variant='destructive'>紧急 {emergencyCount}</Badge>
          <Badge variant='secondary'>建议 {suggestCount}</Badge>
          <Badge variant='outline'>
            正常 {suggestions.length - emergencyCount - suggestCount}
          </Badge>
        </div>
      )}

      <Card>
        <CardContent className='p-0'>
          {loading ? (
            <div className='space-y-2 p-4'>
              {Array.from({ length: 8 }).map((_, index) => (
                <Skeleton key={index} className='h-8 w-full' />
              ))}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>紧急度</TableHead>
                  <TableHead>SKU</TableHead>
                  <TableHead>名称</TableHead>
                  <TableHead className='text-right'>当前库存</TableHead>
                  <TableHead className='text-right'>在途</TableHead>
                  <TableHead className='text-right'>7 日预测</TableHead>
                  <TableHead className='text-right'>可售天数</TableHead>
                  <TableHead className='text-right'>建议补货量</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {suggestions.map((row) => (
                  <TableRow key={row.suggestion_id}>
                    <TableCell>
                      <Badge variant={urgencyVariant(row.urgency)}>
                        {URGENCY_LABELS[row.urgency]}
                      </Badge>
                    </TableCell>
                    <TableCell className='font-mono'>{row.sku_code}</TableCell>
                    <TableCell>{row.name}</TableCell>
                    <TableCell className='text-right font-mono'>
                      {row.current_stock}
                    </TableCell>
                    <TableCell className='text-right font-mono'>
                      {row.qty_in_transit}
                    </TableCell>
                    <TableCell className='text-right font-mono'>
                      {row.forecast_7d}
                    </TableCell>
                    <TableCell className='text-right font-mono'>
                      {row.days_cover === null ? '—' : row.days_cover}
                    </TableCell>
                    <TableCell className='text-right font-mono font-semibold'>
                      {row.suggested_qty}
                    </TableCell>
                  </TableRow>
                ))}
                {suggestions.length === 0 && (
                  <TableRow>
                    <TableCell
                      colSpan={8}
                      className='h-20 text-center text-muted-foreground'
                    >
                      暂无建议，点击右上角「生成补货建议」
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
