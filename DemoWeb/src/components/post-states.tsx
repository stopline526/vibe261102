import Link from "next/link"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

export function PostSkeleton() {
  return (
    <Card>
      <CardHeader className="gap-3">
        <Skeleton className="h-7 w-2/3" />
        <Skeleton className="h-4 w-1/3" />
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-1/2" />
      </CardContent>
    </Card>
  )
}

export function PostMessage({ status }: { status: "not-found" | "error" }) {
  return (
    <Card>
      <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
        <p className="text-sm text-muted-foreground">
          {status === "not-found"
            ? "게시글을 찾을 수 없습니다. 삭제되었거나 잘못된 주소입니다."
            : "게시글을 불러오지 못했습니다."}
        </p>
        <Button asChild variant="outline" size="sm">
          <Link href="/">목록으로</Link>
        </Button>
      </CardContent>
    </Card>
  )
}
