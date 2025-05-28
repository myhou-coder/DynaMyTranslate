"use client"

import type React from "react"

import { createContext, useContext, useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import axios from "axios"
import { useToast } from "@/components/ui/use-toast"
import { setCookie, getCookie, removeCookie } from "@/utils/cookie"

type User = {
  email: string
  token: string
}

type AuthContextType = {
  user: User | null
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  isLoading: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const router = useRouter()
  const { toast } = useToast()

  useEffect(() => {
    // 检查用户是否已登录
    const token = getCookie("token") || localStorage.getItem("token")
    const email = getCookie("email") || localStorage.getItem("email")

    if (token && email) {
      setUser({ email, token })
    }

    setIsLoading(false)
  }, [])

  const login = async (email: string, password: string) => {
    try {
      setIsLoading(true)
      const response = await axios.post("http://localhost:5000/api/login", { email, password })

      if (response.data.success) {
        const token = response.data.data.token

        // 同时设置cookie和localStorage
        setCookie("token", token, 7) // 7天过期
        setCookie("email", email, 7)
        localStorage.setItem("token", token)
        localStorage.setItem("email", email)

        // 先设置用户状态
        setUser({ email, token })

        // 显示成功提示
        toast({
          title: "登录成功",
          description: `欢迎回来，${email}！`,
        })

        // 最后进行路由跳转
        router.push("/translate")
      }
    } catch (error: any) {
      toast({
        variant: "destructive",
        title: "登录失败",
        description: error.response?.data?.error || "发生错误",
      })
      throw error
    } finally {
      setIsLoading(false)
    }
  }

  const register = async (email: string, password: string) => {
    try {
      setIsLoading(true)
      const response = await axios.post("http://localhost:5000/api/register", { email, password })

      if (response.data.success) {
        toast({
          title: "注册成功",
          description: "您现在可以使用您的凭据登录",
        })
        router.push("/login")
      }
    } catch (error: any) {
      toast({
        variant: "destructive",
        title: "注册失败",
        description: error.response?.data?.error || "发生错误",
      })
      throw error
    } finally {
      setIsLoading(false)
    }
  }

  const logout = async () => {
    try {
      setIsLoading(true)
      if (user?.token) {
        await axios.post(
          "http://localhost:5000/api/logout",
          {},
          {
            headers: {
              Authorization: `Bearer ${user.token}`,
            },
          },
        )
      }
    } catch (error) {
      console.error("登出错误:", error)
    } finally {
      // 清除cookie和localStorage
      removeCookie("token")
      removeCookie("email")
      localStorage.removeItem("token")
      localStorage.removeItem("email")

      // 更新状态
      setUser(null)

      // 重定向到首页
      router.push("/")
      setIsLoading(false)
    }
  }

  return <AuthContext.Provider value={{ user, login, register, logout, isLoading }}>{children}</AuthContext.Provider>
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error("useAuth 必须在 AuthProvider 内部使用")
  }
  return context
}

