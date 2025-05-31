"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useToast } from "@/hooks/use-toast"
import { useAuth } from "@/contexts/auth-context"
import apiClient from "@/lib/api-client"
import { Loader2, Save, Eye, EyeOff, ExternalLink, Shield, LogOut } from "lucide-react"

interface Session {
  id: number
  token: string
  is_current: boolean
  created_at: string
}

const languages = [
  { value: "zh-CN", label: "中文（简体）" },
  { value: "en", label: "英文" },
  { value: "ja", label: "日文" },
  { value: "ko", label: "韩文" },
  { value: "fr", label: "法文" },
  { value: "de", label: "德文" },
  { value: "es", label: "西班牙文" },
  { value: "ru", label: "俄文" },
]

export default function SettingsPage() {
  const { user, isLoading: authLoading } = useAuth()
  const router = useRouter()
  const { toast } = useToast()
  
  const [apiKey, setApiKey] = useState("")
  const [defaultSourceLanguage, setDefaultSourceLanguage] = useState("en")
  const [defaultTargetLanguage, setDefaultTargetLanguage] = useState("zh-CN")
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [showApiKey, setShowApiKey] = useState(false)
  const [sessions, setSessions] = useState<Session[]>([])
  const [isLoadingSessions, setIsLoadingSessions] = useState(false)
  const [isRevokingOthers, setIsRevokingOthers] = useState(false)

  // 检查用户是否已登录
  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login")
    }
  }, [authLoading, user, router])

  // 加载用户的API配置
  useEffect(() => {
    const loadApiConfig = async () => {
      if (!user) return
      
      try {
        setIsLoading(true)
        const response = await apiClient.get("/config")
        
        if (response.data.success) {
          const config = response.data.data
          setApiKey(config.deepseek_api_key || "")
          setDefaultSourceLanguage(config.default_source_language || "en")
          setDefaultTargetLanguage(config.default_target_language || "zh-CN")
        }
      } catch (error: any) {
        console.error("加载API配置失败:", error)
        toast({
          variant: "destructive",
          title: "加载配置失败",
          description: error.response?.data?.error || "发生错误",
        })
      } finally {
        setIsLoading(false)
      }
    }

    loadApiConfig()
  }, [user, toast])

  // 加载用户会话
  const loadSessions = async () => {
    if (!user) return
    
    try {
      setIsLoadingSessions(true)
      const response = await apiClient.get("/sessions")
      
      if (response.data.success) {
        setSessions(response.data.data)
      }
    } catch (error: any) {
      console.error("加载会话失败:", error)
      toast({
        variant: "destructive",
        title: "加载会话失败",
        description: error.response?.data?.error || "发生错误",
      })
    } finally {
      setIsLoadingSessions(false)
    }
  }

  useEffect(() => {
    loadSessions()
  }, [user])

  const handleSave = async () => {
    if (!apiKey.trim()) {
      toast({
        variant: "destructive",
        title: "验证失败",
        description: "请输入DeepSeek API Key",
      })
      return
    }

    try {
      setIsSaving(true)
      const response = await apiClient.post("/config", {
        deepseek_api_key: apiKey.trim(),
        default_source_language: defaultSourceLanguage,
        default_target_language: defaultTargetLanguage,
      })

      if (response.data.success) {
        toast({
          title: "保存成功",
          description: "API配置已保存",
        })
      }
    } catch (error: any) {
      toast({
        variant: "destructive",
        title: "保存失败",
        description: error.response?.data?.error || "发生错误",
      })
    } finally {
      setIsSaving(false)
    }
  }

  const handleRevokeOtherSessions = async () => {
    try {
      setIsRevokingOthers(true)
      const response = await apiClient.post("/sessions/revoke-others")
      
      if (response.data.success) {
        toast({
          title: "操作成功",
          description: response.data.message,
        })
        // 重新加载会话列表
        loadSessions()
      }
    } catch (error: any) {
      toast({
        variant: "destructive",
        title: "操作失败",
        description: error.response?.data?.error || "发生错误",
      })
    } finally {
      setIsRevokingOthers(false)
    }
  }

  if (authLoading || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  if (!user) {
    return null
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <div className="mb-6">
        <h1 className="text-3xl font-bold">设置</h1>
        <p className="text-muted-foreground mt-2">管理您的账户设置和API配置</p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              API配置
            </CardTitle>
            <CardDescription>
              配置您的DeepSeek API Key以使用翻译服务
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="apiKey">DeepSeek API Key</Label>
              <div className="relative">
                <Input
                  id="apiKey"
                  type={showApiKey ? "text" : "password"}
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                  className="pr-10"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                  onClick={() => setShowApiKey(!showApiKey)}
                >
                  {showApiKey ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="defaultSourceLanguage">默认原文语言</Label>
                <Select value={defaultSourceLanguage} onValueChange={setDefaultSourceLanguage}>
                  <SelectTrigger>
                    <SelectValue placeholder="选择原文语言" />
                  </SelectTrigger>
                  <SelectContent>
                    {languages.map((lang) => (
                      <SelectItem key={lang.value} value={lang.value}>
                        {lang.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="defaultTargetLanguage">默认目标语言</Label>
                <Select value={defaultTargetLanguage} onValueChange={setDefaultTargetLanguage}>
                  <SelectTrigger>
                    <SelectValue placeholder="选择目标语言" />
                  </SelectTrigger>
                  <SelectContent>
                    {languages.map((lang) => (
                      <SelectItem key={lang.value} value={lang.value}>
                        {lang.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <ExternalLink className="h-4 w-4" />
              <a
                href="https://platform.deepseek.com/api_keys"
                target="_blank"
                rel="noopener noreferrer"
                className="hover:underline"
              >
                获取DeepSeek API Key
              </a>
            </div>

            <Button onClick={handleSave} disabled={isSaving} className="w-full">
              {isSaving ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  保存中...
                </>
              ) : (
                <>
                  <Save className="mr-2 h-4 w-4" />
                  保存配置
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>账户信息</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <Label>邮箱地址</Label>
              <Input value={user.email} disabled />
            </div>
            <div className="pt-4">
              <Button variant="outline" onClick={() => router.push("/translate")}>
                返回翻译
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            会话管理
          </CardTitle>
          <CardDescription>
            管理您在不同设备上的登录会话。这有助于提升账户安全性。
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoadingSessions ? (
            <div className="flex items-center justify-center py-4">
              <Loader2 className="h-6 w-6 animate-spin" />
            </div>
          ) : (
            <div className="space-y-4">
              <div className="text-sm text-muted-foreground">
                当前活跃会话数: {sessions.length}
              </div>
              
              {sessions.map((session) => (
                <div
                  key={session.id}
                  className={`flex items-center justify-between p-4 border rounded-lg ${
                    session.is_current ? 'bg-primary/5 border-primary/20' : ''
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Shield className="h-4 w-4" />
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium">会话 {session.token}</span>
                        {session.is_current && (
                          <span className="text-xs bg-primary text-primary-foreground px-2 py-1 rounded">
                            当前会话
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
              
              {sessions.filter(s => !s.is_current).length > 0 && (
                <div className="pt-4 border-t">
                  <Button
                    variant="destructive"
                    onClick={handleRevokeOtherSessions}
                    disabled={isRevokingOthers}
                    className="w-full"
                  >
                    {isRevokingOthers ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin mr-2" />
                        处理中...
                      </>
                    ) : (
                      <>
                        <LogOut className="h-4 w-4 mr-2" />
                        撤销所有其他会话
                      </>
                    )}
                  </Button>
                  <p className="text-sm text-muted-foreground mt-2 text-center">
                    这将登出您在其他所有设备上的会话
                  </p>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
} 