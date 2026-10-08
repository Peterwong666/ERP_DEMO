import { createFileRoute } from '@tanstack/react-router'
import { PagePlaceholder } from '@/components/layout/page-placeholder'

export const Route = createFileRoute('/_authenticated/receiving/')({
  component: ReceivingPage,
})

function ReceivingPage() {
  return <PagePlaceholder title='收货管理' phase='阶段 6' />
}
