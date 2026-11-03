import { Suspense } from "react"

import { PostDetail } from "@/components/post-detail"
import { PostSkeleton } from "@/components/post-states"

export default function PostPage() {
  return (
    <Suspense fallback={<PostSkeleton />}>
      <PostDetail />
    </Suspense>
  )
}
