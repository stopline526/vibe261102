import { NextResponse, type NextRequest } from "next/server"

import { postInputSchema } from "@/lib/schema"
import { deletePost, getPost, updatePost } from "@/lib/store"

type Ctx = RouteContext<"/api/posts/[id]">

const notFound = () =>
  NextResponse.json({ error: "게시글을 찾을 수 없습니다." }, { status: 404 })

async function parseId(ctx: Ctx) {
  const id = Number((await ctx.params).id)
  return Number.isInteger(id) && id > 0 ? id : null
}

export async function GET(_request: NextRequest, ctx: Ctx) {
  const id = await parseId(ctx)
  const post = id ? await getPost(id) : null
  return post ? NextResponse.json(post) : notFound()
}

export async function PUT(request: NextRequest, ctx: Ctx) {
  const id = await parseId(ctx)
  if (!id) return notFound()
  const parsed = postInputSchema.safeParse(await request.json().catch(() => null))
  if (!parsed.success) {
    return NextResponse.json(
      { error: "입력값이 올바르지 않습니다.", issues: parsed.error.issues },
      { status: 400 }
    )
  }
  const post = await updatePost(id, parsed.data)
  return post ? NextResponse.json(post) : notFound()
}

export async function DELETE(_request: NextRequest, ctx: Ctx) {
  const id = await parseId(ctx)
  const deleted = id ? await deletePost(id) : false
  return deleted ? new NextResponse(null, { status: 204 }) : notFound()
}
