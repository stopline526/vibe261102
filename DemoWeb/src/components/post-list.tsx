"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { usePathname, useRouter, useSearchParams } from "next/navigation"
import { ChevronLeftIcon, ChevronRightIcon, SearchIcon, XIcon } from "lucide-react"

import type { PostListResponse } from "@/lib/schema"
import { formatDate } from "@/lib/format"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

const PAGE_SIZE = 10

export function PostList() {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const query = searchParams.get("q") ?? ""
  const page = Number(searchParams.get("page")) || 1

  const requestKey = `${query}|${page}`
  const [data, setData] = useState<PostListResponse | null>(null)
  // 실패한 요청의 key만 기억해서, 다른 페이지로 이동하면 오류 표시가 자동으로 사라지게 한다.
  const [failedKey, setFailedKey] = useState<string | null>(null)
  const error = failedKey === requestKey ? "게시글을 불러오지 못했습니다." : null

  useEffect(() => {
    const controller = new AbortController()
    const params = new URLSearchParams({
      q: query,
      page: String(page),
      pageSize: String(PAGE_SIZE),
    })
    fetch(`/api/posts?${params}`, { signal: controller.signal, cache: "no-store" })
      .then((res) => {
        if (!res.ok) throw new Error()
        return res.json() as Promise<PostListResponse>
      })
      .then(setData)
      .catch(() => {
        if (!controller.signal.aborted) setFailedKey(requestKey)
      })
    return () => controller.abort()
  }, [query, page, requestKey])

  function navigate(next: { q?: string; page?: number }) {
    const params = new URLSearchParams()
    const q = next.q ?? query
    const p = next.page ?? 1
    if (q) params.set("q", q)
    if (p > 1) params.set("page", String(p))
    const qs = params.toString()
    router.push(qs ? `${pathname}?${qs}` : pathname)
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold tracking-tight">자유 게시판</h1>
        <p className="text-sm text-muted-foreground">
          {data
            ? query
              ? `"${query}" 검색 결과 ${data.total}건`
              : `전체 게시글 ${data.total}건`
            : "게시글을 불러오는 중…"}
        </p>
      </div>

      <form
        role="search"
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault()
          const q = new FormData(e.currentTarget).get("q")
          navigate({ q: String(q ?? "").trim() })
        }}
      >
        <div className="relative flex-1">
          <SearchIcon className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
          {/* key로 URL 검색어가 바뀌면(뒤로 가기 등) 입력창을 새로 그린다. */}
          <Input
            key={query}
            name="q"
            type="search"
            defaultValue={query}
            placeholder="제목·내용 검색"
            aria-label="검색어"
            className="pl-8"
          />
        </div>
        <Button type="submit">검색</Button>
        {query && (
          <Button
            type="button"
            variant="outline"
            onClick={() => navigate({ q: "" })}
            aria-label="검색 초기화"
          >
            <XIcon />
            <span className="hidden sm:inline">초기화</span>
          </Button>
        )}
      </form>

      {error ? (
        <Card>
          <CardContent className="py-10 text-center text-sm text-destructive">
            {error}
          </CardContent>
        </Card>
      ) : !data ? (
        <ListSkeleton />
      ) : data.posts.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
            <p className="text-sm text-muted-foreground">
              {query ? "검색 결과가 없습니다." : "아직 게시글이 없습니다."}
            </p>
            <Button asChild variant="outline" size="sm">
              <Link href="/posts/new">첫 글 작성하기</Link>
            </Button>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* 태블릿 이상: 표 */}
          <Card className="hidden py-0 md:block">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-16 text-center">번호</TableHead>
                  <TableHead>제목</TableHead>
                  <TableHead className="w-32">작성자</TableHead>
                  <TableHead className="w-32 text-right">작성일</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.posts.map((post) => (
                  <TableRow key={post.id}>
                    <TableCell className="text-center text-muted-foreground">
                      {post.id}
                    </TableCell>
                    <TableCell className="max-w-0 truncate font-medium">
                      <Link
                        href={`/posts/${post.id}`}
                        className="hover:underline"
                      >
                        {post.title}
                      </Link>
                      {post.updatedAt !== post.createdAt && (
                        <Badge variant="secondary" className="ml-2">
                          수정됨
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell className="truncate">{post.author}</TableCell>
                    <TableCell className="text-right text-muted-foreground">
                      {formatDate(post.createdAt)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>

          {/* 모바일: 카드 목록 */}
          <ul className="flex flex-col gap-3 md:hidden">
            {data.posts.map((post) => (
              <li key={post.id}>
                <Link href={`/posts/${post.id}`} className="block">
                  <Card className="gap-1 transition-colors hover:bg-muted/50">
                    <CardHeader>
                      <CardTitle className="line-clamp-2">{post.title}</CardTitle>
                      <CardDescription>
                        {post.author} · {formatDate(post.createdAt)}
                      </CardDescription>
                    </CardHeader>
                  </Card>
                </Link>
              </li>
            ))}
          </ul>

          <Pagination
            page={data.page}
            totalPages={data.totalPages}
            onChange={(p) => navigate({ page: p })}
          />
        </>
      )}
    </div>
  )
}

function Pagination({
  page,
  totalPages,
  onChange,
}: {
  page: number
  totalPages: number
  onChange: (page: number) => void
}) {
  if (totalPages <= 1) return null

  // 현재 페이지 주변으로 최대 5개 번호만 보여준다.
  const start = Math.max(1, Math.min(page - 2, totalPages - 4))
  const pages = Array.from(
    { length: Math.min(5, totalPages) },
    (_, i) => start + i
  )

  return (
    <nav aria-label="페이지 이동" className="flex items-center justify-center gap-1">
      <Button
        variant="ghost"
        size="sm"
        disabled={page <= 1}
        onClick={() => onChange(page - 1)}
      >
        <ChevronLeftIcon />
        <span className="hidden sm:inline">이전</span>
      </Button>
      {pages.map((p) => (
        <Button
          key={p}
          variant={p === page ? "outline" : "ghost"}
          size="icon-sm"
          aria-current={p === page ? "page" : undefined}
          onClick={() => onChange(p)}
        >
          {p}
        </Button>
      ))}
      <Button
        variant="ghost"
        size="sm"
        disabled={page >= totalPages}
        onClick={() => onChange(page + 1)}
      >
        <span className="hidden sm:inline">다음</span>
        <ChevronRightIcon />
      </Button>
    </nav>
  )
}

function ListSkeleton() {
  return (
    <div className="flex flex-col gap-3">
      {Array.from({ length: 5 }, (_, i) => (
        <Skeleton key={i} className="h-12 w-full" />
      ))}
    </div>
  )
}
