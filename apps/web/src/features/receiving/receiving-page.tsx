import { useEffect, useState } from 'react'
import { isAxiosError } from 'axios'
import { api } from '@/lib/api'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import type { Product } from '../products/types'
import type { POStatus, PurchaseOrder } from '../purchase-orders/types'
import {
  RECV_STATUS_LABELS,
  type RecvFormLine,
  type RecvStatus,
  type ReceivingOrder,
} from './types'

const OPEN_PO_STATUSES: POStatus[] = ['ordered', 'partial_received']

function statusVariant(
  status: RecvStatus
): 'default' | 'secondary' | 'outline' {
  if (status === 'completed') return 'default'
  if (status === 'inspecting') return 'secondary'
  return 'outline'
}

function errorMessage(error: unknown, fallback: string): string {
  if (isAxiosError(error) && typeof error.response?.data?.detail === 'string') {
    return error.response.data.detail
  }
  return fallback
}

function skuLabel(products: Product[], productId: number): string {
  return (
    products.find((product) => product.product_id === productId)?.sku_code ??
    String(productId)
  )
}

function RecvFormDialog({
  orders,
  products,
  submitting,
  error,
  onClose,
  onSelectPo,
  formLines,
  onChangeLine,
  onSubmit,
}: {
  orders: PurchaseOrder[]
  products: Product[]
  submitting: boolean
  error: string | null
  onClose: () => void
  onSelectPo: (po: PurchaseOrder) => void
  formLines: RecvFormLine[]
  onChangeLine: (index: number, qty: string) => void
  onSubmit: () => void
}) {
  const [poId, setPoId] = useState('')
  const selectedPo = orders.find((o) => String(o.po_id) === poId)

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className='max-h-[90vh] overflow-y-auto sm:max-w-2xl'>
        <DialogHeader>
          <DialogTitle>新建收货单</DialogTitle>
        </DialogHeader>
        <div className='space-y-3'>
          <div className='grid gap-1.5'>
            <Label>采购单</Label>
            <Select
              value={poId}
              onValueChange={(value) => {
                setPoId(value)
                const po = orders.find((o) => String(o.po_id) === value)
                if (po) onSelectPo(po)
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder='选择待收货采购单' />
              </SelectTrigger>
              <SelectContent>
                {orders.map((po) => (
                  <SelectItem key={po.po_id} value={String(po.po_id)}>
                    {po.po_no}（
                    {po.status === 'partial_received' ? '部分收货' : '已下单'}）
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {formLines.length > 0 && (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>SKU</TableHead>
                  <TableHead className='text-right'>订购</TableHead>
                  <TableHead className='text-right'>已收</TableHead>
                  <TableHead className='text-right'>未交</TableHead>
                  <TableHead className='text-right'>本次收货</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {formLines.map((line, index) => {
                  const poLine = selectedPo?.items.find(
                    (i) => i.item_id === line.po_item_id
                  )
                  return (
                    <TableRow key={line.po_item_id}>
                      <TableCell className='font-mono'>
                        {skuLabel(products, line.product_id)}
                      </TableCell>
                      <TableCell className='text-right font-mono'>
                        {poLine?.qty_ordered}
                      </TableCell>
                      <TableCell className='text-right font-mono'>
                        {poLine?.qty_received}
                      </TableCell>
                      <TableCell className='text-right font-mono'>
                        {poLine ? poLine.qty_ordered - poLine.qty_received : 0}
                      </TableCell>
                      <TableCell>
                        <Input
                          type='number'
                          min='0'
                          step='1'
                          className='h-8 text-right'
                          value={line.qty_received}
                          onChange={(event) =>
                            onChangeLine(index, event.target.value)
                          }
                        />
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          )}
          {error && <p className='text-sm text-destructive'>{error}</p>}
        </div>
        <DialogFooter>
          <Button variant='outline' onClick={onClose} disabled={submitting}>
            取消
          </Button>
          <Button onClick={onSubmit} disabled={submitting}>
            {submitting ? '提交中…' : '确认收货'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function RecvDetailDialog({
  recv,
  products,
  onClose,
}: {
  recv: ReceivingOrder
  products: Product[]
  onClose: () => void
}) {
  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className='sm:max-w-lg'>
        <DialogHeader>
          <DialogTitle className='font-mono'>{recv.recv_no}</DialogTitle>
        </DialogHeader>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>SKU</TableHead>
              <TableHead className='text-right'>收货数量</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {recv.items.map((item) => (
              <TableRow key={item.recv_item_id}>
                <TableCell className='font-mono'>
                  {skuLabel(products, item.product_id)}
                </TableCell>
                <TableCell className='text-right font-mono'>
                  {item.qty_received}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </DialogContent>
    </Dialog>
  )
}

export function ReceivingPage() {
  const [orders, setOrders] = useState<PurchaseOrder[]>([])
  const [receiving, setReceiving] = useState<ReceivingOrder[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)

  const [createOpen, setCreateOpen] = useState(false)
  const [formPoId, setFormPoId] = useState<number | null>(null)
  const [formLines, setFormLines] = useState<RecvFormLine[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [detailRecv, setDetailRecv] = useState<ReceivingOrder | null>(null)

  const loadAll = () => {
    Promise.all([
      api.get<PurchaseOrder[]>('/api/purchase-orders'),
      api.get<ReceivingOrder[]>('/api/receiving'),
      api.get<Product[]>('/api/products'),
    ])
      .then(([poResponse, recvResponse, productResponse]) => {
        setOrders(poResponse.data)
        setReceiving(recvResponse.data)
        setProducts(productResponse.data)
        setLoadError(null)
      })
      .catch((error) =>
        setLoadError(errorMessage(error, '数据加载失败，请确认 API 已启动'))
      )
      .finally(() => setLoading(false))
  }

  useEffect(loadAll, [])

  const openCreate = () => {
    setFormPoId(null)
    setFormLines([])
    setFormError(null)
    setCreateOpen(true)
  }

  const selectPo = (po: PurchaseOrder) => {
    setFormPoId(po.po_id)
    setFormLines(
      po.items.map((item) => ({
        po_item_id: item.item_id,
        product_id: item.product_id,
        qty_received: String(item.qty_ordered - item.qty_received),
      }))
    )
  }

  const changeLine = (index: number, qty: string) =>
    setFormLines((lines) =>
      lines.map((line, i) =>
        i === index ? { ...line, qty_received: qty } : line
      )
    )

  const submitCreate = () => {
    if (formPoId === null) {
      setFormError('请先选择采购单')
      return
    }
    const selectedPo = orders.find((po) => po.po_id === formPoId)
    const invalidRow = formLines
      .map((line) => {
        const poLine = selectedPo?.items.find(
          (item) => item.item_id === line.po_item_id
        )
        return {
          sku: poLine ? skuLabel(products, poLine.product_id) : '',
          qty: Number(line.qty_received),
          remaining: poLine ? poLine.qty_ordered - poLine.qty_received : 0,
        }
      })
      .find(
        (row) =>
          row.qty !== 0 &&
          (!Number.isInteger(row.qty) || row.qty < 1 || row.qty > row.remaining)
      )
    if (invalidRow) {
      setFormError(
        `${invalidRow.sku} 本次收货须为 1-${invalidRow.remaining} 的整数（当前：${invalidRow.qty}）`
      )
      return
    }
    const lines = formLines
      .map((line) => ({
        po_item_id: line.po_item_id,
        qty_received: Number(line.qty_received),
      }))
      .filter((line) => line.qty_received > 0)
    if (lines.length === 0) {
      setFormError('至少一行收货数量大于 0')
      return
    }
    setSubmitting(true)
    setFormError(null)
    api
      .post(`/api/receiving/po/${formPoId}`, { lines })
      .then(() => {
        setCreateOpen(false)
        loadAll()
      })
      .catch((error) => setFormError(errorMessage(error, '收货失败')))
      .finally(() => setSubmitting(false))
  }

  const poNoOf = (poId: number) =>
    orders.find((po) => po.po_id === poId)?.po_no ?? String(poId)

  const openOrders = orders.filter((po) => OPEN_PO_STATUSES.includes(po.status))

  return (
    <div className='space-y-4'>
      <div className='flex items-center justify-between gap-4'>
        <div>
          <h1 className='text-xl font-semibold tracking-tight'>收货管理</h1>
          <p className='text-sm text-muted-foreground'>
            对已下单采购单登记收货，库存按系统口径自动过账
          </p>
        </div>
        <Button onClick={openCreate}>新建收货单</Button>
      </div>

      {loadError && (
        <Card>
          <CardContent className='p-4 text-sm text-destructive'>
            {loadError}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent className='p-0'>
          {loading ? (
            <div className='space-y-2 p-4'>
              {Array.from({ length: 6 }).map((_, index) => (
                <Skeleton key={index} className='h-8 w-full' />
              ))}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>收货单号</TableHead>
                  <TableHead>采购单号</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>收货时间</TableHead>
                  <TableHead className='text-right'>行数</TableHead>
                  <TableHead className='text-right'>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {receiving.map((recv) => (
                  <TableRow key={recv.recv_id}>
                    <TableCell className='font-mono'>{recv.recv_no}</TableCell>
                    <TableCell className='font-mono'>
                      {poNoOf(recv.po_id)}
                    </TableCell>
                    <TableCell>
                      <Badge variant={statusVariant(recv.status)}>
                        {RECV_STATUS_LABELS[recv.status]}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {recv.received_at.slice(0, 19).replace('T', ' ')}
                    </TableCell>
                    <TableCell className='text-right font-mono'>
                      {recv.items.length}
                    </TableCell>
                    <TableCell className='text-right'>
                      <Button
                        size='sm'
                        variant='outline'
                        onClick={() => setDetailRecv(recv)}
                      >
                        明细
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
                {receiving.length === 0 && (
                  <TableRow>
                    <TableCell
                      colSpan={6}
                      className='h-20 text-center text-muted-foreground'
                    >
                      暂无收货单
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {createOpen && (
        <RecvFormDialog
          orders={openOrders}
          products={products}
          submitting={submitting}
          error={formError}
          onClose={() => !submitting && setCreateOpen(false)}
          onSelectPo={selectPo}
          formLines={formLines}
          onChangeLine={changeLine}
          onSubmit={submitCreate}
        />
      )}

      {detailRecv && (
        <RecvDetailDialog
          recv={detailRecv}
          products={products}
          onClose={() => setDetailRecv(null)}
        />
      )}
    </div>
  )
}
