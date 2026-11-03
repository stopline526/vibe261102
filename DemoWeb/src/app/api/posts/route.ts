import { NextResponse, type NextRequest } from "next/server"

import { postInputSchema } from "@/lib/schema"
import { createPost, listPosts } from "@/lib/store"

// GET /api/posts?q=검색어&page=1&pageSize=10
export async function GET(request: NextRequest) {
  const params = request.nextUrl.searchParams
  const page = Number(params.get("page")) || 1
  const pageSize = Math.min(50, Number(params.get("pageSize")) || 10)
  const result = await listPosts({ query: params.get("q") ?? "", page, pageSize })
  return NextResponse.json(result)
}

// POST /api/posts
export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => null)
  const parsed = postInputSchema.safeParse(body)
  if (!parsed.success) {
    return NextResponse.json(
      { error: "입력값이 올바르지 않습니다.", issues: parsed.error.issues },
      { status: 400 }
    )
  }
  const post = await createPost(parsed.data)
  return NextResponse.json(post, { status: 201 })
}
