"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { zodResolver } from "@hookform/resolvers/zod"
import { Controller, useForm } from "react-hook-form"
import { toast } from "sonner"

import { postInputSchema, type Post, type PostInput } from "@/lib/schema"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Field,
  FieldDescription,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"

export function PostForm({ post }: { post?: Post }) {
  const router = useRouter()
  const isEdit = Boolean(post)

  const form = useForm<PostInput>({
    resolver: zodResolver(postInputSchema),
    defaultValues: {
      title: post?.title ?? "",
      author: post?.author ?? "",
      content: post?.content ?? "",
    },
  })

  async function onSubmit(values: PostInput) {
    const res = await fetch(isEdit ? `/api/posts/${post!.id}` : "/api/posts", {
      method: isEdit ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(values),
    })
    if (!res.ok) {
      toast.error(isEdit ? "수정하지 못했습니다." : "등록하지 못했습니다.")
      return
    }
    const saved = (await res.json()) as Post
    toast.success(isEdit ? "게시글을 수정했습니다." : "게시글을 등록했습니다.")
    router.push(`/posts/${saved.id}`)
  }

  const cancelHref = isEdit ? `/posts/${post!.id}` : "/"
  const { isSubmitting } = form.formState

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-xl">
          {isEdit ? "게시글 수정" : "새 글 작성"}
        </CardTitle>
        <CardDescription>
          {isEdit
            ? "내용을 고친 뒤 저장 버튼을 눌러 주세요."
            : "제목, 작성자, 내용을 입력해 주세요."}
        </CardDescription>
      </CardHeader>
      <form onSubmit={form.handleSubmit(onSubmit)} noValidate>
        <CardContent>
          <FieldGroup>
            <Controller
              name="title"
              control={form.control}
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel htmlFor="post-title">제목</FieldLabel>
                  <Input
                    {...field}
                    id="post-title"
                    placeholder="제목을 입력하세요"
                    aria-invalid={fieldState.invalid}
                  />
                  <FieldError errors={[fieldState.error]} />
                </Field>
              )}
            />
            <Controller
              name="author"
              control={form.control}
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid} className="sm:max-w-xs">
                  <FieldLabel htmlFor="post-author">작성자</FieldLabel>
                  <Input
                    {...field}
                    id="post-author"
                    placeholder="이름 또는 닉네임"
                    aria-invalid={fieldState.invalid}
                  />
                  <FieldError errors={[fieldState.error]} />
                </Field>
              )}
            />
            <Controller
              name="content"
              control={form.control}
              render={({ field, fieldState }) => (
                <Field data-invalid={fieldState.invalid}>
                  <FieldLabel htmlFor="post-content">내용</FieldLabel>
                  <Textarea
                    {...field}
                    id="post-content"
                    placeholder="내용을 입력하세요"
                    className="min-h-60"
                    aria-invalid={fieldState.invalid}
                  />
                  <FieldDescription>{field.value.length} / 5000자</FieldDescription>
                  <FieldError errors={[fieldState.error]} />
                </Field>
              )}
            />
          </FieldGroup>
        </CardContent>
        <CardFooter className="mt-6 justify-end gap-2">
          <Button asChild variant="outline">
            <Link href={cancelHref}>취소</Link>
          </Button>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "저장 중…" : isEdit ? "저장" : "등록"}
          </Button>
        </CardFooter>
      </form>
    </Card>
  )
}
