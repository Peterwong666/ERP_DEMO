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
import { ConfirmDialog } from '@/components/confirm-dialog'
import type { Product } from '../products/types'
import {
  EMPTY_PO_FORM,
  PO_STATUS_LABELS,
  type POFormValues,
  type POStatus,
  type PurchaseOrder,
  type SupplierOption,
} from './types'

type PendingAction = { kind: 'place' | 'cancel'; po: PurchaseOrder } | null

function statusVariant(
  status: POStatus
): 'default' | 'secondary' | 'destructive' | 'outline' {
  switch (status) {
    case 'ordered':
    case 'received':
      return 'default'
    case 'cancelled':
      return 'destructive'
    case 'draft':
      return 'secondary'
    default:
      return 'outline'
  }
}

function errorMessage(error: unknown, fallback: string): string {
  if (isAxiosError(error) && typeof error.response?.data?.detail === 'string') {
    return error.response.data.detail
  }
  return fallback
}

function POFormDialog({
  form,
  suppliers,
  products,
  submitting,
  error,
  onClose,
  onChange,
  onSubmit,
}: {
  form: POFormValues
  suppliers: SupplierOption[]
  products: Product[]
  submitting: boolean
  error: string | null
  onClose: () => void
  onChange: (next: POFormValues) => void
  onSubmit: () => void
}) {
  const updateLine = (
    index: number,
    field: 'product_id' | 'qty_ordered' | 'unit_price',
    value: string
  ) =>
    onChange({
      ...form,
      lines: form.lines.map((line, i) =>
        i === index ? { ...line, [field]: value } : line
      ),
    })

  const addLine = () =>
    onChange({
      ...form,
      lines: [
        ...form.lines,
        { product_id: '', qty_ordered: '', unit_price: '' },
      ],
    })

  const removeLine = (index: number) =>
    onChange({
      ...form,
      lines: form.lines.filter((_, i) => i !== index),
    })

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className='max-h-[90vh] overflow-y-auto sm:max-w-2xl'>
        <DialogHeader>
          <DialogTitle>新建采购单</DialogTitle>
        </DialogHeader>
        <div className='space-y-3'>
          <div className='grid grid-cols-2 gap-3'>
            <div className='grid gap-1.5'>
              <Label>供应商</Label>
              <Select
                value={form.supplier_id}
                onValueChange={(value) =>
                  onChange({ ...form, supplier_id: value })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder='选择供应商' />
                </SelectTrigger>
                <SelectContent>
                  {suppliers.map((supplier) => (
                    <SelectItem
                      key={supplier.supplier_id}
                      value={String(supplier.supplier_id)}
                    >
                      {supplier.code} · {supplier.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className='grid gap-1.5'>
              <Label htmlFor='po-notes'>备注（可选）</Label>
              <Input
                id='po-notes'
                value={form.notes}
                onChange={(event) =>
                  onChange({ ...form, notes: event.target.value })
                }
              />
            </div>
          </div>

          <div className='space-y-2'>
            <div className='flex items-center justify-between'>
              <Label>采购明细</Label>
              <Button size='sm' variant='outline' onClick={addLine}>
                添加行
              </Button>
            </div>
            {form.lines.map((line, index) => (
              <div
                key={index}
                className='grid grid-cols-[1fr_120px_120px_40px] items-center gap-2'
              >
                <Select
                  value={line.product_id}
                  onValueChange={(value) =>
                    updateLine(index, 'product_id', value)
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder='选择 SKU' />
                  </SelectTrigger>
                  <SelectContent>
                    {products.map((product) => (
                      <SelectItem
                        key={product.product_id}
                        value={String(product.product_id)}
                      >
                        {product.sku_code} · {product.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Input
                  type='number'
                  min='1'
                  placeholder='数量'
                  value={line.qty_ordered}
                  onChange={(event) =>
                    updateLine(index, 'qty_ordered', event.target.value)
                  }
                />
                <Input
                  type='number'
                  min='0'
                  step='0.01'
                  placeholder='单价'
                  value={line.unit_price}
                  onChange={(event) =>
                    updateLine(index, 'unit_price', event.target.value)
                  }
                />
                <Button
                  type='button'
                  variant='ghost'
                  size='sm'
                  disabled={form.lines.length === 1}
                  onClick={() => removeLine(index)}
                >
                  ✕
                </Button>
              </div>
            ))}
          </div>
          {error && <p className='text-sm text-destructive'>{error}</p>}
        </div>
        <DialogFooter>
          <Button variant='outline' onClick={onClose} disabled={submitting}>
            取消
          </Button>
          <Button onClick={onSubmit} disabled={submitting}>
            {submitting ? '提交中…' : '保存草稿'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function PODetailDialog({
  po,
  products,
  suppliers,
  onClose,
}: {
  po: PurchaseOrder
  products: Product[]
  suppliers: SupplierOption[]
  onClose: () => void
}) {
  const productById = new Map(
    products.map((product) => [product.product_id, product])
  )
  const supplierName =
    suppliers.find((s) => s.supplier_id === po.supplier_id)?.name ?? ''

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className='max-h-[90vh] overflow-y-auto sm:max-w-2xl'>
        <DialogHeader>
          <DialogTitle className='font-mono'>{po.po_no}</DialogTitle>
        </DialogHeader>
        <div className='space-y-3 text-sm'>
          <div className='flex justify-between'>
            <span className='text-muted-foreground'>
              供应商：{supplierName}
            </span>
            <Badge variant={statusVariant(po.status)}>
              {PO_STATUS_LABELS[po.status]}
            </Badge>
          </div>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>SKU</TableHead>
                <TableHead className='text-right'>订购</TableHead>
                <TableHead className='text-right'>已收</TableHead>
                <TableHead className='text-right'>在途</TableHead>
                <TableHead className='text-right'>单价</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {po.items.map((item) => (
                <TableRow key={item.item_id}>
                  <TableCell className='font-mono'>
                    {productById.get(item.product_id)?.sku_code ??
                      item.product_id}
                  </TableCell>
                  <TableCell className='text-right font-mono'>
                    {item.qty_ordered}
                  </TableCell>
                  <TableCell className='text-right font-mono'>
                    {item.qty_received}
                  </TableCell>
                  <TableCell className='text-right font-mono'>
                    {item.qty_ordered - item.qty_received}
                  </TableCell>
                  <TableCell className='text-right font-mono'>
                    {item.unit_price}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <p className='text-muted-foreground'>备注：{po.notes ?? '—'}</p>
        </div>
      </DialogContent>
    </Dialog>
  )
}

export function PurchaseOrdersPage() {
  const [orders, setOrders] = useState<PurchaseOrder[]>([])
  const [suppliers, setSuppliers] = useState<SupplierOption[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)

  const [createOpen, setCreateOpen] = useState(false)
  const [form, setForm] = useState<POFormValues>(EMPTY_PO_FORM)
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [detailPo, setDetailPo] = useState<PurchaseOrder | null>(null)
  const [pendingAction, setPendingAction] = useState<PendingAction>(null)

  const loadAll = () => {
    Promise.all([
      api.get<PurchaseOrder[]>('/api/purchase-orders'),
      api.get<SupplierOption[]>('/api/suppliers'),
      api.get<Product[]>('/api/products'),
    ])
      .then(([poResponse, supplierResponse, productResponse]) => {
        setOrders(poResponse.data)
        setSuppliers(supplierResponse.data)
        setProducts(productResponse.data)
        setLoadError(null)
      })
      .catch((error) =>
        setLoadError(
          errorMessage(
            error,
            '数据加载失败，请确认 API 已启动且已执行 make seed'
          )
        )
      )
      .finally(() => setLoading(false))
  }

  useEffect(loadAll, [])

  const openCreate = () => {
    setForm(EMPTY_PO_FORM)
    setFormError(null)
    setCreateOpen(true)
  }

  const submitCreate = () => {
    const isValid =
      form.supplier_id !== '' &&
      form.lines.length > 0 &&
      form.lines.every(
        (line) =>
          line.product_id !== '' &&
          Number(line.qty_ordered) > 0 &&
          Number(line.unit_price) >= 0
      )
    if (!isValid) {
      setFormError(
        '请选择供应商，并为每一行选择 SKU、填写大于 0 的数量与非负单价'
      )
      return
    }
    setSubmitting(true)
    setFormError(null)
    api
      .post('/api/purchase-orders', {
        supplier_id: Number(form.supplier_id),
        notes: form.notes.trim() ? form.notes : null,
        items: form.lines.map((line) => ({
          product_id: Number(line.product_id),
          qty_ordered: Number(line.qty_ordered),
          unit_price: line.unit_price,
        })),
      })
      .then(() => {
        setCreateOpen(false)
        loadAll()
      })
      .catch((error) => setFormError(errorMessage(error, '创建失败')))
      .finally(() => setSubmitting(false))
  }

  const confirmAction = () => {
    if (!pendingAction) return
    const { kind, po } = pendingAction
    const path =
      kind === 'place'
        ? `/api/purchase-orders/${po.po_id}/place`
        : `/api/purchase-orders/${po.po_id}/cancel`
    api
      .post(path)
      .then(() => {
        setPendingAction(null)
        loadAll()
      })
      .catch((error) => {
        setPendingAction(null)
        setLoadError(errorMessage(error, '操作失败'))
      })
  }

  const supplierNameOf = (po: PurchaseOrder) =>
    suppliers.find((s) => s.supplier_id === po.supplier_id)?.name ?? ''

  return (
    <div className='space-y-4'>
      <div className='flex items-center justify-between gap-4'>
        <div>
          <h1 className='text-xl font-semibold tracking-tight'>采购管理</h1>
          <p className='text-sm text-muted-foreground'>
            采购单创建、下单与进度跟踪
          </p>
        </div>
        <Button onClick={openCreate}>新建采购单</Button>
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
                  <TableHead>采购单号</TableHead>
                  <TableHead>供应商</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead className='text-right'>行数</TableHead>
                  <TableHead className='text-right'>总金额</TableHead>
                  <TableHead>下单日期</TableHead>
                  <TableHead>预计到货</TableHead>
                  <TableHead className='text-right'>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {orders.map((po) => (
                  <TableRow key={po.po_id}>
                    <TableCell className='font-mono'>{po.po_no}</TableCell>
                    <TableCell>{supplierNameOf(po)}</TableCell>
                    <TableCell>
                      <Badge variant={statusVariant(po.status)}>
                        {PO_STATUS_LABELS[po.status]}
                      </Badge>
                    </TableCell>
                    <TableCell className='text-right font-mono'>
                      {po.items.length}
                    </TableCell>
                    <TableCell className='text-right font-mono'>
                      {po.total_amount}
                    </TableCell>
                    <TableCell>{po.order_date ?? '—'}</TableCell>
                    <TableCell>{po.expected_date ?? '—'}</TableCell>
                    <TableCell className='text-right'>
                      <div className='flex justify-end gap-2'>
                        <Button
                          size='sm'
                          variant='outline'
                          onClick={() => setDetailPo(po)}
                        >
                          明细
                        </Button>
                        {po.status === 'draft' && (
                          <>
                            <Button
                              size='sm'
                              onClick={() =>
                                setPendingAction({ kind: 'place', po })
                              }
                            >
                              下单
                            </Button>
                            <Button
                              size='sm'
                              variant='outline'
                              onClick={() =>
                                setPendingAction({ kind: 'cancel', po })
                              }
                            >
                              取消
                            </Button>
                          </>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
                {orders.length === 0 && (
                  <TableRow>
                    <TableCell
                      colSpan={8}
                      className='h-20 text-center text-muted-foreground'
                    >
                      暂无采购单
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {createOpen && (
        <POFormDialog
          form={form}
          suppliers={suppliers}
          products={products}
          submitting={submitting}
          error={formError}
          onClose={() => !submitting && setCreateOpen(false)}
          onChange={setForm}
          onSubmit={submitCreate}
        />
      )}

      {detailPo && (
        <PODetailDialog
          po={detailPo}
          products={products}
          suppliers={suppliers}
          onClose={() => setDetailPo(null)}
        />
      )}

      {pendingAction && (
        <ConfirmDialog
          open
          onOpenChange={(open) => !open && setPendingAction(null)}
          title={pendingAction.kind === 'place' ? '确认下单' : '确认取消采购单'}
          desc={
            pendingAction.kind === 'place'
              ? `确认对 ${pendingAction.po.po_no} 执行下单？下单后可安排收货。`
              : `确认取消 ${pendingAction.po.po_no}？取消后不可恢复。`
          }
          confirmText={pendingAction.kind === 'place' ? '下单' : '取消采购单'}
          destructive={pendingAction.kind === 'cancel'}
          cancelBtnText='返回'
          handleConfirm={confirmAction}
        />
      )}
    </div>
  )
}
