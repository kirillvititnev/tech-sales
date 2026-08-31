function notFound(): Response {
  return new Response("Not Found", {
    status: 404,
    headers: { "Cache-Control": "no-store" },
  });
}

export function GET(): Response {
  return notFound();
}

export function POST(): Response {
  return notFound();
}

export function PUT(): Response {
  return notFound();
}

export function PATCH(): Response {
  return notFound();
}

export function DELETE(): Response {
  return notFound();
}
