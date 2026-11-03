import type { Metadata } from "next"
import { Suspense } from "react"

import { PostEdit } from "@/components/post-edit"
import { PostSkeleton } from "@/components/post-states"

export const metadata: Metadata = { title: "게시글 수정" }

export default function EditPostPage() {
  return (
    <Suspense fallback={<PostSkeleton />}>
      <PostEdit />
    </Suspense>
  )
}
