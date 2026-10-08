import { Construction } from 'lucide-react'
import { Header } from '@/components/layout/header'
import { Main } from '@/components/layout/main'
import { Search } from '@/components/search'
import { Card, CardContent } from '@/components/ui/card'

type PagePlaceholderProps = {
  title: string
  phase: string
}

export function PagePlaceholder({ title, phase }: PagePlaceholderProps) {
  return (
    <>
      <Header>
        <Search />
      </Header>
      <Main>
        <h1 className='mb-4 text-base font-semibold'>{title}</h1>
        <Card>
          <CardContent className='flex flex-col items-center gap-3 py-16 text-center'>
            <Construction className='size-8 text-muted-foreground' />
            <div className='space-y-1'>
              <p className='font-medium'>
                「{title}」模块将于{phase}交付
              </p>
              <p className='text-sm text-muted-foreground'>
                阶段 1 仅提供路由与侧边栏导航占位
              </p>
            </div>
          </CardContent>
        </Card>
      </Main>
    </>
  )
}
