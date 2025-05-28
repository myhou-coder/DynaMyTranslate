import { NextResponse } from "next/server"
import type { NextRequest } from "next/server"

export function middleware(request: NextRequest) {
  const path = request.nextUrl.pathname
  const isPublicPath = path === "/login" || path === "/register" || path === "/"

  // 检查cookie中的token
  const token = request.cookies.get("token")?.value || ""

  // 如果访问受保护的路由但没有令牌，则重定向到登录页面
  if (!isPublicPath && !token) {
    return NextResponse.redirect(new URL("/login", request.url))
  }

  // 如果访问登录或注册页面但有令牌，则重定向到翻译页面
  if ((path === "/login" || path === "/register") && token) {
    return NextResponse.redirect(new URL("/translate", request.url))
  }

  return NextResponse.next()
}

// 匹配所有路由，除了静态文件、API路由等
export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
}

