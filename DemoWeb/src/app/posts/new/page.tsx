import type { Metadata } from "next"

import { PostForm } from "@/components/post-form"

export const metadata: Metadata = { title: "새 글 작성" }

export default function NewPostPage() {
  return <PostForm />
}
