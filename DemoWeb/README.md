# DemoWeb 게시판

Next.js(App Router) + TypeScript + shadcn/ui로 만든 간단한 웹 게시판입니다.
Route Handler가 Neon(서버리스 PostgreSQL)에 데이터를 저장합니다.

## 기능

- 게시글 목록: 번호·제목·작성자·작성일 표시, 10개씩 페이지네이션
- 게시글 상세 보기
- 게시글 작성 / 수정 (입력값 검증 포함)
- 게시글 삭제 (확인 다이얼로그)
- 제목·내용 검색
- 반응형 레이아웃 (모바일에서는 카드 목록, 태블릿 이상은 표)
- 다크 / 라이트 / 시스템 테마 전환

## 실행 방법

Node.js 20 이상이 필요합니다.

```bash
cd DemoWeb
npm install
cp .env.example .env.local   # DATABASE_URL 입력
```

개발 서버 (http://localhost:3000):

```bash
npm run dev
```

프로덕션 빌드 후 실행:

```bash
npm run build
npm run start
```

> 저장소 루트의 `.claude/launch.json`에 `DemoWeb` 설정(포트 3000)이 있어서 Claude 미리보기에서도 바로 띄울 수 있습니다.

## 데이터 저장 (Neon PostgreSQL)

게시글은 [Neon](https://neon.tech) PostgreSQL의 `posts` 테이블에 저장됩니다.

1. `.env.example`을 `.env.local`로 복사하고 `DATABASE_URL`에 Neon 연결 문자열을 넣습니다.
   `.env.local`은 `.gitignore`에 들어 있어 커밋되지 않습니다.
2. 서버를 띄우고 첫 요청이 오면 `posts` 테이블이 없을 때만 테이블을 만들고 `data/seed.json`(예시 글 14개)을 넣습니다.
3. 처음 상태로 되돌리려면 Neon SQL Editor에서 `DROP TABLE posts;`를 실행한 뒤 다시 접속하면 됩니다.

```sql
CREATE TABLE posts (
  id         SERIAL PRIMARY KEY,
  title      TEXT        NOT NULL,
  author     TEXT        NOT NULL,
  content    TEXT        NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

## API

| 메서드 | 경로 | 설명 |
| --- | --- | --- |
| GET | `/api/posts?q=&page=&pageSize=` | 목록 (검색·페이지네이션) |
| POST | `/api/posts` | 작성 `{ title, author, content }` |
| GET | `/api/posts/:id` | 상세 |
| PUT | `/api/posts/:id` | 수정 |
| DELETE | `/api/posts/:id` | 삭제 |

## 폴더 구조

```
src/
  app/
    page.tsx                 목록 + 검색
    posts/new/page.tsx       작성
    posts/[id]/page.tsx      상세 + 삭제
    posts/[id]/edit/page.tsx 수정
    api/posts/...            Route Handler (REST API)
  components/                게시판 화면 컴포넌트, 테마 토글
  components/ui/             shadcn/ui 컴포넌트
  lib/schema.ts              zod 스키마와 타입 (클라이언트·서버 공용)
  lib/store.ts               Neon(PostgreSQL) 저장소
data/seed.json               첫 실행 때 넣는 예시 데이터
```

## 사용한 기술

Next.js 16, React 19, TypeScript, Neon PostgreSQL(@neondatabase/serverless), Tailwind CSS v4, shadcn/ui(Radix), react-hook-form + zod, next-themes, sonner
