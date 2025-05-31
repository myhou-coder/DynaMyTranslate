"use client"

import type React from "react"

import { useState, useRef, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Progress } from "@/components/ui/progress"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { useToast } from "@/components/ui/use-toast"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { FileUp, Download, Loader2, Trash2, FileText, LogOut, Settings, AlertTriangle, Calendar, Languages, Activity } from "lucide-react"
import { useAuth } from "@/contexts/auth-context"
import apiClient from "@/lib/api-client"
import { getCookie } from "@/utils/cookie"
import { Item } from "@radix-ui/react-select"
import { processFilename, isFilenameTooLong, truncateFilename } from "@/utils/filename"

// 修改 HistoryItem 类型，添加状态和进度字段
type HistoryItem = {
  id: number
  filename: string
  fileSize: string
  translatedLang: string
  createdAt: string
  downloadUrl: string
  status?: string // 添加状态字段
  progress?: number // 添加进度字段
  taskId?: string // 添加任务ID字段
  sourceLanguage?: string
  targetLanguage?: string
}

const languages = [
  { code: 'en', name: '英文' },
  { code: 'zh-CN', name: '中文' },
  { code: 'ja', name: '日文' },
  { code: 'ko', name: '韩文' },
  { code: 'fr', name: '法文' },
  { code: 'de', name: '德文' },
  { code: 'es', name: '西班牙文' },
  { code: 'ru', name: '俄文' },
]

// 智能检测API地址
function getApiBaseUrl() {
  if (typeof window === 'undefined') {
    return "http://localhost:5000/api"
  }
  
  const hostname = window.location.hostname
  
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return "http://localhost:5000/api"
  } else if (hostname === '100.88.126.48') {
    return "http://100.88.126.48:5000/api"
  } else {
    return process.env.NEXT_PUBLIC_API_BASE_URL || `http://${hostname}:5000/api`
  }
}

export default function TranslatePage() {
  const { user, logout, isLoading: authLoading } = useAuth()
  const router = useRouter()
  const { toast } = useToast()

  // 客户端保护逻辑
  useEffect(() => {
    // 检查cookie和localStorage
    const token = getCookie("token") || localStorage.getItem("token")

    if (!token && !authLoading) {
      // 如果没有token且不在加载状态，重定向到登录页面
      router.push("/login")

      // 显示提示
      toast({
        variant: "destructive",
        title: "需要登录",
        description: "请先登录以访问此页面",
      })
    }
  }, [authLoading, router, toast])

  // 上传状态
  const [file, setFile] = useState<File | null>(null)
  const [sourceLang, setSourceLang] = useState("en")
  const [targetLang, setTargetLang] = useState("zh-CN")
  const [isUploading, setIsUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [taskId, setTaskId] = useState<string | null>(null)

  // 移除这些不再需要的状态变量
  // const [taskId, setTaskId] = useState<string | null>(null)
  // const [translationStatus, setTranslationStatus] = useState<string | null>(null)
  // const [translationProgress, setTranslationProgress] = useState(0)
  // const [downloadUrl, setDownloadUrl] = useState<string | null>(null)

  // 历史记录状态
  const [history, setHistory] = useState<HistoryItem[]>([])
  const [isLoadingHistory, setIsLoadingHistory] = useState(true)
  const [isDeleting, setIsDeleting] = useState<number | null>(null)

  // 登出对话框状态
  const [logoutDialogOpen, setLogoutDialogOpen] = useState(false)

  const progressIntervalRef = useRef<NodeJS.Timeout | null>(null)

  // 加载用户语言偏好设置
  const fetchUserLanguagePreferences = async () => {
    try {
      const response = await apiClient.get("/config")
      if (response.data.success) {
        const config = response.data.data
        if (config.default_source_language) {
          setSourceLang(config.default_source_language)
        }
        if (config.default_target_language) {
          setTargetLang(config.default_target_language)
        }
      }
    } catch (error: any) {
      console.error("加载语言偏好设置失败:", error)
    }
  }

  // 加载历史记录
  useEffect(() => {
    if (user) {
      fetchHistory()
      fetchUserLanguagePreferences()
    }
  }, [user])

  // 如果用户未登录，显示加载状态
  if (authLoading || !user) {
    return (
      <div className="flex h-screen w-full items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent"></div>
      </div>
    )
  }

  const fetchHistory = async () => {
    try {
      setIsLoadingHistory(true)
      const response = await apiClient.get("/history")

      if (response.data.success) {
        setHistory(response.data.data)
      }
    } catch (error: any) {
      toast({
        variant: "destructive",
        title: "加载历史记录失败",
        description: error.response?.data?.error || "发生错误",
      })
    } finally {
      setIsLoadingHistory(false)
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0]

      if (selectedFile.type !== "application/pdf") {
        toast({
          variant: "destructive",
          title: "无效的文件类型",
          description: "请上传PDF文件",
        })
        return
      }

      // 检查文件名长度
      const originalName = selectedFile.name
      const isNameTooLong = isFilenameTooLong(originalName)
      
      if (isNameTooLong) {
        const processedName = processFilename(originalName)
        
        // 创建一个新的File对象，使用处理后的文件名
        const processedFile = new File([selectedFile], processedName, {
          type: selectedFile.type,
          lastModified: selectedFile.lastModified,
        })
        
        // 显示文件名被截断的提示
        toast({
          title: "文件名已调整",
          description: `原文件名过长，已自动调整为: ${processedName}`,
          duration: 4000,
        })
        
        setFile(processedFile)
      } else {
        // 即使文件名不太长，也进行基本的安全处理
        const processedName = processFilename(originalName)
        
        if (processedName !== originalName) {
          const processedFile = new File([selectedFile], processedName, {
            type: selectedFile.type,
            lastModified: selectedFile.lastModified,
          })
          
          toast({
            title: "文件名已清理",
            description: `文件名中的特殊字符已被处理: ${processedName}`,
            duration: 3000,
          })
          
          setFile(processedFile)
        } else {
          setFile(selectedFile)
        }
      }
    }
  }

  // 修改 handleUpload 函数，上传成功后重置上传窗口
  const handleUpload = async () => {
    if (!file) {
      toast({
        variant: "destructive",
        title: "未选择文件",
        description: "请选择要上传的PDF文件",
      })
      return
    }

    // 在上传前再次检查文件名
    if (isFilenameTooLong(file.name)) {
      toast({
        variant: "destructive",
        title: "文件名仍然过长",
        description: "请重新选择文件或联系技术支持",
      })
      return
    }

    try {
      setIsUploading(true)
      setUploadProgress(0)

      const formData = new FormData()
      formData.append("file", file)
      formData.append("sourceLanguage", sourceLang)
      formData.append("targetLanguage", targetLang)

      const response = await apiClient.post("/upload", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / (progressEvent.total || 100))
          setUploadProgress(percentCompleted)
        },
      })

      if (response.data.success) {
        const newTaskId = response.data.data.taskId
        setTaskId(newTaskId)

        toast({
          title: "上传成功",
          description: "您的文件正在处理中，请在历史记录中查看翻译进度",
        })

        // 重置上传窗口
        resetUpload()

        // 刷新历史记录以显示新的翻译任务
        fetchHistory()

        // 开始轮询进度
        startProgressPolling(newTaskId)
      }
    } catch (error: any) {
      const errorMessage = error.response?.data?.error || "发生错误"
      
      // 检查是否是文件名相关的错误
      if (errorMessage.includes("文件名") || errorMessage.includes("filename")) {
        toast({
          variant: "destructive",
          title: "文件名错误",
          description: errorMessage + " 请尝试重命名文件后重新上传。",
        })
      }
      // 检查是否是API Key未配置的错误
      else if (errorMessage.includes("请先配置DeepSeek API Key")) {
        toast({
          variant: "destructive",
          title: "需要配置API Key",
          description: (
            <div className="space-y-2">
              <p>请先配置您的DeepSeek API Key</p>
              <Button
                variant="outline"
                size="sm"
                onClick={() => router.push("/settings")}
                className="w-full mt-2"
              >
                去设置
              </Button>
            </div>
          ),
        })
      } else {
        toast({
          variant: "destructive",
          title: "上传失败",
          description: errorMessage,
        })
      }
    } finally {
      setIsUploading(false)
    }
  }

  // 修改 startProgressPolling 函数，更新历史记录中的进度
  const startProgressPolling = (taskId: string) => {
    // 清除任何现有的轮询间隔
    if (progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current)
    }

    // 设置轮询间隔
    progressIntervalRef.current = setInterval(async () => {
      try {
        const response = await apiClient.get(`/progress?taskId=${taskId}`)

        if (response.data.success) {
          const { status, progress, downloadUrl, error } = response.data.data

          // 更新历史记录中对应任务的状态和进度
          setHistory((prevHistory) =>
            prevHistory.map((item) =>
              item.taskId === taskId
                ? { ...item, status, progress, downloadUrl: downloadUrl || item.downloadUrl }
                : item,
            ),
          )
          if (status === "success" && downloadUrl) {
            toast({
              title: "翻译完成",
              description: "您的翻译文档已准备好下载",
            })

            // 刷新历史记录
            fetchHistory()

            // 停止轮询
            clearInterval(progressIntervalRef.current!)
          } else if (status === "failed") {
            toast({
              variant: "destructive",
              title: "翻译失败",
              description: error || "翻译过程中发生错误",
            })

            // 停止轮询
            clearInterval(progressIntervalRef.current!)
          }
        }
      } catch (error) {
        console.error("检查进度时出错:", error)
      }
    }, 2000) // 每2秒轮询一次
  }

  // 修改 getStatusText 函数，使其接受状态参数
  const getStatusText = (status?: string) => {
    switch (status) {
      case "pending":
        return "等待..."
      case "converting":
        return "正在转换文档..."
      case "translating":
        return "正在翻译内容..."
      case "success":
        return "翻译完成！"
      case "failed":
        return "翻译失败"
      default:
        return ""
    }
  }

  const resetUpload = () => {
    setFile(null)
    setUploadProgress(0)

    if (fileInputRef.current) {
      fileInputRef.current.value = ""
    }
  }

  const handleDelete = async (id: number) => {
    try {
      setIsDeleting(id)
      const response = await apiClient.delete(`/history/${id}`)

      if (response.data.success) {
        setHistory((prev) => prev.filter((item) => item.id !== id))

        toast({
          title: "记录已删除",
          description: "历史记录已成功删除",
        })
      }
    } catch (error: any) {
      toast({
        variant: "destructive",
        title: "删除记录失败",
        description: error.response?.data?.error || "发生错误",
      })
    } finally {
      setIsDeleting(null)
    }
  }

  const handleLogout = async () => {
    await logout()
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return new Intl.DateTimeFormat("zh-CN", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(date)
  }

  const getLanguageName = (code: string) => {
    const language = languages.find(lang => lang.code === code)
    return language ? language.name : code
  }

  // 截断文件名的函数
  const truncateFileName = (filename: string, maxLength: number = 20): string => {
    if (filename.length <= maxLength) {
      return filename
    }
    
    const extension = filename.split('.').pop()
    const nameWithoutExt = filename.substring(0, filename.lastIndexOf('.'))
    
    if (extension && nameWithoutExt.length > maxLength - extension.length - 3) {
      const truncatedName = nameWithoutExt.substring(0, maxLength - extension.length - 3)
      return `${truncatedName}...${extension}`
    }
    
    return filename.substring(0, maxLength - 3) + '...'
  }

  // 格式化状态显示
  const getStatusBadge = (status?: string, progress?: number) => {
    if (status === "success") {
      return (
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 bg-green-500 rounded-full"></div>
          <span className="text-green-700 dark:text-green-400 text-sm font-medium">完成</span>
        </div>
      )
    } else if (status === "failed") {
      return (
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 bg-red-500 rounded-full"></div>
          <span className="text-red-700 dark:text-red-400 text-sm font-medium">失败</span>
        </div>
      )
    } else if (status) {
      return (
        <div className="flex flex-col gap-1 min-w-[100px]">
          <div className="flex items-center gap-1">
            <Activity className="w-3 h-3 text-blue-500 animate-pulse" />
            <span className="text-blue-700 dark:text-blue-400 text-sm font-medium">{getStatusText(status)}</span>
          </div>
          <div className="flex items-center gap-2">
            <Progress value={progress || 0} className="h-1.5 flex-1" />
            <span className="text-xs text-muted-foreground">{progress || 0}%</span>
          </div>
        </div>
      )
    }
    return (
      <div className="flex items-center gap-1">
        <div className="w-2 h-2 bg-gray-400 rounded-full"></div>
        <span className="text-muted-foreground text-sm">未知</span>
      </div>
    )
  }

  // 组件的其余部分保持不变...
  return (
    <TooltipProvider>
      <div className="flex flex-col min-h-screen">
        <header className="sticky top-0 z-10 border-b bg-background">
          <div className="container flex h-16 items-center justify-between py-4 max-w-7xl mx-auto">
            <h1 className="text-2xl font-bold">DynaMyTranslate</h1>
            <div className="flex items-center gap-4">
              <span className="text-sm text-muted-foreground">欢迎，{user.email}</span>
              <Button variant="outline" size="sm" onClick={() => router.push("/settings")}>
                <Settings className="mr-2 h-4 w-4" />
                设置
              </Button>
              <AlertDialog open={logoutDialogOpen} onOpenChange={setLogoutDialogOpen}>
                <AlertDialogTrigger asChild>
                  <Button variant="outline" size="sm">
                    <LogOut className="mr-2 h-4 w-4" />
                    退出登录
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>确认退出</AlertDialogTitle>
                    <AlertDialogDescription>您确定要退出登录吗？</AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>取消</AlertDialogCancel>
                    <AlertDialogAction onClick={handleLogout}>确认退出</AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            </div>
          </div>
        </header>

        <main className="flex-1 container py-6 max-w-7xl mx-auto">
          <div className="grid gap-6 lg:grid-cols-2">
            {/* 左侧：上传区域 */}
            <div>
              <h2 className="text-2xl font-bold tracking-tight mb-4">上传文档</h2>
              <Card>
                <CardContent className="p-6">
                  <div className="space-y-6">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <label className="text-sm font-medium">原文语言</label>
                        <Select value={sourceLang} onValueChange={setSourceLang} disabled={isUploading || !!taskId}>
                          <SelectTrigger className="w-full">
                            <SelectValue placeholder="选择原文语言" />
                          </SelectTrigger>
                          <SelectContent>
                            {languages.map((lang) => (
                              <SelectItem key={lang.code} value={lang.code}>
                                {lang.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-2">
                        <label className="text-sm font-medium">目标语言</label>
                        <Select value={targetLang} onValueChange={setTargetLang} disabled={isUploading || !!taskId}>
                          <SelectTrigger className="w-full">
                            <SelectValue placeholder="选择目标语言" />
                          </SelectTrigger>
                          <SelectContent>
                            {languages.map((lang) => (
                              <SelectItem key={lang.code} value={lang.code}>
                                {lang.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    </div>

                    {/* 修改上传区域的条件渲染 */}
                    <div className="space-y-2">
                      <label className="text-sm font-medium">上传PDF</label>
                      {/* 添加文件名长度提示 */}
                      <div className="text-xs text-muted-foreground mb-2">
                        <p>• 支持PDF格式文件</p>
                        <p>• 文件名过长将自动调整（建议不超过100个字符）</p>
                        <p>• 特殊字符将被替换为安全字符</p>
                      </div>
                      <div className="flex flex-col gap-4">
                        <input
                          ref={fileInputRef}
                          type="file"
                          accept=".pdf"
                          onChange={handleFileChange}
                          className="hidden"
                          disabled={isUploading}
                        />
                        {!file && !isUploading && (
                          <div
                            onClick={() => fileInputRef.current?.click()}
                            className="cursor-pointer rounded-lg border-2 border-dashed border-gray-300 p-12 text-center hover:border-primary/50 dark:border-gray-700"
                          >
                            <FileUp className="mx-auto h-12 w-12 text-muted-foreground" />
                            <p className="mt-2 text-sm text-muted-foreground">点击选择PDF文件或拖放至此</p>
                          </div>
                        )}

                        {file && !isUploading && (
                          <div className="rounded-lg border p-4">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <FileUp className="h-5 w-5 text-muted-foreground" />
                                <div className="flex-1">
                                  <p className="text-sm font-medium">{file.name}</p>
                                  <p className="text-xs text-muted-foreground">
                                    {(file.size / 1024 / 1024).toFixed(2)} MB
                                  </p>
                                  {/* 添加文件名长度提示 */}
                                  {file.name.length > 80 && (
                                    <div className="flex items-center gap-1 mt-1">
                                      <AlertTriangle className="h-3 w-3 text-yellow-500" />
                                      <p className="text-xs text-yellow-600 dark:text-yellow-400">
                                        文件名较长，已自动调整
                                      </p>
                                    </div>
                                  )}
                                  {/* 显示原始文件名（如果被修改） */}
                                  {(() => {
                                    const originalName = fileInputRef.current?.files?.[0]?.name
                                    return originalName && originalName !== file.name ? (
                                      <p className="text-xs text-muted-foreground mt-1">
                                        原文件名: {originalName.length > 40 ? `${originalName.substring(0, 40)}...` : originalName}
                                      </p>
                                    ) : null
                                  })()}
                                </div>
                              </div>
                              <Button variant="ghost" size="sm" onClick={resetUpload} disabled={isUploading}>
                                更改
                              </Button>
                            </div>

                            <div className="mt-4">
                              <Button onClick={handleUpload} disabled={isUploading} className="w-full">
                                上传并翻译
                              </Button>
                            </div>
                          </div>
                        )}

                        {isUploading && (
                          <div className="rounded-lg border p-4">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <FileUp className="h-5 w-5 text-muted-foreground" />
                                <div>
                                  <p className="text-sm font-medium">{file?.name}</p>
                                  <p className="text-xs text-muted-foreground">上传中...</p>
                                </div>
                              </div>
                            </div>

                            <div className="mt-4 space-y-2">
                              <div className="flex justify-between text-xs">
                                <span>上传中...</span>
                                <span>{uploadProgress}%</span>
                              </div>
                              <Progress value={uploadProgress} className="h-2" />
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* 右侧：历史记录 */}
            <div>
              <h2 className="text-2xl font-bold tracking-tight mb-4">翻译历史</h2>
              <Card>
                <CardContent className="p-6">
                  {isLoadingHistory ? (
                    <div className="flex h-40 items-center justify-center">
                      <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                    </div>
                  ) : history.length === 0 ? (
                    <div className="flex h-40 flex-col items-center justify-center gap-2 text-center">
                      <FileText className="h-10 w-10 text-muted-foreground" />
                      <h3 className="text-lg font-medium">暂无翻译</h3>
                      <p className="text-sm text-muted-foreground">上传文档开始翻译</p>
                    </div>
                  ) : (
                    <div className="max-h-[600px] overflow-auto">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>
                              <div className="flex items-center gap-2">
                                <FileText className="w-4 h-4" />
                                文件名
                              </div>
                            </TableHead>
                            <TableHead>
                              <div className="flex items-center gap-2">
                                <Languages className="w-4 h-4" />
                                语言
                              </div>
                            </TableHead>
                            <TableHead>
                              <div className="flex items-center gap-2">
                                <Calendar className="w-4 h-4" />
                                日期
                              </div>
                            </TableHead>
                            <TableHead>
                              <div className="flex items-center gap-2">
                                <Activity className="w-4 h-4" />
                                状态
                              </div>
                            </TableHead>
                            <TableHead className="text-right">操作</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {history.map((item) => (
                            <TableRow key={item.id} className="hover:bg-muted/50 transition-colors">
                              <TableCell className="font-medium">
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <span className="cursor-help">{truncateFileName(item.filename)}</span>
                                  </TooltipTrigger>
                                  <TooltipContent>
                                    <p className="max-w-xs break-words">{item.filename}</p>
                                  </TooltipContent>
                                </Tooltip>
                              </TableCell>
                              <TableCell>
                                <div className="flex items-center gap-1 text-sm">
                                  <span className="px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded-md text-xs font-medium">
                                    {getLanguageName(item.sourceLanguage || 'en')}
                                  </span>
                                  <span className="text-muted-foreground">→</span>
                                  <span className="px-2 py-1 bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 rounded-md text-xs font-medium">
                                    {getLanguageName(item.targetLanguage || item.translatedLang)}
                                  </span>
                                </div>
                              </TableCell>
                              <TableCell>
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <span className="text-sm text-muted-foreground cursor-help">
                                      {formatDate(item.createdAt)}
                                    </span>
                                  </TooltipTrigger>
                                  <TooltipContent>
                                    <p>{new Date(item.createdAt).toLocaleString('zh-CN')}</p>
                                  </TooltipContent>
                                </Tooltip>
                              </TableCell>
                              <TableCell>
                                {getStatusBadge(item.status, item.progress)}
                              </TableCell>
                              <TableCell className="text-right">
                                <div className="flex justify-end gap-2">
                                  {(!item.status || item.status === "success") && (
                                    <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={async () => {
                                      try {
                                        // 处理跨域请求
                                        const response = await fetch(`${getApiBaseUrl()}/download/${item.id}`, {
                                          headers: {
                                            Authorization: `Bearer ${localStorage.getItem('token')}`  // 携带认证token
                                          }
                                        });
                                        if (!response.ok) throw new Error('下载失败');
                                        // 获取文件名（从Content-Disposition或自定义）
                                        const filename = response.headers.get('content-disposition')
                                          ?.split('filename=')[1]
                                          || `translated_${Date.now()}.pdf`;
                                        // 创建Blob对象
                                        const blob = await response.blob();
                                        
                                        // 创建临时下载链接
                                        const link = document.createElement('a');
                                        link.href = URL.createObjectURL(blob);
                                        link.download = filename;
                                        document.body.appendChild(link);
                                        link.click();
                                        document.body.removeChild(link);
                                        URL.revokeObjectURL(link.href);
                                      } catch (error) {
                                        console.error('下载失败:', error);
                                        alert('文件下载失败，请重试');
                                      }
                                    }}
                                    >
                                      <Download className="h-4 w-4" />
                                    </Button>
                                  )}
                                  <AlertDialog>
                                    <AlertDialogTrigger asChild>
                                      <Button variant="outline" size="sm">
                                        <Trash2 className="h-4 w-4 text-destructive" />
                                      </Button>
                                    </AlertDialogTrigger>
                                    <AlertDialogContent>
                                      <AlertDialogHeader>
                                        <AlertDialogTitle>删除记录</AlertDialogTitle>
                                        <AlertDialogDescription>
                                          您确定要删除此翻译记录吗？ 此操作无法撤销。
                                        </AlertDialogDescription>
                                      </AlertDialogHeader>
                                      <AlertDialogFooter>
                                        <AlertDialogCancel>取消</AlertDialogCancel>
                                        <AlertDialogAction
                                          onClick={() => handleDelete(item.id)}
                                          disabled={isDeleting === item.id}
                                        >
                                          {isDeleting === item.id ? (
                                            <>
                                              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                              删除中...
                                            </>
                                          ) : (
                                            "删除"
                                          )}
                                        </AlertDialogAction>
                                      </AlertDialogFooter>
                                    </AlertDialogContent>
                                  </AlertDialog>
                                </div>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </div>
        </main>

        <footer className="border-t py-6 md:py-0">
          <div className="container flex flex-col items-center justify-between gap-4 md:h-24 md:flex-row max-w-7xl mx-auto">
            <p className="text-sm text-gray-500 dark:text-gray-400">
              &copy; {new Date().getFullYear()} DynaMyTranslate。保留所有权利。
            </p>
          </div>
        </footer>
      </div>
    </TooltipProvider>
  )
}

