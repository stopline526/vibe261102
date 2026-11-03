"use client"

import { useEffect, useState } from "react"

import type { Post } from "@/lib/schema"

type State =
  | { status: "loading" }
  | { status: "not-found" }
  | { status: "error" }
  | { status: "ready"; post: Post }

// 상세·수정 화면에서 게시글 한 건을 불러온다.
export function usePost(id: string) {
  const [state, setState] = useState<{ id: string; value: State }>({
    id,
    value: { status: "loading" },
  })

  useEffect(() => {
    const controller = new AbortController()
    fetch(`/api/posts/${id}`, { signal: controller.signal, cache: "no-store" })
      .then(async (res): Promise<State> => {
        if (res.status === 404) return { status: "not-found" }
        if (!res.ok) return { status: "error" }
        return { status: "ready", post: (await res.json()) as Post }
      })
      .catch((): State => ({ status: "error" }))
      .then((value) => {
        if (!controller.signal.aborted) setState({ id, value })
      })
    return () => controller.abort()
  }, [id])

  return state.id === id ? state.value : ({ status: "loading" } as State)
}
