import { z } from "zod"

export const postInputSchema = z.object({
  title: z
    .string()
    .trim()
    .min(1, "제목을 입력해 주세요.")
    .max(100, "제목은 100자 이하로 입력해 주세요."),
  author: z
    .string()
    .trim()
    .min(1, "작성자를 입력해 주세요.")
    .max(20, "작성자는 20자 이하로 입력해 주세요."),
  content: z
    .string()
    .trim()
    .min(1, "내용을 입력해 주세요.")
    .max(5000, "내용은 5000자 이하로 입력해 주세요."),
})

export type PostInput = z.infer<typeof postInputSchema>

export type Post = PostInput & {
  id: number
  createdAt: string
  updatedAt: string
}

export type PostSummary = Omit<Post, "content">

export type PostListResponse = {
  posts: PostSummary[]
  total: number
  page: number
  pageSize: number
  totalPages: number
}
