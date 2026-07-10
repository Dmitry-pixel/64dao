export const dynamic = "force-dynamic";
export const revalidate = 0;

async function getSiteMode() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  try {
    const res = await fetch(`${apiUrl}/api/site-mode`, { cache: "no-store" });
    if (!res.ok) throw new Error("bad response");
    return res.json();
  } catch {
    return {
      title: "Ведутся технические работы",
      text: "Мы обновляем контент сайта. Это временно — скоро всё вернётся в обычный режим.",
    };
  }
}

export default async function MaintenancePage() {
  const { title, text } = await getSiteMode();

  return (
    <div
      style={{
        minHeight: "100vh",
        width: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        backgroundColor: "#e8e4db",
        fontFamily: "Georgia, serif",
        color: "#1a2540",
        padding: "24px",
      }}
    >
      <div style={{ maxWidth: 560, textAlign: "center" }}>
        <h1
          style={{
            fontSize: "clamp(28px, 5vw, 40px)",
            marginBottom: 16,
            color: "#1a2540",
          }}
        >
          {title}
        </h1>
        <p
          style={{
            fontSize: 18,
            lineHeight: 1.6,
            color: "#1a2540",
            opacity: 0.85,
          }}
        >
          {text}
        </p>
      </div>
    </div>
  );
}
