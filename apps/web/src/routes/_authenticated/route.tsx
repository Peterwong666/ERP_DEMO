import { createFileRoute } from '@tanstack/react-router'
import { AuthenticatedLayout } from '@/components/layout/authenticated-layout'

// 布局路由组：继承自 shadcn-admin 模板，作为全部业务页面的父级布局（侧边栏/头部）。
// 本项目为演示系统、无鉴权需求（见 docs/PRD.md），组名中的 "authenticated" 仅为模板命名保留。
export const Route = createFileRoute('/_authenticated')({
  component: AuthenticatedLayout,
})
