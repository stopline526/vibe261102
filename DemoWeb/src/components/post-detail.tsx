"use client"

import { useState } from "react"
import Link from "next/link"
import { useParams, useRouter } from "next/navigation"
import { ArrowLeftIcon, PencilIcon, Trash2Icon } from "lucide-react"
import { toast } from "sonner"

import { formatDateTime } from "@/lib/format"
import { usePost } from "@/components/use-post"
import { PostMessage, PostSkeleton } from "@/components/post-states"
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
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"

export function PostDetail() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const state = usePost(id)
  const [deleting, setDeleting] = useState(false)

  if (state.status === "loading") return <PostSkeleton />
  if (state.status !== "ready") return <PostMessage status={state.status} />

  const { post } = state
  const edited = post.updatedAt !== post.createdAt

  async function handleDelete() {
    setDeleting(true)
    const res = await fetch(`/api/posts/${post.id}`, { method: "DELETE" })
    if (!res.ok) {
      setDeleting(false)
      toast.error("삭제하지 못했습니다.")
      return
    }
    toast.success("게시글을 삭제했습니다.")
    router.push("/")
  }

  return (
    <div className="flex flex-col gap-4">
      <Button asChild variant="ghost" size="sm" className="self-start">
        <Link href="/">
          <ArrowLeftIcon /> 목록으로
        </Link>
      </Button>

      <Card>
        <CardHeader>
          <CardTitle className="text-xl leading-snug break-words sm:text-2xl">
            {post.title}
          </CardTitle>
          <CardDescription className="flex flex-wrap gap-x-3 gap-y-1">
            <span>{post.author}</span>
            <span>작성 {formatDateTime(post.createdAt)}</span>
            {edited && <span>수정 {formatDateTime(post.updatedAt)}</span>}
          </CardDescription>
        </CardHeader>
        <Separator />
        <CardContent>
          <p className="leading-7 break-words whitespace-pre-wrap">{post.content}</p>
        </CardContent>
        <CardFooter className="justify-end gap-2 border-t">
          <Button asChild variant="outline">
            <Link href={`/posts/${post.id}/edit`}>
              <PencilIcon /> 수정
            </Link>
          </Button>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="destructive" disabled={deleting}>
                <Trash2Icon /> 삭제
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>게시글을 삭제할까요?</AlertDialogTitle>
                <AlertDialogDescription>
                  &ldquo;{post.title}&rdquo; 글이 영구적으로 삭제되며 되돌릴 수
                  없습니다.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>취소</AlertDialogCancel>
                <AlertDialogAction variant="destructive" onClick={handleDelete}>
                  삭제
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </CardFooter>
      </Card>
    </div>
  )
}
