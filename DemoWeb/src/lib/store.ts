import "server-only"

import { neon, type NeonQueryFunction } from "@neondatabase/serverless"

import type { Post, PostInput, PostSummary } from "@/lib/schema"
import seed from "../../data/seed.json"

// Neon(PostgreSQL)에 게시글을 저장한다. 연결 문자열은 .env.local의 DATABASE_URL.
let client: NeonQueryFunction<false, false> | null = null
function db() {
  if (!client) {
    // Vercel 등에 .env 줄을 그대로 붙여 넣으면 값에 따옴표가 섞여 들어가므로 벗겨 낸다.
    const url = process.env.DATABASE_URL?.trim().replace(/^(["'])(.*)\1$/, "$2")
    if (!url) throw new Error("DATABASE_URL 환경 변수가 설정되지 않았습니다.")
    client = neon(url)
  }
  return client
}

// 처음 실행할 때 posts 테이블을 만들고 data/seed.json의 예시 글을 넣는다.
// 테이블이 이미 있으면 아무것도 하지 않으므로, 글을 모두 지워도 다시 채워지지 않는다.
let ready: Promise<void> | null = null
function ensureSchema() {
  ready ??= (async () => {
    const sql = db()
    const [{ exists }] = await sql`SELECT to_regclass('public.posts') IS NOT NULL AS exists`
    if (exists) return
    await sql`
      CREATE TABLE IF NOT EXISTS posts (
        id         SERIAL PRIMARY KEY,
        title      TEXT        NOT NULL,
        author     TEXT        NOT NULL,
        content    TEXT        NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
      )`
    const posts = [...seed.posts].sort((a, b) => a.id - b.id)
    await sql`
      INSERT INTO posts (title, author, content, created_at, updated_at)
      SELECT * FROM unnest(
        ${posts.map((p) => p.title)}::text[],
        ${posts.map((p) => p.author)}::text[],
        ${posts.map((p) => p.content)}::text[],
        ${posts.map((p) => p.createdAt)}::timestamptz[],
        ${posts.map((p) => p.updatedAt)}::timestamptz[]
      )`
  })().catch((error) => {
    ready = null
    throw error
  })
  return ready
}

type Row = Record<string, unknown>

function toSummary(row: Row): PostSummary {
  return {
    id: Number(row.id),
    title: String(row.title),
    author: String(row.author),
    createdAt: new Date(row.created_at as string).toISOString(),
    updatedAt: new Date(row.updated_at as string).toISOString(),
  }
}

const toPost = (row: Row): Post => ({ ...toSummary(row), content: String(row.content) })

export async function listPosts({
  query = "",
  page = 1,
  pageSize = 10,
}: {
  query?: string
  page?: number
  pageSize?: number
}) {
  await ensureSchema()
  const sql = db()
  // ILIKE 패턴에서 %, _ 를 글자 그대로 찾도록 이스케이프한다.
  const pattern = `%${query.trim().replace(/[\\%_]/g, "\\$&")}%`

  const [{ total }] = await sql`
    SELECT count(*)::int AS total FROM posts
    WHERE title ILIKE ${pattern} OR content ILIKE ${pattern}`
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  const current = Math.min(Math.max(1, page), totalPages)

  // 목록에는 본문을 내려주지 않는다.
  const rows = await sql`
    SELECT id, title, author, created_at, updated_at FROM posts
    WHERE title ILIKE ${pattern} OR content ILIKE ${pattern}
    ORDER BY id DESC
    LIMIT ${pageSize} OFFSET ${(current - 1) * pageSize}`

  return { posts: rows.map(toSummary), total, page: current, pageSize, totalPages }
}

export async function getPost(id: number) {
  await ensureSchema()
  const [row] = await db()`SELECT * FROM posts WHERE id = ${id}`
  return row ? toPost(row) : null
}

export async function createPost(input: PostInput) {
  await ensureSchema()
  const [row] = await db()`
    INSERT INTO posts (title, author, content)
    VALUES (${input.title}, ${input.author}, ${input.content})
    RETURNING *`
  return toPost(row)
}

export async function updatePost(id: number, input: PostInput) {
  await ensureSchema()
  const [row] = await db()`
    UPDATE posts
    SET title = ${input.title}, author = ${input.author},
        content = ${input.content}, updated_at = now()
    WHERE id = ${id}
    RETURNING *`
  return row ? toPost(row) : null
}

export async function deletePost(id: number) {
  await ensureSchema()
  const rows = await db()`DELETE FROM posts WHERE id = ${id} RETURNING id`
  return rows.length > 0
}
