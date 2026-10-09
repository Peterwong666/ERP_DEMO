export type ProductCategory =
  | 'electronics'
  | 'bags'
  | 'home'
  | 'apparel'
  | 'beauty'
  | 'toys'

export type ProductStatus = 'developing' | 'on_sale' | 'discontinued'

export interface Product {
  product_id: number
  sku_code: string
  name: string
  category: ProductCategory
  status: ProductStatus
  unit: string
  standard_cost: string
  weight_g: number
  safety_stock: number
  default_supplier_id: number
  barcode: string | null
  description: string | null
}

export type ProductFormValues = {
  sku_code: string
  name: string
  category: ProductCategory
  unit: string
  standard_cost: string
  weight_g: string
  safety_stock: string
  barcode: string
  description: string
}

export const CATEGORY_OPTIONS: ProductCategory[] = [
  'electronics',
  'bags',
  'home',
  'apparel',
  'beauty',
  'toys',
]

export const CATEGORY_LABELS: Record<ProductCategory, string> = {
  electronics: '电子',
  bags: '包袋',
  home: '家居',
  apparel: '服饰',
  beauty: '美妆',
  toys: '玩具',
}

export const STATUS_LABELS: Record<ProductStatus, string> = {
  developing: '开发中',
  on_sale: '在售',
  discontinued: '停售',
}

export const EMPTY_PRODUCT_FORM: ProductFormValues = {
  sku_code: '',
  name: '',
  category: 'electronics',
  unit: '件',
  standard_cost: '',
  weight_g: '',
  safety_stock: '0',
  barcode: '',
  description: '',
}
