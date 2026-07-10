"use client";

import { useEffect, useState } from "react";

type SiteMode = {
  enabled: boolean;
  title: string;
  text: string;
};

export default function SiteModePage() {
  const [mode, setMode] = useState<SiteMode | null>(null);
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    fetch(`${apiUrl}/api/site-mode`, { credentials: "include" })
      .then((r) => r.json())
      .then(setMode)
      .catch(() => setError("Не удалось загрузить текущее состояние"));
  }, []);

  async function save() {
    if (!mode) return;
    setSaving(true);
    setError(null);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL;
      const res = await fetch(`${apiUrl}/api/admin/site-mode`, {
        method: "PUT",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(mode),
      });
      if (!res.ok) throw new Error(await res.text());
      setSavedAt(new Date().toLocaleTimeString("ru-RU"));
    } catch (e) {
      setError("Не удалось сохранить. Проверьте консоль/сеть.");
    } finally {
      setSaving(false);
    }
  }

  if (!mode) {
    return <div style={{ padding: 24 }}>Загрузка…</div>;
  }

  return (
    <div style={{ padding: 24, maxWidth: 640 }}>
      <h1 style={{ fontSize: 22, marginBottom: 8, color: "#1a2540" }}>
        Режим заглушки
      </h1>
      <p style={{ color: "#555", marginBottom: 24, lineHeight: 1.5 }}>
        При включении: главная, /register и все публичные страницы (кроме
        /admin, /login, /verify) показывают страницу-заглушку. Регистрация
        через API также блокируется (403). Можно спокойно редактировать
        контент в других разделах админки, пока режим включён.
      </p>

      <label
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          marginBottom: 24,
          cursor: "pointer",
        }}
      >
        <input
          type="checkbox"
          checked={mode.enabled}
          onChange={(e) => setMode({ ...mode, enabled: e.target.checked })}
          style={{ width: 20, height: 20 }}
        />
        <span style={{ fontWeight: 600 }}>
          Заглушка {mode.enabled ? "включена" : "выключена"}
        </span>
      </label>

      <div style={{ marginBottom: 16 }}>
        <label style={{ display: "block", marginBottom: 6, fontWeight: 600 }}>
          Заголовок
        </label>
        <input
          type="text"
          value={mode.title}
          onChange={(e) => setMode({ ...mode, title: e.target.value })}
          style={{
            width: "100%",
            padding: "8px 12px",
            border: "1px solid #ccc",
            borderRadius: 6,
            fontSize: 16,
          }}
        />
      </div>

      <div style={{ marginBottom: 24 }}>
        <label style={{ display: "block", marginBottom: 6, fontWeight: 600 }}>
          Текст
        </label>
        <textarea
          value={mode.text}
          onChange={(e) => setMode({ ...mode, text: e.target.value })}
          rows={4}
          style={{
            width: "100%",
            padding: "8px 12px",
            border: "1px solid #ccc",
            borderRadius: 6,
            fontSize: 16,
            fontFamily: "inherit",
          }}
        />
      </div>

      <button
        onClick={save}
        disabled={saving}
        style={{
          backgroundColor: "#1e3a8a",
          color: "#fff",
          border: "none",
          borderRadius: 6,
          padding: "10px 20px",
          fontSize: 16,
          cursor: saving ? "default" : "pointer",
          opacity: saving ? 0.6 : 1,
        }}
      >
        {saving ? "Сохранение…" : "Сохранить"}
      </button>

      {savedAt && (
        <span style={{ marginLeft: 12, color: "#2e7d32" }}>
          Сохранено в {savedAt}
        </span>
      )}
      {error && <div style={{ marginTop: 12, color: "#c0392b" }}>{error}</div>}
    </div>
  );
}
