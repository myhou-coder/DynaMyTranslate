import Link from "next/link"
import { Button } from "@/components/ui/button"
import { FileText, Languages, History } from "lucide-react"

export default function Home() {
  return (
    <div className="flex flex-col min-h-screen">
      <header className="border-b">
        <div className="container flex h-16 items-center justify-between py-4">
          <h1 className="text-2xl font-bold">DynaMyTranslate</h1>
          <div className="flex gap-4">
            <Link href="/login">
              <Button variant="outline">登录</Button>
            </Link>
            <Link href="/register">
              <Button>注册</Button>
            </Link>
          </div>
        </div>
      </header>
      <main className="flex-1">
        <section className="py-12 md:py-24 lg:py-32">
          <div className="container px-4 md:px-6">
            <div className="flex flex-col items-center justify-center space-y-4 text-center">
              <h2 className="text-3xl font-bold tracking-tighter sm:text-4xl md:text-5xl">翻译您的文献文档</h2>
              <p className="max-w-[700px] text-gray-500 md:text-xl/relaxed lg:text-base/relaxed xl:text-xl/relaxed dark:text-gray-400">
                上传您的PDF文档，轻松将其翻译成中文。
              </p>
              <div className="flex flex-col gap-2 min-[400px]:flex-row">
                <Link href="/translate">
                  <Button size="lg">开始使用</Button>
                </Link>
              </div>
            </div>
          </div>
        </section>
        <section className="py-12 md:py-24 lg:py-32 bg-muted/50">
          <div className="container px-4 md:px-6">
            <div className="grid gap-10 sm:grid-cols-2 md:grid-cols-3">
              <div className="flex flex-col items-center gap-2 text-center">
                <div className="flex h-20 w-20 items-center justify-center rounded-full bg-primary/10">
                  <FileText className="h-10 w-10 text-primary" />
                </div>
                <h3 className="text-xl font-bold">上传文档</h3>
                <p className="text-gray-500 dark:text-gray-400">安全地将您的PDF文档上传到我们的平台。</p>
              </div>
              <div className="flex flex-col items-center gap-2 text-center">
                <div className="flex h-20 w-20 items-center justify-center rounded-full bg-primary/10">
                  <Languages className="h-10 w-10 text-primary" />
                </div>
                <h3 className="text-xl font-bold">翻译内容</h3>
                <p className="text-gray-500 dark:text-gray-400">将您的文档翻译成中文。</p>
              </div>
              <div className="flex flex-col items-center gap-2 text-center">
                <div className="flex h-20 w-20 items-center justify-center rounded-full bg-primary/10">
                  <History className="h-10 w-10 text-primary" />
                </div>
                <h3 className="text-xl font-bold">管理历史</h3>
                <p className="text-gray-500 dark:text-gray-400">随时访问和管理您的翻译历史记录。</p>
              </div>
            </div>
          </div>
        </section>
      </main>
      <footer className="border-t py-6 md:py-0">
        <div className="container flex flex-col items-center justify-between gap-4 md:h-24 md:flex-row">
          <p className="text-sm text-gray-500 dark:text-gray-400">
            &copy; {new Date().getFullYear()} DynaMyTranslate。保留所有权利。
          </p>
        </div>
      </footer>
    </div>
  )
}

