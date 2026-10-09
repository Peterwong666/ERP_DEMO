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
import type { ReceivingOrder } from '../receiving/types'
import {
  DEFECT_REASON_OPTIONS,
  INSP_STATUS_LABELS,
  type DefectFormLine,
  type InspectionOrder,
  type InspectionStatus,
  type ItemResultForm,
} from './types'

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

function buildItemForms(insp: InspectionOrder): ItemResultForm[] {
  return insp.items.map((item) => ({
    insp_item_id: item.insp_item_id,
    qty_passed: String(item.qty_inspected),
    defects: [],
  }))
}

function ResultDialog({
  insp,
  products,
  submitting,
  error,
  onClose,
  forms,
  onChangeForms,
  onSubmit,
}: {
  insp: InspectionOrder
  products: Product[]
  submitting: boolean
  error: string | null
  onClose: () => void
  forms: ItemResultForm[]
  onChangeForms: (next: ItemResultForm[]) => void
  onSubmit: () => void
}) {
  const itemOf = (itemId: number) =>
    insp.items.find((item) => item.insp_item_id === itemId)

  const updateForm = (itemId: number, next: ItemResultForm) =>
    onChangeForms(
      forms.map((form) => (form.insp_item_id === itemId ? next : form))
    )

  const setPassed = (itemId: number, qty: string) => {
    const form = forms.find((f) => f.insp_item_id === itemId)
    if (form) updateForm(itemId, { ...form, qty_passed: qty })
  }

  const addDefect = (itemId: number) => {
    const form = forms.find((f) => f.insp_item_id === itemId)
    if (form) {
      updateForm(itemId, {
        ...form,
        defects: [...form.defects, { reason_code: '', qty: '' }],
      })
    }
  }

  const updateDefect = (
    itemId: number,
    index: number,
    patch: Partial<DefectFormLine>
  ) => {
    const form = forms.find((f) => f.insp_item_id === itemId)
    if (form) {
      updateForm(itemId, {
        ...form,
        defects: form.defects.map((defect, i) =>
          i === index ? { ...defect, ...patch } : defect
        ),
      })
    }
  }

  const removeDefect = (itemId: number, index: number) => {
    const form = forms.find((f) => f.insp_item_id === itemId)
    if (form) {
      updateForm(itemId, {
        ...form,
        defects: form.defects.filter((_, i) => i !== index),
      })
    }
  }

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className='max-h-[90vh] overflow-y-auto sm:max-w-2xl'>
        <DialogHeader>
          <DialogTitle>录入质检结果 · {insp.insp_no}</DialogTitle>
        </DialogHeader>
        <div className='space-y-4'>
          {forms.map((form) => {
            const item = itemOf(form.insp_item_id)
            return (
              <div
                key={form.insp_item_id}
                className='space-y-2 rounded border p-3'
              >
                <div className='flex items-center justify-between'>
                  <span className='font-mono text-sm'>
                    {item ? skuLabel(products, item.product_id) : ''}
                  </span>
                  <span className='text-xs text-muted-foreground'>
                    检验 {item?.qty_inspected} 件
                  </span>
                </div>
                <div className='grid grid-cols-[100px_1fr] items-center gap-2'>
                  <Label
                    className='text-xs'
                    htmlFor={`pass-${form.insp_item_id}`}
                  >
                    合格数量
                  </Label>
                  <Input
                    id={`pass-${form.insp_item_id}`}
                    type='number'
                    min='0'
                    step='1'
                    className='h-8'
                    value={form.qty_passed}
                    onChange={(event) =>
                      setPassed(form.insp_item_id, event.target.value)
                    }
                  />
                </div>
                <div className='space-y-1.5'>
                  <div className='flex items-center justify-between'>
                    <span className='text-xs font-medium'>不良明细</span>
                    <Button
                      size='sm'
                      variant='outline'
                      onClick={() => addDefect(form.insp_item_id)}
                    >
                      添加不良
                    </Button>
                  </div>
                  {form.defects.map((defect, index) => (
                    <div
                      key={index}
                      className='grid grid-cols-[1fr_100px_32px] items-center gap-2'
                    >
                      <Select
                        value={defect.reason_code}
                        onValueChange={(value) =>
                          updateDefect(form.insp_item_id, index, {
                            reason_code: value as DefectFormLine['reason_code'],
                          })
                        }
                      >
                        <SelectTrigger className='h-8'>
                          <SelectValue placeholder='不良原因' />
                        </SelectTrigger>
                        <SelectContent>
                          {DEFECT_REASON_OPTIONS.map((option) => (
                            <SelectItem key={option.value} value={option.value}>
                              {option.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <Input
                        type='number'
                        min='1'
                        className='h-8'
                        placeholder='数量'
                        value={defect.qty}
                        onChange={(event) =>
                          updateDefect(form.insp_item_id, index, {
                            qty: event.target.value,
                          })
                        }
                      />
                      <Button
                        type='button'
                        variant='ghost'
                        size='sm'
                        aria-label='删除不良行'
                        onClick={() => removeDefect(form.insp_item_id, index)}
                      >
                        ✕
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
            )
          })}
          {error && <p className='text-sm text-destructive'>{error}</p>}
        </div>
        <DialogFooter>
          <Button variant='outline' onClick={onClose} disabled={submitting}>
            取消
          </Button>
          <Button onClick={onSubmit} disabled={submitting}>
            {submitting ? '提交中…' : '提交结果'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function InspDetailDialog({
  insp,
  products,
  onClose,
}: {
  insp: InspectionOrder
  products: Product[]
  onClose: () => void
}) {
  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className='sm:max-w-xl'>
        <DialogHeader>
          <DialogTitle className='font-mono'>{insp.insp_no}</DialogTitle>
        </DialogHeader>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>SKU</TableHead>
              <TableHead className='text-right'>检验</TableHead>
              <TableHead className='text-right'>合格</TableHead>
              <TableHead className='text-right'>不良</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {insp.items.map((item) => (
              <TableRow key={item.insp_item_id}>
                <TableCell className='font-mono'>
                  {skuLabel(products, item.product_id)}
                </TableCell>
                <TableCell className='text-right font-mono'>
                  {item.qty_inspected}
                </TableCell>
                <TableCell className='text-right font-mono'>
                  {item.qty_passed}
                </TableCell>
                <TableCell className='text-right font-mono'>
                  {item.qty_failed}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </DialogContent>
    </Dialog>
  )
}

function statusVariant(status: InspectionStatus): 'default' | 'secondary' {
  return status === 'completed' ? 'default' : 'secondary'
}

export function InspectionPage() {
  const [receiving, setReceiving] = useState<ReceivingOrder[]>([])
  const [inspections, setInspections] = useState<InspectionOrder[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)

  const [activeInsp, setActiveInsp] = useState<InspectionOrder | null>(null)
  const [forms, setForms] = useState<ItemResultForm[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [starting, setStarting] = useState(false)
  const [startError, setStartError] = useState<string | null>(null)
  const [detailInsp, setDetailInsp] = useState<InspectionOrder | null>(null)

  const loadAll = () => {
    Promise.all([
      api.get<ReceivingOrder[]>('/api/receiving'),
      api.get<InspectionOrder[]>('/api/inspection'),
      api.get<Product[]>('/api/products'),
    ])
      .then(([recvResponse, inspResponse, productResponse]) => {
        setReceiving(recvResponse.data)
        setInspections(inspResponse.data)
        setProducts(productResponse.data)
        setLoadError(null)
      })
      .catch((error) =>
        setLoadError(errorMessage(error, '数据加载失败，请确认 API 已启动'))
      )
      .finally(() => setLoading(false))
  }

  useEffect(loadAll, [])

  const openResults = (insp: InspectionOrder) => {
    setActiveInsp(insp)
    setForms(buildItemForms(insp))
    setFormError(null)
  }

  const startForRecv = (recvId: number) => {
    setStarting(true)
    setStartError(null)
    api
      .post<InspectionOrder>(`/api/inspection/start/${recvId}`)
      .then((response) => {
        loadAll()
        openResults(response.data)
      })
      .catch((error) => setStartError(errorMessage(error, '开工失败')))
      .finally(() => setStarting(false))
  }

  const submitResults = () => {
    if (!activeInsp) return
    const rows = forms.map((form) => {
      const item = activeInsp.items.find(
        (i) => i.insp_item_id === form.insp_item_id
      )
      const inspected = item?.qty_inspected ?? 0
      const passed = Number(form.qty_passed)
      const defects = form.defects.map((defect) => ({
        reason_code: defect.reason_code,
        qty: Number(defect.qty),
      }))
      return { inspected, passed, defects }
    })

    const hasInvalidRow = rows.some(
      (row) =>
        !Number.isInteger(row.passed) ||
        row.passed < 0 ||
        row.passed > row.inspected ||
        row.defects.some(
          (d) => d.reason_code === '' || !Number.isInteger(d.qty) || d.qty <= 0
        ) ||
        row.passed + row.defects.reduce((sum, d) => sum + d.qty, 0) !==
          row.inspected
    )
    if (hasInvalidRow) {
      setFormError(
        '每行需满足：0 ≤ 合格数 ≤ 检验数，不良原因/数量完整，且 合格+不良=检验数'
      )
      return
    }

    setSubmitting(true)
    setFormError(null)
    api
      .post(`/api/inspection/${activeInsp.insp_id}/complete`, {
        results: forms.map((form) => ({
          insp_item_id: form.insp_item_id,
          qty_passed: Number(form.qty_passed),
          defects: form.defects.map((defect) => ({
            reason_code: defect.reason_code,
            qty: Number(defect.qty),
          })),
        })),
      })
      .then(() => {
        setActiveInsp(null)
        loadAll()
      })
      .catch((error) => setFormError(errorMessage(error, '提交失败')))
      .finally(() => setSubmitting(false))
  }

  const recvNoOf = (recvId: number) =>
    receiving.find((recv) => recv.recv_id === recvId)?.recv_no ?? String(recvId)

  const pendingRecvs = receiving.filter(
    (recv) => recv.status === 'pending_inspection'
  )

  return (
    <div className='space-y-4'>
      <div>
        <h1 className='text-xl font-semibold tracking-tight'>质检管理</h1>
        <p className='text-sm text-muted-foreground'>
          收货单开工质检，按合格/不良结果自动调拨库存
        </p>
      </div>

      {loadError && (
        <Card>
          <CardContent className='p-4 text-sm text-destructive'>
            {loadError}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent className='p-4'>
          <h2 className='mb-2 text-sm font-medium'>待质检收货单</h2>
          {loading ? (
            <Skeleton className='h-8 w-full' />
          ) : pendingRecvs.length === 0 ? (
            <p className='text-sm text-muted-foreground'>暂无待质检收货单</p>
          ) : (
            <div className='flex flex-wrap gap-2'>
              {pendingRecvs.map((recv) => (
                <div
                  key={recv.recv_id}
                  className='flex items-center gap-2 rounded border px-3 py-1.5'
                >
                  <span className='font-mono text-sm'>{recv.recv_no}</span>
                  <Button
                    size='sm'
                    disabled={starting}
                    onClick={() => startForRecv(recv.recv_id)}
                  >
                    {starting ? '开工中…' : '开工质检'}
                  </Button>
                </div>
              ))}
            </div>
          )}
          {startError && (
            <p className='mt-2 text-sm text-destructive'>{startError}</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardContent className='p-0'>
          {loading ? (
            <div className='space-y-2 p-4'>
              {Array.from({ length: 5 }).map((_, index) => (
                <Skeleton key={index} className='h-8 w-full' />
              ))}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>质检单号</TableHead>
                  <TableHead>收货单号</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>质检时间</TableHead>
                  <TableHead>质检员</TableHead>
                  <TableHead className='text-right'>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {inspections.map((insp) => (
                  <TableRow key={insp.insp_id}>
                    <TableCell className='font-mono'>{insp.insp_no}</TableCell>
                    <TableCell className='font-mono'>
                      {recvNoOf(insp.recv_id)}
                    </TableCell>
                    <TableCell>
                      <Badge variant={statusVariant(insp.status)}>
                        {INSP_STATUS_LABELS[insp.status]}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {insp.inspected_at
                        ? insp.inspected_at.slice(0, 19).replace('T', ' ')
                        : '—'}
                    </TableCell>
                    <TableCell>{insp.inspector}</TableCell>
                    <TableCell className='text-right'>
                      <div className='flex justify-end gap-2'>
                        <Button
                          size='sm'
                          variant='outline'
                          onClick={() => setDetailInsp(insp)}
                        >
                          明细
                        </Button>
                        {insp.status === 'inspecting' && (
                          <Button size='sm' onClick={() => openResults(insp)}>
                            录入结果
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
                {inspections.length === 0 && (
                  <TableRow>
                    <TableCell
                      colSpan={6}
                      className='h-20 text-center text-muted-foreground'
                    >
                      暂无质检单
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {activeInsp && (
        <ResultDialog
          insp={activeInsp}
          products={products}
          submitting={submitting}
          error={formError}
          onClose={() => !submitting && setActiveInsp(null)}
          forms={forms}
          onChangeForms={setForms}
          onSubmit={submitResults}
        />
      )}

      {detailInsp && (
        <InspDetailDialog
          insp={detailInsp}
          products={products}
          onClose={() => setDetailInsp(null)}
        />
      )}
    </div>
  )
}
