import { createFileRoute } from '@tanstack/react-router'
import { PagePlaceholder } from '@/components/layout/page-placeholder'

export const Route = createFileRoute('/_authenticated/inspection/')({
  component: InspectionPage,
})

function InspectionPage() {
  return <PagePlaceholder title='质检管理' phase='阶段 7' />
}
