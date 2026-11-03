"use client"

import { useParams } from "next/navigation"

import { usePost } from "@/components/use-post"
import { PostForm } from "@/components/post-form"
import { PostMessage, PostSkeleton } from "@/components/post-states"

export function PostEdit() {
  const { id } = useParams<{ id: string }>()
  const state = usePost(id)

  if (state.status === "loading") return <PostSkeleton />
  if (state.status !== "ready") return <PostMessage status={state.status} />
  return <PostForm post={state.post} />
}
