import { useCallback, useEffect, useState } from 'react'
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
import { Textarea } from '@/components/ui/textarea'
import {
  CATEGORY_LABELS,
  CATEGORY_OPTIONS,
  EMPTY_PRODUCT_FORM,
  STATUS_LABELS,
  type Product,
  type ProductCategory,
  type ProductFormValues,
} from './types'

type SaveMode = 'create' | 'edit'

function toFormValues(product: Product): ProductFormValues {
  return {
    sku_code: product.sku_code,
    name: product.name,
    category: product.category,
    unit: product.unit,
    standard_cost: product.standard_cost,
    weight_g: String(product.weight_g),
    safety_stock: String(product.safety_stock),
    barcode: product.barcode ?? '',
    description: product.description ?? '',
  }
}

function buildPayload(form: ProductFormValues) {
  return {
    name: form.name,
    category: form.category,
    unit: form.unit,
    standard_cost: form.standard_cost,
    weight_g: Number(form.weight_g),
    safety_stock: Number(form.safety_stock),
    barcode: form.barcode.trim() ? form.barcode : null,
    description: form.description.trim() ? form.description : null,
  }
}

function errorMessage(error: unknown, fallback: string): string {
  if (isAxiosError(error) && typeof error.response?.data?.detail === 'string') {
    return error.response.data.detail
  }
  return fallback
}

function StatusBadge({ status }: { status: Product['status'] }) {
  const variant =
    status === 'on_sale'
      ? 'default'
      : status === 'discontinued'
        ? 'destructive'
        : 'secondary'
  return <Badge variant={variant}>{STATUS_LABELS[status]}</Badge>
}

function ProductFormDialog({
  mode,
  form,
  submitting,
  error,
  onClose,
  onChange,
  onSubmit,
}: {
  mode: SaveMode
  form: ProductFormValues
  submitting: boolean
  error: string | null
  onClose: () => void
  onChange: (next: ProductFormValues) => void
  onSubmit: () => void
}) {
  const setField = (field: keyof ProductFormValues, value: string) =>
    onChange({ ...form, [field]: value })

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className='max-h-[90vh] overflow-y-auto sm:max-w-lg'>
        <DialogHeader>
          <DialogTitle>
            {mode === 'create' ? '新建产品' : '编辑产品'}
          </DialogTitle>
        </DialogHeader>
        <div className='grid gap-3'>
          <div className='grid gap-1.5'>
            <Label htmlFor='sku_code'>SKU 编码</Label>
            <Input
              id='sku_code'
              value={form.sku_code}
              disabled={mode === 'edit'}
              onChange={(event) => setField('sku_code', event.target.value)}
            />
          </div>
          <div className='grid gap-1.5'>
            <Label htmlFor='name'>产品名称</Label>
            <Input
              id='name'
              value={form.name}
              onChange={(event) => setField('name', event.target.value)}
            />
          </div>
          <div className='grid grid-cols-2 gap-3'>
            <div className='grid gap-1.5'>
              <Label>类目</Label>
              <Select
                value={form.category}
                onValueChange={(value) => setField('category', value)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CATEGORY_OPTIONS.map((category) => (
                    <SelectItem key={category} value={category}>
                      {CATEGORY_LABELS[category]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className='grid gap-1.5'>
              <Label htmlFor='unit'>单位</Label>
              <Input
                id='unit'
                value={form.unit}
                onChange={(event) => setField('unit', event.target.value)}
              />
            </div>
          </div>
          <div className='grid grid-cols-3 gap-3'>
            <div className='grid gap-1.5'>
              <Label htmlFor='standard_cost'>标准成本</Label>
              <Input
                id='standard_cost'
                type='number'
                min='0'
                step='0.01'
                value={form.standard_cost}
                onChange={(event) =>
                  setField('standard_cost', event.target.value)
                }
              />
            </div>
            <div className='grid gap-1.5'>
              <Label htmlFor='weight_g'>重量(g)</Label>
              <Input
                id='weight_g'
                type='number'
                min='1'
                value={form.weight_g}
                onChange={(event) => setField('weight_g', event.target.value)}
              />
            </div>
            <div className='grid gap-1.5'>
              <Label htmlFor='safety_stock'>安全库存</Label>
              <Input
                id='safety_stock'
                type='number'
                min='0'
                value={form.safety_stock}
                onChange={(event) =>
                  setField('safety_stock', event.target.value)
                }
              />
            </div>
          </div>
          <div className='grid gap-1.5'>
            <Label htmlFor='barcode'>条码（可选）</Label>
            <Input
              id='barcode'
              value={form.barcode}
              onChange={(event) => setField('barcode', event.target.value)}
            />
          </div>
          <div className='grid gap-1.5'>
            <Label htmlFor='description'>描述（可选）</Label>
            <Textarea
              id='description'
              rows={2}
              value={form.description}
              onChange={(event) => setField('description', event.target.value)}
            />
          </div>
          {error && <p className='text-sm text-destructive'>{error}</p>}
        </div>
        <DialogFooter>
          <Button variant='outline' onClick={onClose} disabled={submitting}>
            取消
          </Button>
          <Button onClick={onSubmit} disabled={submitting}>
            {submitting ? '保存中…' : '保存'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([])
  const [categoryFilter, setCategoryFilter] = useState<'all' | ProductCategory>(
    'all'
  )
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)

  const [dialogMode, setDialogMode] = useState<SaveMode>('create')
  const [form, setForm] = useState<ProductFormValues>(EMPTY_PRODUCT_FORM)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  const loadProducts = useCallback((category: 'all' | ProductCategory) => {
    const params = category === 'all' ? undefined : { category }
    api
      .get<Product[]>('/api/products', { params })
      .then((response) => {
        setProducts(response.data)
        setLoadError(null)
      })
      .catch((error) => setLoadError(errorMessage(error, '产品列表加载失败')))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => loadProducts(categoryFilter), [categoryFilter, loadProducts])

  const openCreate = () => {
    setDialogMode('create')
    setForm(EMPTY_PRODUCT_FORM)
    setEditingId(null)
    setFormError(null)
  }

  const openEdit = (product: Product) => {
    setDialogMode('edit')
    setForm(toFormValues(product))
    setEditingId(product.product_id)
    setFormError(null)
  }

  const closeDialog = () => {
    if (submitting) return
    setEditingId(null)
  }

  const submitForm = () => {
    if (
      !form.name.trim() ||
      !form.standard_cost ||
      Number(form.weight_g) <= 0
    ) {
      setFormError('请填写名称、正数标准成本与重量')
      return
    }
    setSubmitting(true)
    setFormError(null)
    const request =
      dialogMode === 'create'
        ? api.post('/api/products', {
            ...buildPayload(form),
            sku_code: form.sku_code,
          })
        : api.patch(`/api/products/${editingId}`, buildPayload(form))
    request
      .then(() => {
        setEditingId(null)
        loadProducts(categoryFilter)
      })
      .catch((error) => setFormError(errorMessage(error, '保存失败')))
      .finally(() => setSubmitting(false))
  }

  const toggleStatus = (product: Product) => {
    const nextStatus = product.status === 'on_sale' ? 'discontinued' : 'on_sale'
    api
      .post(`/api/products/${product.product_id}/status`, {
        status: nextStatus,
      })
      .then(() => loadProducts(categoryFilter))
      .catch((error) => setLoadError(errorMessage(error, '状态切换失败')))
  }

  return (
    <div className='space-y-4'>
      <div className='flex items-center justify-between gap-4'>
        <div>
          <h1 className='text-xl font-semibold tracking-tight'>新品管理</h1>
          <p className='text-sm text-muted-foreground'>
            维护 SKU 主数据与在售状态
          </p>
        </div>
        <div className='flex items-center gap-2'>
          <Select
            value={categoryFilter}
            onValueChange={(value) =>
              setCategoryFilter(value as 'all' | ProductCategory)
            }
          >
            <SelectTrigger className='w-36'>
              <SelectValue placeholder='全部类目' />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value='all'>全部类目</SelectItem>
              {CATEGORY_OPTIONS.map((category) => (
                <SelectItem key={category} value={category}>
                  {CATEGORY_LABELS[category]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button onClick={openCreate}>新建产品</Button>
        </div>
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
                  <TableHead>SKU</TableHead>
                  <TableHead>名称</TableHead>
                  <TableHead>类目</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead className='text-right'>标准成本</TableHead>
                  <TableHead className='text-right'>重量(g)</TableHead>
                  <TableHead className='text-right'>安全库存</TableHead>
                  <TableHead className='text-right'>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {products.map((product) => (
                  <TableRow key={product.product_id}>
                    <TableCell className='font-mono'>
                      {product.sku_code}
                    </TableCell>
                    <TableCell>{product.name}</TableCell>
                    <TableCell>{CATEGORY_LABELS[product.category]}</TableCell>
                    <TableCell>
                      <StatusBadge status={product.status} />
                    </TableCell>
                    <TableCell className='text-right font-mono'>
                      {product.standard_cost}
                    </TableCell>
                    <TableCell className='text-right font-mono'>
                      {product.weight_g}
                    </TableCell>
                    <TableCell className='text-right font-mono'>
                      {product.safety_stock}
                    </TableCell>
                    <TableCell className='text-right'>
                      <div className='flex justify-end gap-2'>
                        <Button
                          size='sm'
                          variant='outline'
                          onClick={() => openEdit(product)}
                        >
                          编辑
                        </Button>
                        <Button
                          size='sm'
                          variant='outline'
                          onClick={() => toggleStatus(product)}
                        >
                          {product.status === 'on_sale' ? '停售' : '上架'}
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
                {products.length === 0 && (
                  <TableRow>
                    <TableCell
                      colSpan={8}
                      className='h-20 text-center text-muted-foreground'
                    >
                      暂无产品
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {editingId !== null && (
        <ProductFormDialog
          mode={dialogMode}
          form={form}
          submitting={submitting}
          error={formError}
          onClose={closeDialog}
          onChange={setForm}
          onSubmit={submitForm}
        />
      )}
    </div>
  )
}
