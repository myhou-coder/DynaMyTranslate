import Link from "next/link"
import { Button } from "@/components/ui/button"

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center text-center">
      <h1 className="text-6xl font-bold">404</h1>
      <h2 className="mt-4 text-2xl font-semibold">页面未找到</h2>
      <p className="mt-2 text-muted-foreground">您正在查找的页面不存在或已被移动。</p>
      <Link href="/" className="mt-8">
        <Button>返回首页</Button>
      </Link>
    </div>
  )
}

