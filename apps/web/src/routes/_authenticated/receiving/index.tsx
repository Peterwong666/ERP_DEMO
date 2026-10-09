import { createFileRoute } from '@tanstack/react-router'
import { ReceivingPage } from '@/features/receiving/receiving-page'

export const Route = createFileRoute('/_authenticated/receiving/')({
  component: ReceivingPage,
})
