import { Suspense } from "react"

import { PostList } from "@/components/post-list"

export default function HomePage() {
  return (
    <Suspense>
      <PostList />
    </Suspense>
  )
}
