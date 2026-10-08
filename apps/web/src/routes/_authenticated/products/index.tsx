import { createFileRoute } from '@tanstack/react-router'
import { PagePlaceholder } from '@/components/layout/page-placeholder'

export const Route = createFileRoute('/_authenticated/products/')({
  component: ProductsPage,
})

function ProductsPage() {
  return <PagePlaceholder title='新品管理' phase='阶段 4' />
}
