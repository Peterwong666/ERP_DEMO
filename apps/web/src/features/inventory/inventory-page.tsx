import { useEffect, useState } from 'react'
import { isAxiosError } from 'axios'
import { api } from '@/lib/api'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import type {
  AdjustForm,
  InventoryBalance,
  InventoryTransaction,
  LowStockRow,
  ReconciliationRow,
  StockType,
  TxnType,
} from './types'

const STOCK_LABELS: Record<StockType, string> = {
  available: '可用',
  pending: '待检',
  defective: '不良',
}

const TXN_LABELS: Record<TxnType, string> = {
  recv_inbound: '收货入库',
  qc_pass: '质检合格',
  qc_fail: '质检不良',
  manual_adjust: '手工调整',
  adjust_outbound: '调整出库',
}

function errorMessage(error: unknown, fallback: string): string {
  if (isAxiosError(error) && typeof error.response?.data?.detail === 'string') {
    return error.response.data.detail
  }
  return fallback
}

function formatTime(value: string): string {
  return value.slice(0, 19).replace('T', ' ')
}

function AdjustDialog({
  balances,
  submitting,
  error,
  form,
  onChangeForm,
  onClose,
  onSubmit,
}: {
  balances: InventoryBalance[]
  submitting: boolean
  error: string | null
  form: AdjustForm
  onChangeForm: (next: AdjustForm) => void
  onClose: () => void
  onSubmit: () => void
}) {
  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className='sm:max-w-md'>
        <DialogHeader>
          <DialogTitle>手工库存调整</DialogTitle>
          <DialogDescription>
            调整记入可用库存：正数入库、负数出库，每笔余额变动都有对应流水
          </DialogDescription>
        </DialogHeader>
        <div className='space-y-3'>
          <div className='grid gap-1.5'>
            <Label htmlFor='adjust-product'>商品</Label>
            <select
              id='adjust-product'
              className='h-9 rounded-md border px-3 text-sm'
              value={form.product_id}
              onChange={(event) =>
                onChangeForm({ ...form, product_id: event.target.value })
              }
            >
              <option value=''>选择商品</option>
              {balances.map((row) => (
                <option key={row.product_id} value={row.product_id}>
                  {row.sku_code}（{row.name}）
                </option>
              ))}
            </select>
          </div>
          <div className='grid gap-1.5'>
            <Label htmlFor='adjust-qty'>变动数量（正=入库，负=出库）</Label>
            <Input
              id='adjust-qty'
              type='number'
              step='1'
              value={form.change_qty}
              onChange={(event) =>
                onChangeForm({ ...form, change_qty: event.target.value })
              }
            />
          </div>
          <div className='grid gap-1.5'>
            <Label htmlFor='adjust-reason'>原因</Label>
            <Input
              id='adjust-reason'
              value={form.reason}
              onChange={(event) =>
                onChangeForm({ ...form, reason: event.target.value })
              }
            />
          </div>
          {error && <p className='text-sm text-destructive'>{error}</p>}
        </div>
        <DialogFooter>
          <Button variant='outline' onClick={onClose} disabled={submitting}>
            取消
          </Button>
          <Button onClick={onSubmit} disabled={submitting}>
            {submitting ? '提交中…' : '确认调整'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export function InventoryPage() {
  const [balances, setBalances] = useState<InventoryBalance[]>([])
  const [transactions, setTransactions] = useState<InventoryTransaction[]>([])
  const [reconciliation, setReconciliation] = useState<ReconciliationRow[]>([])
  const [reconLoaded, setReconLoaded] = useState(false)
  const [lowStock, setLowStock] = useState<LowStockRow[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)

  const [filters, setFilters] = useState({
    ref_doc_no: '',
    date_from: '',
    date_to: '',
  })

  const [adjustOpen, setAdjustOpen] = useState(false)
  const [adjustForm, setAdjustForm] = useState<AdjustForm>({
    product_id: '',
    change_qty: '',
    reason: '',
  })
  const [adjusting, setAdjusting] = useState(false)
  const [adjustError, setAdjustError] = useState<string | null>(null)

  const loadAll = () => {
    Promise.all([
      api.get<InventoryBalance[]>('/api/inventory'),
      api.get<ReconciliationRow[]>('/api/inventory/reconciliation'),
      api.get<LowStockRow[]>('/api/inventory/low-stock'),
    ])
      .then(([balanceRes, reconRes, lowRes]) => {
        setBalances(balanceRes.data)
        setReconciliation(reconRes.data)
        setReconLoaded(true)
        setLowStock(lowRes.data)
        setLoadError(null)
      })
      .catch((error) =>
        setLoadError(errorMessage(error, '数据加载失败，请确认 API 已启动'))
      )
      .finally(() => setLoading(false))
  }

  useEffect(loadAll, [])

  const searchTransactions = () => {
    api
      .get<InventoryTransaction[]>('/api/inventory/transactions', {
        params: {
          ref_doc_no: filters.ref_doc_no || undefined,
          date_from: filters.date_from || undefined,
          date_to: filters.date_to || undefined,
        },
      })
      .then((response) => {
        setTransactions(response.data)
        setLoadError(null)
      })
      .catch((error) =>
        setLoadError(errorMessage(error, '流水查询失败，请检查日期格式'))
      )
  }

  const openAdjust = () => {
    setAdjustForm({ product_id: '', change_qty: '', reason: '' })
    setAdjustError(null)
    setAdjustOpen(true)
  }

  const submitAdjust = () => {
    const productId = Number(adjustForm.product_id)
    const changeQty = Number(adjustForm.change_qty)
    if (!productId) {
      setAdjustError('请选择商品')
      return
    }
    if (!Number.isInteger(changeQty) || changeQty === 0) {
      setAdjustError('变动数量须为非 0 整数')
      return
    }
    if (!adjustForm.reason.trim()) {
      setAdjustError('请填写调整原因')
      return
    }
    setAdjusting(true)
    setAdjustError(null)
    api
      .post('/api/inventory/adjust', {
        product_id: productId,
        change_qty: changeQty,
        reason: adjustForm.reason.trim(),
      })
      .then(() => {
        setAdjustOpen(false)
        loadAll()
      })
      .catch((error) => setAdjustError(errorMessage(error, '调整失败')))
      .finally(() => setAdjusting(false))
  }

  return (
    <div className='space-y-4'>
      <div>
        <h1 className='text-xl font-semibold tracking-tight'>库存管理</h1>
        <p className='text-sm text-muted-foreground'>
          库存余额始终等于流水之和：余额、流水、对账与低库存监控
        </p>
      </div>

      {loadError && (
        <Card>
          <CardContent className='p-4 text-sm text-destructive'>
            {loadError}
          </CardContent>
        </Card>
      )}

      <Tabs defaultValue='balances'>
        <TabsList>
          <TabsTrigger value='balances'>库存余额</TabsTrigger>
          <TabsTrigger value='transactions'>流水查询</TabsTrigger>
          <TabsTrigger value='reconciliation'>对账</TabsTrigger>
          <TabsTrigger value='low-stock'>低库存</TabsTrigger>
        </TabsList>

        <TabsContent value='balances'>
          <Card>
            <CardContent className='p-4'>
              <div className='mb-3 flex justify-end'>
                <Button size='sm' onClick={openAdjust}>
                  手工调整
                </Button>
              </div>
              {loading ? (
                <Skeleton className='h-24 w-full' />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>SKU</TableHead>
                      <TableHead>名称</TableHead>
                      <TableHead className='text-right'>可用</TableHead>
                      <TableHead className='text-right'>待检</TableHead>
                      <TableHead className='text-right'>不良</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {balances.map((row) => (
                      <TableRow key={row.product_id}>
                        <TableCell className='font-mono'>
                          {row.sku_code}
                        </TableCell>
                        <TableCell>{row.name}</TableCell>
                        <TableCell className='text-right font-mono'>
                          {row.qty_available}
                        </TableCell>
                        <TableCell className='text-right font-mono'>
                          {row.qty_pending}
                        </TableCell>
                        <TableCell className='text-right font-mono'>
                          {row.qty_defective}
                        </TableCell>
                      </TableRow>
                    ))}
                    {balances.length === 0 && (
                      <TableRow>
                        <TableCell
                          colSpan={5}
                          className='h-20 text-center text-muted-foreground'
                        >
                          暂无库存数据
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value='transactions'>
          <Card>
            <CardContent className='p-4'>
              <div className='mb-3 flex flex-wrap items-end gap-2'>
                <div className='grid gap-1'>
                  <Label className='text-xs' htmlFor='filter-doc'>
                    单据号
                  </Label>
                  <Input
                    id='filter-doc'
                    className='h-8 w-44'
                    value={filters.ref_doc_no}
                    onChange={(event) =>
                      setFilters({ ...filters, ref_doc_no: event.target.value })
                    }
                  />
                </div>
                <div className='grid gap-1'>
                  <Label className='text-xs' htmlFor='filter-from'>
                    起始日期
                  </Label>
                  <Input
                    id='filter-from'
                    type='date'
                    className='h-8 w-40'
                    value={filters.date_from}
                    onChange={(event) =>
                      setFilters({ ...filters, date_from: event.target.value })
                    }
                  />
                </div>
                <div className='grid gap-1'>
                  <Label className='text-xs' htmlFor='filter-to'>
                    截止日期
                  </Label>
                  <Input
                    id='filter-to'
                    type='date'
                    className='h-8 w-40'
                    value={filters.date_to}
                    onChange={(event) =>
                      setFilters({ ...filters, date_to: event.target.value })
                    }
                  />
                </div>
                <Button size='sm' onClick={searchTransactions}>
                  查询
                </Button>
              </div>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>时间</TableHead>
                    <TableHead>SKU</TableHead>
                    <TableHead>类型</TableHead>
                    <TableHead>库存口径</TableHead>
                    <TableHead>单据号</TableHead>
                    <TableHead className='text-right'>变动</TableHead>
                    <TableHead>原因</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {transactions.map((txn) => (
                    <TableRow key={txn.txn_id}>
                      <TableCell className='font-mono text-xs whitespace-nowrap'>
                        {formatTime(txn.created_at)}
                      </TableCell>
                      <TableCell className='font-mono'>
                        {balances.find(
                          (row) => row.product_id === txn.product_id
                        )?.sku_code ?? txn.product_id}
                      </TableCell>
                      <TableCell>{TXN_LABELS[txn.txn_type]}</TableCell>
                      <TableCell>{STOCK_LABELS[txn.stock_type]}</TableCell>
                      <TableCell className='font-mono text-xs'>
                        {txn.ref_doc_no}
                      </TableCell>
                      <TableCell className='text-right font-mono'>
                        {txn.change_qty > 0
                          ? `+${txn.change_qty}`
                          : txn.change_qty}
                      </TableCell>
                      <TableCell className='text-xs text-muted-foreground'>
                        {txn.reason ?? '—'}
                      </TableCell>
                    </TableRow>
                  ))}
                  {transactions.length === 0 && (
                    <TableRow>
                      <TableCell
                        colSpan={7}
                        className='h-20 text-center text-muted-foreground'
                      >
                        请输入条件后点击「查询」
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value='reconciliation'>
          <Card>
            <CardContent className='p-4'>
              {reconLoaded ? (
                <Badge
                  variant={
                    reconciliation.length === 0 ? 'default' : 'destructive'
                  }
                >
                  {reconciliation.length === 0
                    ? '账实一致：全部商品余额与流水之和相符'
                    : `发现 ${reconciliation.length} 处不一致`}
                </Badge>
              ) : (
                <Badge variant='secondary'>对账数据未加载</Badge>
              )}
              {reconciliation.length > 0 && (
                <Table className='mt-3'>
                  <TableHeader>
                    <TableRow>
                      <TableHead>SKU</TableHead>
                      <TableHead>库存口径</TableHead>
                      <TableHead className='text-right'>账面余额</TableHead>
                      <TableHead className='text-right'>流水合计</TableHead>
                      <TableHead className='text-right'>差异</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {reconciliation.map((row) => (
                      <TableRow key={`${row.product_id}-${row.stock_type}`}>
                        <TableCell className='font-mono'>
                          {balances.find(
                            (balance) => balance.product_id === row.product_id
                          )?.sku_code ?? row.product_id}
                        </TableCell>
                        <TableCell>{STOCK_LABELS[row.stock_type]}</TableCell>
                        <TableCell className='text-right font-mono'>
                          {row.book_qty}
                        </TableCell>
                        <TableCell className='text-right font-mono'>
                          {row.ledger_qty}
                        </TableCell>
                        <TableCell className='text-right font-mono text-destructive'>
                          {row.book_qty - row.ledger_qty}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value='low-stock'>
          <Card>
            <CardContent className='p-4'>
              <p className='mb-3 text-sm text-muted-foreground'>
                低库存规则：可用量 ≤ 安全库存，或近 7 日销量推算可售天数低于 14
                天（阈值可在系统设置调整）
              </p>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>SKU</TableHead>
                    <TableHead>名称</TableHead>
                    <TableHead className='text-right'>可用</TableHead>
                    <TableHead className='text-right'>安全库存</TableHead>
                    <TableHead className='text-right'>可售天数</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {lowStock.map((row) => (
                    <TableRow key={row.product_id}>
                      <TableCell className='font-mono'>
                        {row.sku_code}
                      </TableCell>
                      <TableCell>{row.name}</TableCell>
                      <TableCell className='text-right font-mono'>
                        {row.qty_available}
                      </TableCell>
                      <TableCell className='text-right font-mono'>
                        {row.safety_stock}
                      </TableCell>
                      <TableCell className='text-right font-mono'>
                        {row.days_cover === null ? '无销量' : row.days_cover}
                      </TableCell>
                    </TableRow>
                  ))}
                  {lowStock.length === 0 && (
                    <TableRow>
                      <TableCell
                        colSpan={5}
                        className='h-20 text-center text-muted-foreground'
                      >
                        暂无低库存 SKU
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {adjustOpen && (
        <AdjustDialog
          balances={balances}
          submitting={adjusting}
          error={adjustError}
          form={adjustForm}
          onChangeForm={setAdjustForm}
          onClose={() => !adjusting && setAdjustOpen(false)}
          onSubmit={submitAdjust}
        />
      )}
    </div>
  )
}
