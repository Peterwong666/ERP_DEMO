import { createFileRoute } from '@tanstack/react-router'
import { PagePlaceholder } from '@/components/layout/page-placeholder'

export const Route = createFileRoute('/_authenticated/ai-supply/')({
  component: AiSupplyPage,
})

function AiSupplyPage() {
  return <PagePlaceholder title='AI 供应链' phase='阶段 9' />
}
